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
//  - (2026-09-07) the viewer's three new render terms, ported line for line: the line is LAMBERTIAN
//    off its face rather than isotropic, the carpet's first bounce comes back up the walls, and the
//    columns shadow each other. Same constants, same closed form, same comments; see the viewer's
//    photoMaterial and AGENTS.md "The lighting render".
//  - the columns keep their glTF material with the viewer's roughness and env map;
//  - same renderer: sRGB out, ACES tone mapping, exposure 1, RoomEnvironment for the gloss.
export const MAX_LIGHTS = 96;
export const AMBIENT = 0.015;
export const HOUSE_LUX = 150;              // the photographs' floor illuminance (viewer's assumption)
export const LM_PER_PIXEL = 1088 / 60;     // ENTTEC 8PXA60: 1,088 lm/m at 60 px/m
export const PX_PER_M = 60;
const COLUMN_ROUGHNESS = 0.5;
// the shaft radius the columns shadow with: the fin valley the runs ride, plus the fins' mean
// 100 mm proud (50 at the foot, 150 at the ceiling). The viewer measures it off runs.json; the
// game's slots are built on the same polylines, so the same figure stands.
export const COL_R = 0.26;
// the carpet's diffuse reflectance and colour, measured off the floor photograph the scan carries
// (the viewer samples that texture at load; this is that measurement, so the game and the viewer
// bounce the same red). Deep red wool: 23% in the red channel, 6% green, 7% blue.
export const FLOOR_ALB = [0.228, 0.059, 0.070];
// the stone walls' tone, the viewer's WALL_TINT (Lloyd's 2026-09-07 pick: the bake landed on the
// daylight photograph's stone, warm grey, about three times lighter than the night scan)
export const WALL_TINT = [3.3, 4.7, 4.7];
// the ashlar the viewer draws on the walls (index.html STONE): running bond, half-block stagger,
// courses and blocks measured off the daylight photographs, pale joints; same numbers here
export const STONE = { course: 0.285, block: 0.710, joint: 0.014 };
// the limestone tile the viewer paints the stones with (tools/stone.jpg, 1 m per repeat)
const STONE_TEX = (() => { const t = new THREE.TextureLoader().load('tools/stone.jpg'); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8; return t; })();

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
  const walls = (src.name || '') === 'walls';
  // the wall atlas ships with a plain linear sampler; the ashlar samples it three mips soft
  if (walls && src.map) { src.map.minFilter = THREE.LinearMipmapLinearFilter; src.map.generateMipmaps = true; src.map.anisotropy = 8; src.map.needsUpdate = true; }
  const m = new THREE.ShaderMaterial({
    uniforms: {
      map: { value: src.map || null }, stoneMap: { value: STONE_TEX }, tint: { value: (src.name || '') === 'walls' ? new THREE.Color().setRGB(...WALL_TINT) : new THREE.Color(src.map ? 0xffffff : src.color) },
      alpha: { value: src.transparent ? src.opacity : 1.0 },
      house: { value: 1 }, ambient: { value: AMBIENT },
      nLights: { value: 0 }, lightPos: { value: lightPos }, lightCol: { value: lightCol },
      bounceAlb: { value: new THREE.Vector3(FLOOR_ALB[0], FLOOR_ALB[1], FLOOR_ALB[2]) }, bounceY: { value: o.y },
      colR: { value: COL_R }, nOcc: { value: ('ontouchstart' in window) ? 1 : 2 },
      doorU: { value: hall.doorU }, doorD: { value: hall.doorD }, doorHalfW: { value: hall.doorW * 0.5 }, doorTop: { value: o.y + 3.0 }
    },
    vertexShader: `varying vec2 vUv; varying vec3 vPos;
      void main(){ vUv=uv; vec4 wp=modelMatrix*vec4(position,1.0); vPos=wp.xyz; gl_Position=projectionMatrix*viewMatrix*wp; }`,
    fragmentShader: `uniform sampler2D map, stoneMap; uniform vec3 tint; uniform float house, ambient, alpha; uniform int nLights;
      uniform vec4 lightPos[${MAX_LIGHTS}]; uniform vec4 lightCol[${MAX_LIGHTS}];
      uniform float doorU, doorD, doorHalfW, doorTop;
      uniform vec3 bounceAlb; uniform float bounceY, colR; uniform int nOcc;
      varying vec2 vUv; varying vec3 vPos;
      // the plan-view shadow test: the shafts are vertical and run the full height, so a column
      // occludes a light exactly when the segment from the fragment to it passes within the shaft
      // radius of that column's axis. Soft over half a radius: a 12 m line source is not a point.
      float occl(vec2 p, vec2 q, vec2 c, float r){
        vec2 pq=q-p, pc=c-p; float L2=max(dot(pq,pq),1e-6);
        float t=clamp(dot(pc,pq)/L2,0.0,1.0);
        return smoothstep(r*0.55, r*1.25, length(pc-pq*t));
      }
      void main(){
        // the doorway: nothing of the scan inside the door volume
        { vec3 q=vPos-vec3(${o.x},${o.y},${o.z}); float du=dot(q,vec3(${U.x},${U.y},${U.z})); float dd=dot(q,vec3(${N.x},${N.y},${N.z}));
          if(abs(du-doorU)<0.6 && abs(dd-doorD)<doorHalfW && vPos.y<doorTop) discard; }
        vec3 Nn=normalize(cross(dFdx(vPos),dFdy(vPos)));
        vec3 albedo=texture2D(map,vUv).rgb*tint;
        ${walls ? `{
         // THE ASHLAR, the viewer's block line for line (index.html, "THE STONE COURSING"): the
         // bake three mips soft for its colour, courses up from the carpet, blocks along the wall
         // the face belongs to, joints box-filtered over the pixel footprint
         vec3 bake=texture2D(map,vUv,2.5).rgb*tint;
         float dark=smoothstep(0.010,0.022,dot(bake,vec3(0.3333)));
         vec3 q=vPos-vec3(${o.x},${o.y},${o.z});
         float su=dot(q,vec3(${U.x},${U.y},${U.z})), sd=dot(q,vec3(${N.x},${N.y},${N.z})), sy=q.y;
         float along=abs(dot(Nn,vec3(${U.x},${U.y},${U.z})))<0.7?su:sd;
         if(abs(Nn.y)<0.5){
          float ci=floor(sy/${STONE.course}); float dy=abs(sy-(ci+0.5)*${STONE.course});
          float ax=along+${STONE.block * 0.5}*mod(ci,2.0); float bi=floor(ax/${STONE.block}); float dx=abs(ax-(bi+0.5)*${STONE.block});
          float ey=${STONE.course * 0.5}-dy, ex=${STONE.block * 0.5}-dx;
          float ay=max(fwidth(sy),1e-4), ax2=max(fwidth(along),1e-4);
          float jy=clamp((${STONE.joint * 0.5}-ey+ay*0.5)/ay,0.0,1.0), jx=clamp((${STONE.joint * 0.5}-ex+ax2*0.5)/ax2,0.0,1.0);
          float joint=max(jx,jy);
          float hb=fract(sin(dot(vec2(bi,ci),vec2(12.9898,78.233)))*43758.5453);
          float hg=fract(sin(dot(floor(vec2(ax,sy)*160.0),vec2(39.3467,11.135)))*23421.631);
          float hb2=fract(sin(dot(vec2(bi,ci),vec2(26.651,44.317)))*19341.973);
          vec2 suv=vec2(ax,sy)+vec2(hb*7.31,hb2*5.17);
          vec3 stoneCol=texture2D(stoneMap,suv).rgb*(0.86+0.28*hb)*(0.97+0.06*hg)*vec3(1.0+0.05*(hb-0.5),1.0,1.0-0.05*(hb-0.5));
          vec3 mortar=vec3(dot(stoneCol,vec3(0.3333)))*0.78*(0.92+0.16*hg);
          albedo=mix(stoneCol,mortar,joint)*mix(0.12,1.0,dark);
         } else albedo=texture2D(stoneMap,vec2(su,sd)).rgb*0.9*mix(0.12,1.0,dark);
        }` : ''}
        vec3 E=vec3(house+ambient);
        // the two column axes nearest this fragment, read out of the light list itself: a run
        // light sits on its column's axis and lightPos.w says which column it is, so the shadow
        // costs no uniform vectors of its own (the viewer's note about the 224-vector budget)
        vec2 oc0=vec2(0.0), oc1=vec2(0.0); float od0=1e12, od1=1e12, ow0=-1.0, ow1=-1.0;
        if(nOcc>0){ for(int i=0;i<${MAX_LIGHTS};i++){ if(i>=nLights)break;
          vec2 cxz=lightPos[i].xz; float w=lightPos[i].w; vec2 dd=cxz-vPos.xz; float d=dot(dd,dd);
          if(w==ow0){ od0=min(od0,d); }
          else if(w==ow1){ od1=min(od1,d); }
          else if(d<od0){ od1=od0; oc1=oc0; ow1=ow0; od0=d; oc0=cxz; ow0=w; }
          else if(d<od1){ od1=d; oc1=cxz; ow1=w; } } }
        for(int i=0;i<${MAX_LIGHTS};i++){ if(i>=nLights)break;
          // CLOSED-FORM DIFFUSE INTEGRAL OF A VERTICAL LAMBERTIAN LINE (the viewer's maths).
          // lightPos.xyz the segment's foot, lightCol.w its height, flux divided by the height.
          // The bar is a diffused FACE, so its intensity falls with the cosine of the angle off
          // that face: I = K B(azimuth) cos(elevation), and integrating over the sphere makes
          // K = Phi/pi^2, exactly 4/pi of the isotropic Phi/4pi, flux still conserved. cos(beta)
          // is rho/r with rho constant along a vertical segment, so the integral is the same one
          // over r^4 and still closes:
          //   int (aN + bN t) rho / r^4 dt = A u/(2 rho r^2) + A atan(u/rho)/(2 rho^2) - bN rho/(2 r^2)
          vec3 v=lightPos[i].xyz-vPos; float h=max(lightCol[i].w,0.01);
          float hd2=max(v.x*v.x+v.z*v.z,colR*colR*0.25); float rho=sqrt(hd2); float e=v.y;
          float aN=dot(Nn,v); float bN=Nn.y;
          float t0=0.0, t1=h;
          if(bN>1e-6) t0=clamp(-aN/bN,0.0,h);
          else if(bN<-1e-6) t1=clamp(-aN/bN,0.0,h);
          else if(aN<=0.0) t1=t0;
          float A=aN-bN*e, u0=t0+e, u1=t1+e;
          float r0=hd2+u0*u0, r1=hd2+u1*u1;
          float da=atan((u1-u0)*hd2, rho*(hd2+u0*u1));
          float I=max(A*(u1/r1-u0/r0)/(2.0*rho) + A*da/(2.0*hd2) - bN*rho*0.5*(1.0/r1-1.0/r0), 0.0)*(1.27323954/h);
          float sh=1.0;
          if(nOcc>0&&lightPos[i].w!=ow0) sh*=occl(vPos.xz,lightPos[i].xz,oc0,colR);
          if(nOcc>1&&lightPos[i].w!=ow1) sh*=occl(vPos.xz,lightPos[i].xz,oc1,colR);
          E+=lightCol[i].rgb*(I*sh);
          // THE FIRST BOUNCE. Half of a Lambertian face's flux leaves below the horizon (the
          // cosine is even in the elevation), and in this hall that half lands on the carpet,
          // which is deep red and throws deep red back up the walls. One virtual cosine emitter
          // per light, at the foot of its column on the floor, carrying 0.5 x the flux x the
          // carpet's albedo; its softening radius is the light's own mean height, which is
          // roughly how far its downward half spreads and keeps the term finite at the foot.
          // In these units the 0.5 share and the 4/pi come to 2 x bounceAlb.
          vec3 bw=vec3(lightPos[i].x,bounceY,lightPos[i].z)-vPos;
          float BR=max(lightPos[i].y+h*0.5-bounceY,0.25);
          float d2=dot(bw,bw)+BR*BR;
          float cs=max(-bw.y,0.0), cr=max(dot(Nn,bw),0.0);
          E+=lightCol[i].rgb*bounceAlb*(2.0*cs*cr/(d2*d2)); }
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
// which column a run belongs to, as the viewer packs it: a number in lightPos.w the shader
// compares for equality, so the shadow test can skip a light's own shaft. The viewer uses
// (column index + 0.5)/16 because that value doubles as its blade-texture row; the game has no
// blade rows, so it is the identity alone.
const COLUMN_W = new Map();
function columnW(name) { if (!COLUMN_W.has(name)) COLUMN_W.set(name, (COLUMN_W.size + 0.5) / 16); return COLUMN_W.get(name); }
export function updateRunLights(install) {
  let nl = 0;
  const scale = LM_PER_PIXEL / (4 * Math.PI) / HOUSE_LUX;
  for (const run of install.runs) {
    if (nl >= MAX_LIGHTS) break;
    let n = 0; for (const s of run.slots) { if (install.fitted.has(s.id)) n++; else break; }
    if (!n) continue;
    const h = n * 1.5, px = h * PX_PER_M, foot = run.points[0];
    lightPos[nl * 4] = foot.x; lightPos[nl * 4 + 1] = foot.y; lightPos[nl * 4 + 2] = foot.z; lightPos[nl * 4 + 3] = columnW(run.column);
    lightCol[nl * 4] = WHITE.r * px * scale; lightCol[nl * 4 + 1] = WHITE.g * px * scale; lightCol[nl * 4 + 2] = WHITE.b * px * scale; lightCol[nl * 4 + 3] = h;
    nl++;
  }
  for (const m of photoMats) { m.uniforms.nLights.value = nl; m.uniformsNeedUpdate = true; }
  return nl;
}
