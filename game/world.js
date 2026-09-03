import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export const HALL = {
  origin: new THREE.Vector3(-54.907447, -1.43545, 3.040286),
  u: new THREE.Vector3(0.975681, 0, 0.219196),
  inRoom: new THREE.Vector3(0.219186, 0, -0.975639),
  floorY: -1.435,
  length: 48.9,
  depth: 15,
  ceiling: 12.2,
  doorU: 48.9,
  doorD: 7.5,
  doorW: 2.5
};

export const COLUMN_FEET = [
  [7.71,3.82],[7.53,11.41],[14.94,3.86],[14.88,11.29],[22.3,3.86],[22.17,11.33],
  [29.67,3.77],[29.96,11.15],[37.18,3.84],[36.82,11.52],[44.54,3.80],[44.23,11.27]
];

export function hallToWorld(u, d, y = HALL.floorY) {
  return HALL.origin.clone().addScaledVector(HALL.u, u).addScaledVector(HALL.inRoom, d).setY(y);
}

export function worldToHall(p) {
  const v = p.clone().sub(HALL.origin);
  return { u: v.dot(HALL.u), d: v.dot(HALL.inRoom) };
}

function makeBox(size, pos, mat) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(size.x, size.y, size.z), mat);
  mesh.position.copy(pos);
  return mesh;
}

function makeHallBox(scene, u, d, y, len, dep, h, mat) {
  const mesh = makeBox(new THREE.Vector3(len, h, dep), hallToWorld(u, d, y), mat);
  mesh.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(HALL.u, new THREE.Vector3(0, 1, 0), HALL.inRoom));
  scene.add(mesh);
  return mesh;
}

export async function loadWorld(scene) {
  const world = {
    floorY: HALL.floorY,
    columns: [],
    solids: [],
    storage: hallToWorld(52.2, 7.5, HALL.floorY),
    skip: hallToWorld(60.0, 7.5, HALL.floorY),
    corridor: { u0: 48.9, u1: 58.8, d0: 4.35, d1: 10.65, skipD0: 6.05, skipD1: 8.95 }
  };

  scene.background = new THREE.Color(0x08090b);
  scene.add(new THREE.HemisphereLight(0xdfe8ff, 0x1b1712, 0.85));
  const sun = new THREE.DirectionalLight(0xffffff, 1.4);
  sun.position.set(-18, 18, 8);
  scene.add(sun);
  const hallGlow = new THREE.PointLight(0xfff1d0, 5.5, 38, 1.8);
  hallGlow.position.copy(hallToWorld(43.5, 7.5, world.floorY + 5.2));
  scene.add(hallGlow);

  const gltf = await new GLTFLoader().loadAsync(new URL('../model.glb', import.meta.url).href);
  gltf.scene.traverse((o) => {
    if (!o.isMesh) return;
    o.castShadow = false;
    o.receiveShadow = false;
    const name = o.name.toLowerCase();
    if (name.includes('floor') || name.includes('flat-floor')) {
      const box = new THREE.Box3().setFromObject(o);
      world.floorY = box.min.y;
    }
  });
  scene.add(gltf.scene);

  const floor = new THREE.GridHelper(62, 62, 0x3b3f48, 0x20232a);
  floor.position.y = world.floorY + 0.01;
  scene.add(floor);

  const columnMat = new THREE.MeshStandardMaterial({ color: 0x2b3036, roughness: 0.8 });
  for (const [i, foot] of COLUMN_FEET.entries()) {
    const pos = hallToWorld(foot[0], foot[1], world.floorY + HALL.ceiling * 0.5);
    const mesh = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.55, HALL.ceiling, 20), columnMat);
    mesh.position.copy(pos);
    mesh.visible = false;
    mesh.userData.label = (i % 2 ? 'S' : 'N') + (Math.floor(i / 2) + 1);
    scene.add(mesh);
    world.columns.push({ label: mesh.userData.label, pos: hallToWorld(foot[0], foot[1], world.floorY), radius: 0.55, mesh });
  }

  const wallMat = new THREE.MeshStandardMaterial({ color: 0x141820, roughness: 0.9 });
  const floorMat = new THREE.MeshStandardMaterial({ color: 0x22262d, roughness: 0.85 });
  const c = world.corridor;
  const midU = (c.u0 + c.u1) * 0.5;
  const midD = (c.d0 + c.d1) * 0.5;
  makeHallBox(scene, midU, midD, world.floorY - 0.06, c.u1 - c.u0, c.d1 - c.d0, 0.12, floorMat);
  makeHallBox(scene, midU, c.d0 - 0.12, world.floorY + 1.55, c.u1 - c.u0, 0.24, 3.1, wallMat);
  makeHallBox(scene, midU, c.d1 + 0.12, world.floorY + 1.55, c.u1 - c.u0, 0.24, 3.1, wallMat);
  makeHallBox(scene, midU, midD, world.floorY + 3.14, c.u1 - c.u0, c.d1 - c.d0, 0.22, wallMat);
  makeHallBox(scene, c.u1 + 0.12, 5.15, world.floorY + 1.55, 0.24, 1.6, 3.1, wallMat);
  makeHallBox(scene, c.u1 + 0.12, 9.85, world.floorY + 1.55, 0.24, 1.6, 3.1, wallMat);
  makeHallBox(scene, c.u1 + 0.12, midD, world.floorY + 3.05, 0.24, c.d1 - c.d0, 0.25, wallMat);
  for (const [u, d] of [[50.4, 5.2], [53.2, 9.4], [56.5, 6.0]]) {
    const l = new THREE.PointLight(0xffddb0, 2.2, 8, 1.7);
    l.position.copy(hallToWorld(u, d, world.floorY + 2.65));
    scene.add(l);
  }
  const doorFrame = new THREE.MeshStandardMaterial({ color: 0xb9a887, roughness: 0.65 });
  scene.add(makeBox(new THREE.Vector3(0.25, 3, 0.15), hallToWorld(48.9, 6.15, world.floorY + 1.5), doorFrame));
  scene.add(makeBox(new THREE.Vector3(0.25, 3, 0.15), hallToWorld(48.9, 8.85, world.floorY + 1.5), doorFrame));
  scene.add(makeBox(new THREE.Vector3(2.7, 0.15, 0.15), hallToWorld(48.9, 7.5, world.floorY + 3), doorFrame));

  const skip = new THREE.Mesh(new THREE.BoxGeometry(3.2, 1.1, 1.8), new THREE.MeshStandardMaterial({ color: 0x40556a, roughness: 0.8 }));
  skip.position.copy(world.skip).y += 0.55;
  scene.add(skip);
  world.skipMesh = skip;
  return world;
}

export function collideWorld(pos, radius, world) {
  const hd = worldToHall(pos);
  const inDoor = Math.abs(hd.u - HALL.doorU) < 1.2 && Math.abs(hd.d - HALL.doorD) < HALL.doorW * 0.5;
  const inCorridor = hd.u >= HALL.length - 0.1;
  hd.u = THREE.MathUtils.clamp(hd.u, -0.8, 61);
  if (inCorridor) {
    const c = world.corridor;
    hd.d = THREE.MathUtils.clamp(hd.d, c.d0 + radius, c.d1 - radius);
    if (hd.u > c.u1 - radius && (hd.d < c.skipD0 || hd.d > c.skipD1)) hd.u = c.u1 - radius;
  } else {
    hd.d = THREE.MathUtils.clamp(hd.d, radius, HALL.depth - radius);
    if (hd.u > HALL.length - radius && !inDoor) hd.u = HALL.length - radius;
  }
  pos.copy(hallToWorld(hd.u, hd.d, pos.y));
  for (const col of world.columns) {
    const a = new THREE.Vector2(pos.x - col.pos.x, pos.z - col.pos.z);
    const min = col.radius + radius;
    const len = a.length();
    if (len > 0.001 && len < min) {
      a.setLength(min - len);
      pos.x += a.x;
      pos.z += a.y;
    }
  }
  pos.y = Math.max(pos.y, world.floorY);
}
