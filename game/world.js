import * as THREE from 'three';

export const HALL = {
  origin: new THREE.Vector3(-54.907447, -1.43545, 3.040286),
  // (Lloyd, 2026-09-04: "the camera is literally moving towards one of the walls") these two
  // MUST be unit length and perpendicular: collideWorld goes world -> hall -> world every frame,
  // and a basis 0.0001 short slid every mover 0.6 mm towards the d=0 wall per pass, with no input
  u: new THREE.Vector3(0.975681, 0, 0.219196).normalize(),
  inRoom: new THREE.Vector3(0.219196, 0, -0.975681).normalize(),
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

export function hallPoint(u, d, y = HALL.floorY) { return hallToWorld(u, d, y); }
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

export function makeHallBox(scene, u, d, y, len, dep, h, mat) {
  const mesh = makeBox(new THREE.Vector3(len, h, dep), hallToWorld(u, d, y), mat);
  // (2026-09-04, found by the seal sweep) the basis has to be right-handed or the quaternion comes
  // out degenerate and the box stands unrotated on the world axes: (u, Y, inRoom) is left-handed
  // (u x Y = -inRoom), so every corridor box sat 12.7 degrees off the hall, 3.7 m out at its far
  // end, while the collider ran in the hall frame. Local z is -inRoom now; a box is symmetric
  const Y = new THREE.Vector3(0, 1, 0);
  mesh.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(HALL.u, Y, new THREE.Vector3().crossVectors(HALL.u, Y)));
  scene.add(mesh);
  return mesh;
}

// (Lloyd, 2026-09-04: "the wheels are clipping into the floor") the scanned floor is not level:
// it rises about 10 cm from the d=3 side to the d=12 side and 2 cm along u, while the lift, the
// crew and everything dropped stand on the flat HALL.floorY. Measure the scan's floor plane
// (a ray down at each of a grid of hall points), then rotate the whole scan about a floor point
// so that plane is horizontal and slide it so the floor sits exactly at HALL.floorY. Half a
// degree: the ceiling moves 11 cm sideways, the floor points move under a millimetre.
export function levelHall(hall) {
  hall.updateMatrixWorld(true);
  const ray = new THREE.Raycaster();
  const down = new THREE.Vector3(0, -1, 0);
  const pts = [];
  for (let u = 3; u <= 46; u += 4.3) {
    for (let d = 2.5; d <= 12.5; d += 2.5) {
      ray.set(hallToWorld(u, d, HALL.floorY + 1.0), down);
      const hit = ray.intersectObject(hall, true).find((h) => Math.abs(h.point.y - HALL.floorY) < 0.35);
      if (hit) pts.push([u, d, hit.point.y]);
    }
  }
  if (pts.length < 6) { console.warn('levelScan: floor not found, scan left as loaded'); return; }
  // least squares y = c + a u + b d
  let Suu = 0, Sud = 0, Sdd = 0, Su = 0, Sd = 0, Suy = 0, Sdy = 0, Sy = 0;
  const n = pts.length;
  for (const [u, d, y] of pts) { Suu += u * u; Sud += u * d; Sdd += d * d; Su += u; Sd += d; Suy += u * y; Sdy += d * y; Sy += y; }
  const M = new THREE.Matrix3().set(Suu, Sud, Su, Sud, Sdd, Sd, Su, Sd, n).invert();
  const abc = new THREE.Vector3(Suy, Sdy, Sy).applyMatrix3(M);
  const [a, b, c] = [abc.x, abc.y, abc.z];
  // the plane's upward normal in world axes, then the rotation that makes it vertical
  const normal = new THREE.Vector3(0, 1, 0).addScaledVector(HALL.u, -a).addScaledVector(HALL.inRoom, -b).normalize();
  const q = new THREE.Quaternion().setFromUnitVectors(normal, new THREE.Vector3(0, 1, 0));
  const pivot = hallToWorld(HALL.length * 0.5, HALL.depth * 0.5, c + a * HALL.length * 0.5 + b * HALL.depth * 0.5);
  // rotate the loaded scene about the pivot as one rigid thing, then drop it onto the datum
  const R = new THREE.Matrix4().makeRotationFromQuaternion(q);
  hall.applyMatrix4(new THREE.Matrix4().makeTranslation(pivot.x, pivot.y, pivot.z).multiply(R).multiply(new THREE.Matrix4().makeTranslation(-pivot.x, -pivot.y, -pivot.z)));
  hall.position.y += HALL.floorY - pivot.y;
  hall.updateMatrixWorld(true);
  world_levelling = { a, b, c, points: n };
}
let world_levelling = null;
export function scanLevelling() { return world_levelling; }

// (Lloyd, 2026-09-04) install mode runs inside the proposal sim, and the sim measures its own
// floor off the model. The datum is set from there so the two agree to the millimetre instead of
// both carrying a hard-coded -1.435.
export function setFloorY(y) { if (Number.isFinite(y)) HALL.floorY = y; }

// the world with nothing built yet: the datums and the room's plan, no scene objects. The hall
// itself (the scan, its levelling, its lights and its materials) belongs to whoever is hosting
// the game -- index.html in install mode -- and is filled in by the caller.
export function makeWorld(floorY = HALL.floorY) {
  return {
    floorY,
    columns: [],
    solids: [],
    // (Lloyd, 2026-09-04: make the storage space larger) 17 m x 9 m: two rows of six pallets
    // along the walls, a 4 m aisle between them for the lifts, the skip out through the end
    storage: hallToWorld(57.5, 7.5, floorY),
    skip: hallToWorld(68.6, 7.5, floorY),
    corridor: { u0: 48.9, u1: 66.0, d0: 3.0, d1: 12.0, skipD0: 6.0, skipD1: 9.0 },
    obstacles: []
  };
}

function leafMatFor() { return new THREE.MeshStandardMaterial({ color: 0x3a3f47, roughness: 0.7, metalness: 0.15 }); }
// a canvas with one word on it, for the sign and the column tags
function textTexture(text, w, h, fg, bg) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const g = c.getContext('2d');
  g.fillStyle = bg; g.fillRect(0, 0, w, h);
  g.fillStyle = fg; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.font = 'bold ' + Math.round(h * 0.62) + 'px Arial, Helvetica, sans-serif';
  g.fillText(text, w / 2, h / 2 + h * 0.03);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  return t;
}

// everything the game puts in the room: the invisible column colliders, the corridor and storage
// space behind the hall, its lights, the double doors and the skip. All of it goes into whatever
// `scene` is passed, so a host can hand in one group and drop the lot in a single remove().
export function buildProps(scene, world) {
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
  makeHallBox(scene, c.u1 + 0.12, (c.d0 + c.skipD0) * 0.5, world.floorY + 1.55, 0.24, c.skipD0 - c.d0, 3.1, wallMat);
  makeHallBox(scene, c.u1 + 0.12, (c.skipD1 + c.d1) * 0.5, world.floorY + 1.55, 0.24, c.d1 - c.skipD1, 3.1, wallMat);
  makeHallBox(scene, c.u1 + 0.12, midD, world.floorY + 3.05, 0.24, c.d1 - c.d0, 0.25, wallMat);
  for (const [u, d] of [[51.5, 5.5], [51.5, 9.5], [56, 5.5], [56, 9.5], [60.5, 5.5], [60.5, 9.5], [65, 7.5]]) {
    const l = new THREE.PointLight(0xffddb0, 2.2, 8, 1.7);
    l.position.copy(hallToWorld(u, d, world.floorY + 2.65));
    scene.add(l);
  }
  const doorFrame = new THREE.MeshStandardMaterial({ color: 0xb9a887, roughness: 0.65 });
  // (Lloyd, 2026-09-05: "some weird bar above the doors") the frame stands in the hall frame like
  // every other box; the header used to lie on the world x axis, 12.7 degrees off the wall
  makeHallBox(scene, 48.6, 6.15, world.floorY + 1.5, 0.25, 0.15, 3, doorFrame);
  makeHallBox(scene, 48.6, 8.85, world.floorY + 1.5, 0.25, 0.15, 3, doorFrame);
  makeHallBox(scene, 48.6, 7.5, world.floorY + 3, 0.25, 2.85, 0.15, doorFrame);
  // (Lloyd, 2026-09-06: "a sign above the doors that says storage") a lit board over the header,
  // facing the hall, standing in the hall frame like the frame itself
  makeHallBox(scene, 48.55, 7.5, world.floorY + 3.42, 0.06, 1.9, 0.5, leafMatFor());
  const sign = new THREE.Mesh(new THREE.PlaneGeometry(1.8, 0.42), new THREE.MeshBasicMaterial({ map: textTexture('STORAGE', 512, 120, '#f4efe2', '#1d2128'), toneMapped: false }));
  sign.position.copy(hallToWorld(48.5, 7.5, world.floorY + 3.42));
  sign.lookAt(sign.position.clone().sub(HALL.u));   // plane normal along -u: read from inside the hall
  scene.add(sign);
  world.sign = sign;

  // (Lloyd, 2026-09-06: "we need to know which column is which") every column wears its label
  // twice, a tag on the room side and one on the wall side, above head height so it reads from
  // the floor and from the deck. Sprites: they face whoever is looking
  const labelTex = new Map();
  world.tags = [];
  for (const col of world.columns) {
    if (!labelTex.has(col.label)) labelTex.set(col.label, textTexture(col.label, 256, 128, '#ffd166', 'rgba(8,10,14,0.85)'));
    const hd = worldToHall(col.pos);
    for (const dir of [1, -1]) {
      const tag = new THREE.Sprite(new THREE.SpriteMaterial({ map: labelTex.get(col.label), toneMapped: false, depthWrite: false }));
      tag.scale.set(0.9, 0.45, 1);
      tag.position.copy(hallToWorld(hd.u, hd.d + dir * (col.radius + 0.12), world.floorY + 3.0));
      tag.renderOrder = 5;
      tag.userData.label = col.label;
      scene.add(tag);
      world.tags.push(tag);
    }
  }

  // (Lloyd, 2026-09-04) the storage doorway is a pair of DOUBLE DOORS: two 1.25 m leaves hinged on
  // the jambs, swinging into the corridor as anyone (or the lift) comes within reach, closing
  // behind them. A shut pair is a wall; open leaves are passed freely
  const leafMat = leafMatFor();
  world.doors = [];
  for (const side of [-1, 1]) {
    const hinge = new THREE.Group();
    // hung 0.3 m on the HALL side of the wall line: the model's end wall is solid and one-sided,
    // so doors behind it would be hidden from the hall (and the wall is see-through from the corridor)
    hinge.position.copy(hallToWorld(HALL.doorU - 0.3, HALL.doorD + side * HALL.doorW * 0.5, world.floorY));
    hinge.rotation.y = -Math.atan2(HALL.u.z, HALL.u.x);   // local x along the wall (u), local z = -inRoom
    const leaf = new THREE.Mesh(new THREE.BoxGeometry(0.06, 2.95, HALL.doorW * 0.5 - 0.02), leafMat);
    leaf.position.set(0, 1.5, side * (HALL.doorW * 0.25));
    const bar = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.05, 0.6), doorFrame);
    bar.position.set(0.06, 1.05, side * (HALL.doorW * 0.25 + 0.2));
    hinge.add(leaf, bar);
    scene.add(hinge);
    world.doors.push({ hinge, side, open: 0, yaw0: hinge.rotation.y });
  }
  world.doorCentre = hallToWorld(HALL.doorU, HALL.doorD, world.floorY);
  const skip = new THREE.Mesh(new THREE.BoxGeometry(3.2, 1.1, 1.8), new THREE.MeshStandardMaterial({ color: 0x40556a, roughness: 0.8 }));
  skip.position.copy(world.skip).y += 0.55;
  scene.add(skip);
  world.skipMesh = skip;
  return world;
}

// the doors swing for whoever is near: open within 3 m of the doorway, shut again past it
export function updateDoors(dt, world, points) {
  if (!world.doors) return;
  const near = points.some((p) => p.distanceTo(world.doorCentre) < 3.2);
  for (const d of world.doors) {
    d.open = THREE.MathUtils.clamp(d.open + (near ? dt * 1.6 : -dt * 1.1), 0, 1);
    const k = d.open < 0.5 ? 2 * d.open * d.open : 1 - 2 * (1 - d.open) * (1 - d.open);
    d.hinge.rotation.y = d.yaw0 + d.side * k * 1.75;   // the wall's own yaw plus 100 degrees, each leaf away from the middle, into the corridor
    // (Lloyd, 2026-09-06: "we shouldn't be able to clip through the doors") the leaf on the plan:
    // hinge (0.3 m hall side of the wall line, at the jamb) to tip, 1.25 m along local z rotated
    // by the swing. Local z is -inRoom, so the tip's d runs back towards the middle when shut
    const th = d.side * k * 1.75;
    d.seg = { u0: HALL.doorU - 0.3, d0: HALL.doorD + d.side * HALL.doorW * 0.5,
              u1: HALL.doorU - 0.3 + d.side * 1.25 * Math.sin(th), d1: HALL.doorD + d.side * HALL.doorW * 0.5 - d.side * 1.25 * Math.cos(th) };
  }
  world.doorsShut = world.doors.every((d) => d.open < 0.15);
  // the doorway counts as open only once both leaves have swung past about 85 degrees; until then
  // nobody crosses the line, however fast they arrive (the sprint used to tunnel through a
  // leaf that had barely started to move)
  world.doorsClear = world.doors.every((d) => d.open >= 0.75);
}

// the last resolved side of the door line for every mover, so a step that lands on the far side
// of doors that are not yet clear is put back where it came from. A jump of over 2 m is a
// teleport (a spawn, a pack-up), not a step, and is let through
const lastSide = new WeakMap();

// (Lloyd, 2026-09-04: "the camera is literally moving towards one of the walls") one pass of
// pushes left a mover still inside the next circle or the wall, and the next frame's pass moved
// it again: a slide with no input. Now the walls and circles are settled together, a few passes
// per call, so a frame ends with nothing left to push, and the callers only collide when they
// actually moved
export function collideWorld(pos, radius, world, ignore) {
  for (let pass = 0; pass < 4; pass++) collideOnce(pos, radius, world, ignore);
}
// (Lloyd, 2026-09-06: "show a proximity to nearby objects in the scissor lift icon, so we don't
// hit anything") a ring of probes around the chassis: each walks outward from the machine's edge
// in its own direction until the collider pushes it back, which is where a wall, a column, a
// door, a pallet or another machine stands. Returns one entry per direction, `a` in the chassis
// frame (0 = forward, clockwise from above) and `dist` in metres from the edge, or null when
// nothing is within `reach`
export function proximity(world, lift, n = 16, reach = 1.6, ignore = []) {
  const out = [];
  const q = new THREE.Vector3();
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2;
    const fx = Math.cos(a), fz = Math.sin(a);                       // chassis frame: x forward, z right
    const r0 = Math.min(1.25 / Math.max(Math.abs(fx), 1e-6), 0.6 / Math.max(Math.abs(fz), 1e-6));   // the chassis edge in this direction
    const dir = new THREE.Vector3(fx, 0, fz).applyAxisAngle(new THREE.Vector3(0, 1, 0), lift.yaw);
    let dist = null;
    for (let r = r0 + 0.05; r <= r0 + reach; r += 0.1) {
      q.copy(lift.pos).addScaledVector(dir, r); q.y = world.floorY;
      const x = q.x, z = q.z;
      collideWorld(q, 0.05, world, [lift, lift.box, ...ignore]);
      if (Math.hypot(q.x - x, q.z - z) > 0.02) { dist = r - r0; break; }
    }
    out.push({ a, dist });
  }
  return out;
}

// push a point (hall coords) out of a capsule of radius r around the segment
function pushSeg(hd, r, seg) {
  const ax = seg.u1 - seg.u0, ay = seg.d1 - seg.d0;
  const l2 = ax * ax + ay * ay || 1e-9;
  const t = THREE.MathUtils.clamp(((hd.u - seg.u0) * ax + (hd.d - seg.d0) * ay) / l2, 0, 1);
  const cx = seg.u0 + ax * t, cy = seg.d0 + ay * t;
  let dx = hd.u - cx, dy = hd.d - cy;
  const len = Math.hypot(dx, dy);
  if (len >= r) return;
  if (len < 1e-4) { dx = -ay; dy = ax; const n = Math.hypot(dx, dy) || 1; dx /= n; dy /= n; } else { dx /= len; dy /= len; }
  hd.u = cx + dx * r; hd.d = cy + dy * r;
}
function collideOnce(pos, radius, world, ignore) {
  const hd = worldToHall(pos);
  const inDoor = Math.abs(hd.u - HALL.doorU) < 1.2 && Math.abs(hd.d - HALL.doorD) < HALL.doorW * 0.5 - radius + 0.02;
  // the jambs: a mover in the wall's thickness but outside the opening is put back on its own side
  if (!inDoor && Math.abs(hd.u - HALL.doorU) < radius) hd.u = hd.u < HALL.doorU ? HALL.doorU - radius : HALL.doorU + radius;
  const inCorridor = hd.u >= HALL.length - 0.1;
  // shut doors are a wall: nothing crosses the door line until they have swung clear
  const prev = lastSide.get(pos);
  let inHall = hd.u < HALL.doorU;
  if (world.doors && !world.doorsClear && prev && Math.abs(prev.u - hd.u) < 2 && prev.inHall !== inHall) inHall = prev.inHall;
  if (world.doors && !world.doorsClear && inDoor) { if (inHall && hd.u > HALL.doorU - radius - 0.05) hd.u = HALL.doorU - radius - 0.05; if (!inHall && hd.u < HALL.doorU + radius + 0.05) hd.u = HALL.doorU + radius + 0.05; }
  // the leaves themselves: a mover circle is pushed off each leaf's segment on the plan
  if (world.doors) for (const d of world.doors) if (d.seg) pushSeg(hd, radius + 0.04, d.seg);
  hd.u = THREE.MathUtils.clamp(hd.u, -0.8, 72);
  if (inCorridor) {
    const c = world.corridor;
    hd.d = THREE.MathUtils.clamp(hd.d, c.d0 + radius, c.d1 - radius);
    // the opening to the skip is a person-sized one: a lift (radius 0.9) stops at the end wall
    if (hd.u > c.u1 - radius && (radius > 0.5 || hd.d < c.skipD0 || hd.d > c.skipD1)) hd.u = c.u1 - radius;
  } else {
    hd.d = THREE.MathUtils.clamp(hd.d, radius, HALL.depth - radius);
    if (hd.u > HALL.length - radius && !inDoor) hd.u = HALL.length - radius;
  }
  lastSide.set(pos, { u: hd.u, inHall: hd.u < HALL.doorU });
  pos.copy(hallToWorld(hd.u, hd.d, pos.y));
  const push = (cx, cz, r) => {
    const a = new THREE.Vector2(pos.x - cx, pos.z - cz);
    const min = r + radius;
    const len = a.length();
    if (len > 0.001 && len < min) { a.setLength(min - len); pos.x += a.x; pos.z += a.y; }
  };
  for (const col of world.columns) push(col.pos.x, col.pos.z, col.radius);
  // (Lloyd, 2026-09-04: nothing clips into anything) everything standing on the floor is a
  // circle on the plan: pallets, boxes, bags, lifts (two circles), the skip. `ignore` names the
  // things the mover is part of or carrying
  for (const o of world.obstacles) { if (ignore && ignore.includes(o.ref)) continue; push(o.x, o.z, o.r); }
  pos.y = Math.max(pos.y, world.floorY);
}
