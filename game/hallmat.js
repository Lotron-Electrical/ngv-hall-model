import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

// THE HALL, RENDERED THE WAY THE PROPOSAL VIEWER RENDERS IT (Lloyd, 2026-09-04: "make sure the
// model of the hall is the same one we use for the proposal simulator"). This is a port of
// index.html's photoMaterial and its renderer setup, trimmed of what the game has no use for
// (the void's hole, the court's door in the glass, frost, the per-gap blade profiles, daylight):
//  - the scan's floor, walls and canopy are photographs, so they render UNLIT: albedo times the
//    house light (plus a sliver of ambient), never re-lit by scene lights;
//  - every installed run is a vertical LINE LIGHT: the closed-form integral of the LEDs along it
//    (the same maths as the viewer), so a fitted run washes the column and floor the way the
//    viewer's strips do. 12 columns x 8 runs = 96 = the viewer's MAX_LIGHTS, one slot per run;
//  - the columns keep their glTF material with the viewer's roughness and env map;
//  - same renderer: sRGB out, ACES tone mapping, exposure 1, RoomEnvironment for the gloss.
export const MAX_LIGHTS = 96;
export const AMBIENT = 0.015;
export const HOUSE_LUX = 150;              // the photographs' floor illuminance (viewer's assumption)
export const LM_PER_PIXEL = 1088 / 60;     // ENTTEC 8PXA60: 1,088 lm/m at 60 px/m
export const PX_PER_M = 60;
const COLUMN_ROUGHNESS = 0.5;

export const lightPos = new Float32Array(MAX_LIGHTS * 4);
export const lightCol = new Float32Array(MAX_LIGHTS * 4);
export const photoMats = [];
export const columnMats = [];

export function setupRenderer(renderer, scene) {
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;
}

// door: the storage doorway cut out of the end wall (u along the wall, d into the room)
export function photoMaterial(src, hall) {
  const o = hall.origin, U = hall.u, N = hall.inRoom;
  const m = new THREE.ShaderMaterial({
    uniforms: {
      map: { value: src.map || null }, tint: { value: new THREE.Color(src.map ? 0xffffff : src.color) },
      alpha: { value: src.transparent ? src.opacity : 1.0 },
      house: { value: 1 }, ambient: { value: AMBIENT },
      nLights: { value: 0 }, lightPos: { value: lightPos }, lightCol: { value: lightCol },
      doorU: { value: hall.doorU }, doorD: { value: hall.doorD }, doorHalfW: { value: hall.doorW * 0.5 }, doorTop: { value: o.y + 3.0 }
    },
    vertexShader: `varying vec2 vUv; varying vec3 vPos;
      void main(){ vUv=uv; vec4 wp=modelMatrix*vec4(position,1.0); vPos=wp.xyz; gl_Position=projectionMatrix*viewMatrix*wp; }`,
    fragmentShader: `uniform sampler2D map; uniform vec3 tint; uniform float house, ambient, alpha; uniform int nLights;
      uniform vec4 lightPos[${MAX_LIGHTS}]; uniform vec4 lightCol[${MAX_LIGHTS}];
      uniform float doorU, doorD, doorHalfW, doorTop;
      varying vec2 vUv; varying vec3 vPos;
      void main(){
        // the doorway: nothing of the scan inside the door volume
        { vec3 q=vPos-vec3(${o.x},${o.y},${o.z}); float du=dot(q,vec3(${U.x},${U.y},${U.z})); float dd=dot(q,vec3(${N.x},${N.y},${N.z}));
          if(abs(du-doorU)<0.6 && abs(dd-doorD)<doorHalfW && vPos.y<doorTop) discard; }
        vec3 albedo=texture2D(map,vUv).rgb*tint;
        vec3 Nn=normalize(cross(dFdx(vPos),dFdy(vPos)));
        vec3 E=vec3(house+ambient);
        for(int i=0;i<${MAX_LIGHTS};i++){ if(i>=nLights)break;
          // closed-form diffuse integral of a vertical line of point sources (viewer's maths):
          // lightPos.xyz the segment's foot, lightCol.w its height, flux divided by the height
          vec3 v=lightPos[i].xyz-vPos; float h=max(lightCol[i].w,0.01);
          float hd2=max(v.x*v.x+v.z*v.z,2.5e-3); float c=dot(v,v); float e=v.y;
          float aN=dot(Nn,v); float bN=Nn.y;
          float t0=0.0, t1=h;
          if(bN>1e-6) t0=clamp(-aN/bN,0.0,h);
          else if(bN<-1e-6) t1=clamp(-aN/bN,0.0,h);
          else if(aN<=0.0) t1=t0;
          float k=(aN-bN*e)/hd2;
          float g0=(k*(t0+e)-bN)*inversesqrt(max(c+2.0*e*t0+t0*t0,1e-6));
          float g1=(k*(t1+e)-bN)*inversesqrt(max(c+2.0*e*t1+t1*t1,1e-6));
          float I=max(g1-g0,0.0)/h;
          E+=lightCol[i].rgb*I; }
        gl_FragColor=vec4(albedo*E,alpha);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
    side: THREE.DoubleSide, transparent: !!src.transparent, depthWrite: !src.transparent
  });
  m.name = src.name; photoMats.push(m); return m;
}

// the viewer's rule: photographs unlit, columns keep a lit gloss material
export function dressHall(gltfScene, hall) {
  gltfScene.traverse((o) => {
    if (!o.isMesh) return;
    const ms = Array.isArray(o.material) ? o.material : [o.material];
    const out = ms.map((m) => { if (/column/i.test(m.name || '')) { m.roughness = COLUMN_ROUGHNESS; m.envMapIntensity = 1 + AMBIENT; columnMats.push(m); return m; } return photoMaterial(m, hall); });
    o.material = Array.isArray(o.material) ? out : out[0];
  });
}

// the installed runs as line lights: one per run, its foot at the run's first point and its
// height the fitted length (the slots go in bottom to top, so the lit part is one segment)
const WHITE = new THREE.Color(1.0, 0.93, 0.82);   // 4000 K-ish, the strip's white die
export function updateRunLights(install) {
  let nl = 0;
  const scale = LM_PER_PIXEL / (4 * Math.PI) / HOUSE_LUX;
  for (const run of install.runs) {
    if (nl >= MAX_LIGHTS) break;
    let n = 0; for (const s of run.slots) { if (install.fitted.has(s.id)) n++; else break; }
    if (!n) continue;
    const h = n * 1.5, px = h * PX_PER_M, foot = run.points[0];
    lightPos[nl * 4] = foot.x; lightPos[nl * 4 + 1] = foot.y; lightPos[nl * 4 + 2] = foot.z; lightPos[nl * 4 + 3] = 0;
    lightCol[nl * 4] = WHITE.r * px * scale; lightCol[nl * 4 + 1] = WHITE.g * px * scale; lightCol[nl * 4 + 2] = WHITE.b * px * scale; lightCol[nl * 4 + 3] = h;
    nl++;
  }
  for (const m of photoMats) { m.uniforms.nLights.value = nl; m.uniformsNeedUpdate = true; }
  return nl;
}
