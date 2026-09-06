import * as THREE from 'three';
import { hallToWorld, worldToHall, hallQuat, snapSheet, sheetSpotWhy, laySheet, liftSheetUp, SHEET, HALL } from './world.js';

const COLUMNS = ['N1','N2','N3','N4','N5','N6','S1','S2','S3','S4','S5','S6'];
const BOX = { x: 0.5, y: 0.34, z: 0.42 };
const STACK_FULL = 30;                 // sheets on a full pallet of ply: 30 x 18 mm = 0.54 m
const SHEET_REACH = 3.8;               // how far from your feet a sheet may be laid
const SHEET_TAKE = 3.4;                // how far a laid sheet can be picked up from

function mat(color, roughness = 0.75, extra = {}) {
  return new THREE.MeshStandardMaterial({ color, roughness, ...extra });
}

function meshBox(color, sx, sy, sz, extra = {}) {
  return new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), mat(color, 0.75, extra));
}

function makeLabel(text) {
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 128;
  const g = canvas.getContext('2d');
  g.fillStyle = '#111318';
  g.fillRect(0, 0, canvas.width, canvas.height);
  g.strokeStyle = '#b9a887';
  g.lineWidth = 8;
  g.strokeRect(8, 8, canvas.width - 16, canvas.height - 16);
  g.fillStyle = '#f1eee5';
  g.font = '700 72px IBM Plex Sans, Arial, sans-serif';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.fillText(text, 128, 64);
  const tex = new THREE.CanvasTexture(canvas);
  const label = new THREE.Mesh(new THREE.PlaneGeometry(0.72, 0.36), new THREE.MeshBasicMaterial({ map: tex }));
  label.position.set(0, 0.92, -0.54);
  label.userData.texture = tex;
  return label;
}

function makePallet(column) {
  const group = new THREE.Group();
  const wood = mat(0x6b4d2e);
  for (const z of [-0.38, 0, 0.38]) {
    const slat = new THREE.Mesh(new THREE.BoxGeometry(1.25, 0.08, 0.18), wood);
    slat.position.set(0, 0.04, z);
    group.add(slat);
  }
  const boxes = [];
  for (let y = 0; y < 2; y++) {
    for (let z = 0; z < 2; z++) {
      for (let x = 0; x < 2; x++) {
        const b = meshBox(0x9a7b55, BOX.x, BOX.y, BOX.z);
        b.position.set((x - 0.5) * 0.55, 0.22 + y * 0.37, (z - 0.5) * 0.46);
        group.add(b);
        boxes.push(b);
      }
    }
  }
  group.add(makeLabel(column));
  return { group, boxes };
}

// (Lloyd, 2026-09-06: "we also need to put down floor protection before we can drive the scissor
// lift on the carpet") a pallet of plywood floor protection: bearers under a stack of 2400 x 1200
// sheets, standing square to the hall, its long side along u or across it. One box mesh is scaled
// to the count, and hidden when the last sheet has gone
function makeStack(along) {
  const group = new THREE.Group();
  const wood = mat(0x6b4d2e);
  for (const z of [-0.45, 0, 0.45]) {
    const bearer = new THREE.Mesh(new THREE.BoxGeometry(SHEET.long, 0.09, 0.16), wood);
    bearer.position.set(0, 0.045, z);
    group.add(bearer);
  }
  const pile = new THREE.Mesh(new THREE.BoxGeometry(SHEET.long, STACK_FULL * SHEET.thick, SHEET.short), mat(0xc9a76a, 0.8));
  group.add(pile);
  const label = makeLabel('PLY');
  label.position.set(0, 0.95, -0.62);
  group.add(label);
  group.quaternion.copy(sheetQuat(along));   // square to the hall, turned when its long side runs across the corridor
  return { group, pile, quat: group.quaternion.clone() };
}
function updateStackPile(stack) {
  const n = Math.max(0, stack.sheets);
  stack.pile.visible = n > 0;
  stack.pile.scale.y = Math.max(0.001, n / STACK_FULL);
  stack.pile.position.y = 0.09 + n * SHEET.thick * 0.5;
}

// a sheet in the hands: 20 kg of ply takes both, so it is carried low and nearly on edge, leaning
// back against the chest. You see its top edge along the bottom of the picture and nothing else
// (Lloyd's standing rule: nothing a hand holds may fill the view)
function makeCarrySheet() {
  const group = new THREE.Group();
  const board = new THREE.Mesh(new THREE.BoxGeometry(SHEET.long, SHEET.thick, SHEET.short), mat(0xc9a76a, 0.8));
  group.add(board);
  group.position.set(0.0, -1.16, -1.05);
  group.rotation.set(-1.45, 0, 0.05);
  return group;
}

function makeJack() {
  const group = new THREE.Group();
  const red = mat(0xaa2f2a, 0.62);
  const dark = mat(0x30343a, 0.65);
  for (const x of [-0.28, 0.28]) {
    const tine = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.12, 1.35), red);
    tine.position.set(x, 0.08, -0.28);
    group.add(tine);
  }
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.78, 0.22, 0.35), red);
  body.position.set(0, 0.16, 0.48);
  group.add(body);
  const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 1.25, 10), dark);
  handle.position.set(0, 0.75, 0.74);
  handle.rotation.x = -0.42;
  group.add(handle);
  return group;
}

function makeBag() {
  const bag = meshBox(0x273b2d, 0.65, 0.82, 0.65);
  bag.scale.set(1, 1, 0.85);
  return bag;
}

function makeBoxObject(lights = 8) {
  const mesh = meshBox(0x9a7b55, BOX.x, BOX.y, BOX.z);
  return { type: 'box', lights, carried: false, disposed: false, mesh };
}

// (Lloyd, 2026-09-05) the light in hand is the pixel bar itself: 20 x 45 x 1500, black anodised,
// black face, no glow (it is not powered); wrapped, a translucent sleeve sits over it
function makeBarMesh(wrapped) {
  const bar = new THREE.Mesh(new THREE.BoxGeometry(0.045, 0.02, 1.5), mat(0x0c0c0e, 0.5, { metalness: 0.55 }));
  const face = new THREE.Mesh(new THREE.BoxGeometry(0.001, 0.018, 1.49), mat(0x08080a, 0.35));
  face.position.x = 0.0225; bar.add(face);
  if (wrapped) { const sleeve = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.035, 1.52), mat(0xf4f4ee, 0.25, { transparent: true, opacity: 0.5 })); bar.add(sleeve); }
  return bar;
}
function makeCarryLight(wrapped) {
  const group = new THREE.Group();
  const bar = makeBarMesh(wrapped);
  group.add(bar);
  // held low and to the right, slanted away, so it does not fill the view (Lloyd's phone shot)
  group.position.set(0.42, -0.62, -1.0);
  group.rotation.set(0.35, -0.55, 0.1);
  return group;
}

// what a body rests its centre on, and how wide it is on the plan
const REST = { box: 0.17, emptyBox: 0.17, bag: 0.41, wrap: 0.04, light: 0.012, wrapped: 0.02, jack: 0 };
const RADIUS = { box: 0.4, emptyBox: 0.4, bag: 0.45, wrap: 0.3, light: 0.3, wrapped: 0.3, jack: 0.5 };
const TOPS = { box: 0.34, emptyBox: 0.34, bag: 0.82 };   // what can be stood on, and how tall it is
// (Lloyd, 2026-09-06: "all the objects need to have collision ... the lights can't clip when they
// are dropped onto the scissor lift") the deck is a fenced tray: a body that lands on it is kept
// inside the rails by its own half-extents (x along the chassis, z across, after the bar is turned
// to lie along the deck), and a body that misses the deck lands on the chassis tray or is pushed
// clear of the machine, never through it
const DECK_WIN = { x: 1.2, z: 0.55 };                                  // inside the rail posts
const HALF = { box: { x: 0.3, z: 0.25 }, emptyBox: { x: 0.3, z: 0.25 }, bag: { x: 0.3, z: 0.3 }, wrap: { x: 0.21, z: 0.17 }, light: { x: 0.76, z: 0.03 }, wrapped: { x: 0.76, z: 0.03 }, jack: { x: 0.6, z: 0.3 } };
const CHASSIS = { x: 1.2, z: 0.58, top: 0.76 };                        // the blue slab + tray, from lift.js build()
function restOf(o) { return REST[o.type] ?? 0.05; }

// the bodies that are loose right now: not carried, not in a bag, not the lift's own box
function bodiesOf(items) {
  const out = [];
  for (const b of items.boxes) if (!b.carried && !b.disposed && !b.onLift) out.push(b);
  for (const b of items.bags) if (!b.carried && !b.disposed) out.push(b);
  for (const w of items.wraps) if (!w.carried && !w.bagged) out.push(w);
  for (const l of items.lights) if (!l.carried) out.push(l);
  if (items.jack && !items.jack.held && !items.jack.by) out.push(items.jack);
  for (const j of items.jacks || []) if (!j.held && !j.by) out.push(j);
  return out;
}

// one body, one step: gravity, the fall, the landing, the slide to rest. A body that lands on
// the deck is captured in deck coordinates and rides the machine until it is picked up again
function stepBody(o, dt, items, lift, others) {
  if (!o.vel) o.vel = new THREE.Vector3();
  const m = o.mesh, rest = restOf(o), floorY = items.world.floorY;
  if (o.deck) {   // riding the deck
    const p = lift.deckPoint(o.deck.x, o.deck.y);
    m.position.set(p.x, lift.floorY + lift.deckY + lift.height + 0.07 + rest, p.z);
    m.rotation.y = (o.deckYaw || 0) + lift.yaw;
    return;
  }
  const v = o.vel;
  const y0 = m.position.y - rest;   // where the underside WAS: a surface counts if it was under it before this step, so a slow frame cannot tunnel through the deck
  v.y -= 9.8 * dt;
  m.position.addScaledVector(v, dt);
  // what is under it: the floor, the deck when it is over the deck plate, or the top of a box or bag
  let support = floorY, onDeck = false, under = null;   // `under`: the thing it stands on, which must not shove it sideways
  const deckTop = lift.floorY + lift.deckY + lift.height + 0.07;
  const d = lift.toDeck(m.position);
  const half = HALF[o.type] || { x: 0.3, z: 0.3 };
  if (Math.abs(d.x) < DECK_WIN.x && Math.abs(d.y) < DECK_WIN.z && y0 >= deckTop - 0.05) { support = deckTop; onDeck = true; under = lift; }
  // under a raised deck, or beside it inside the chassis footprint: it lands on the chassis tray
  else if (Math.abs(d.x) < CHASSIS.x && Math.abs(d.y) < CHASSIS.z && y0 >= lift.floorY + CHASSIS.top - 0.05 && m.position.y - rest < deckTop - 0.2) { support = lift.floorY + CHASSIS.top; under = lift; }
  for (const b of others) {
    if (b === o || !TOPS[b.type]) continue;
    const top = b.mesh.position.y - restOf(b) + TOPS[b.type];
    if (top <= support) continue;
    if (Math.hypot(b.mesh.position.x - m.position.x, b.mesh.position.z - m.position.z) < 0.42 && y0 >= top - 0.05) { support = top; onDeck = false; under = b; }
  }
  if (m.position.y - rest <= support) {
    m.position.y = support + rest;
    if (v.y < 0) { v.y = Math.abs(v.y) > 1.2 ? -v.y * 0.18 : 0; }
    // friction on whatever it landed on
    const k = Math.exp(-6 * dt); v.x *= k; v.z *= k;
    if (v.lengthSq() < 0.0004) {
      v.set(0, 0, 0);
      if (onDeck) {
        // captured on the deck: a bar turns to lie along the chassis (it is longer than the deck
        // is wide) and everything is kept inside the rail line by its own half-extents
        const bar = o.type === 'light' || o.type === 'wrapped';
        o.deckYaw = bar ? 0 : m.rotation.y - lift.yaw;
        o.deck = new THREE.Vector2(THREE.MathUtils.clamp(d.x, -DECK_WIN.x + half.x, DECK_WIN.x - half.x), THREE.MathUtils.clamp(d.y, -DECK_WIN.z + half.z, DECK_WIN.z - half.z));
        if (lift.box === o) { o.deck.x = THREE.MathUtils.clamp(o.deck.x, -1.0, 0.5); }
      }
    }
  } else { const k = Math.exp(-0.3 * dt); v.x *= k; v.z *= k; }
  // on the deck and still sliding: the rails hold it in; a bar that hits a rail turns to lie along it
  if (onDeck) {
    const q = lift.toDeck(m.position);
    const cx = THREE.MathUtils.clamp(q.x, -DECK_WIN.x + Math.min(half.x, 0.3), DECK_WIN.x - Math.min(half.x, 0.3));
    const cz = THREE.MathUtils.clamp(q.y, -DECK_WIN.z + Math.min(half.z, 0.3), DECK_WIN.z - Math.min(half.z, 0.3));
    if (cx !== q.x || cz !== q.y) { const w = lift.deckPoint(cx, cz); m.position.x = w.x; m.position.z = w.z; v.x *= 0.3; v.z *= 0.3; }
  }
  // walls, columns and the other things on the floor stop it sliding through them, in the air as
  // well as on the ground (a light dropped beside the lift used to fall through the chassis)
  // (2026-09-05) the lift's own plan circles used to push a box straight off its deck: whatever
  // the body stands on is left out of the push
  const airborne = m.position.y - rest > support + 0.01;
  if (v.x !== 0 || v.z !== 0 || airborne) {
    const ig = [o]; if (under) ig.push(under);
    // a body above the deck line is over the machine, not in it: the lift's plan circles only
    // apply below the deck (and never to what stands on it)
    if (!under && m.position.y - rest >= deckTop - 0.05) ig.push(lift);
    collideWorldRef(m.position, RADIUS[o.type] ?? 0.3, items.world, ig);
    // the loose things on the floor keep out of each other on the plan: bars, wraps and bags as
    // much as boxes. What it stands on, and what stands on it, is left alone
    for (const b of others) {
      if (b === o || b === under || (b.deck && !onDeck)) continue;
      if (Math.abs((b.mesh.position.y - restOf(b)) - (m.position.y - rest)) > 0.25) continue;
      const rr = (RADIUS[o.type] ?? 0.3) * 0.6 + (RADIUS[b.type] ?? 0.3) * 0.6;
      const dx = m.position.x - b.mesh.position.x, dz = m.position.z - b.mesh.position.z;
      const len = Math.hypot(dx, dz);
      if (len > 0.001 && len < rr) { const k = (rr - len) / len; m.position.x += dx * k * 0.5; m.position.z += dz * k * 0.5; }
    }
  }
}
let collideWorldRef = null;   // set by createItems: world.js's collider, so this module does not import it twice
export function setCollider(fn) { collideWorldRef = fn; }

// let go of something: a small toss from the hands, out and a little up, with the walk's speed
function toss(o, player, dist = 0.9, items = null) {
  const m = o.mesh;
  const fwd = new THREE.Vector3(0, 0, -1).applyAxisAngle(new THREE.Vector3(0, 1, 0), player.yaw);
  m.position.copy(player.camera.position).addScaledVector(fwd, dist); m.position.y -= 0.45;
  m.rotation.set(0, player.yaw, 0);
  o.vel = fwd.multiplyScalar(1.4); o.vel.y = 0.6;
  o.deck = null; o.onDeck = null;
  // (Lloyd, 2026-09-06: nothing clips when dropped on the scissor lift) let go on the deck and it
  // goes down on the deck: the rails are there, so the throw is a short drop onto the plate,
  // inside the rail line, never a lob over the side
  const L = items && items.lift;
  if (L && L.aboard) {
    const half = HALF[o.type] || { x: 0.3, z: 0.3 };
    const d = L.toDeck(m.position);
    const w = L.deckPoint(THREE.MathUtils.clamp(d.x, -DECK_WIN.x + half.x, DECK_WIN.x - half.x), THREE.MathUtils.clamp(d.y, -DECK_WIN.z + half.z, DECK_WIN.z - half.z));
    m.position.set(w.x, L.floorY + L.deckY + L.height + 0.07 + restOf(o) + 0.25, w.z);
    if (o.type === 'light' || o.type === 'wrapped') m.rotation.y = L.yaw;   // a bar lies along the chassis
    o.vel.set(0, 0, 0);
  }
}

function carry(player, item) {
  item.deck = null; item.vel = null;
  if (item.mesh) {
    item.mesh.removeFromParent();
    player.camera.add(item.mesh);
    item.mesh.position.set(0.34, -0.42, -0.9);
    item.mesh.rotation.set(0.06, -0.18, 0);
    item.mesh.visible = true;
  }
  item.carried = true;
  player.stow(item);
}

// two rows of six, N along the near wall and S along the far one, 2.3 m apart, labels to the aisle
function palletHome(i, world) { const row = i < 6 ? 0 : 1; return hallToWorld(51.6 + (i % 6) * 2.3, row ? 10.5 : 4.5, world.floorY); }

// the plan's obstacles for collideWorld, rebuilt every frame from what stands on the floor
export function refreshObstacles(items, lifts) {
  const O = items.world.obstacles; O.length = 0;
  items.lifts = lifts;   // every machine on the floor this frame: the sheet rules ask who is standing where
  for (const p of items.pallets) { if (isCarriedPallet(p, items)) continue; O.push({ x: p.mesh.position.x, z: p.mesh.position.z, r: 0.95, ref: p }); }
  // a stack of ply is 2.4 x 1.2: two circles trace it, where one of 1.3 would close the lane the
  // machines drive down the corridor to the doors
  for (const s of items.stacks) {
    if (isCarriedPallet(s, items)) continue;
    const ax = new THREE.Vector3(0.62, 0, 0).applyQuaternion(s.mesh.quaternion);
    O.push({ x: s.mesh.position.x + ax.x, z: s.mesh.position.z + ax.z, r: 0.72, ref: s },
           { x: s.mesh.position.x - ax.x, z: s.mesh.position.z - ax.z, r: 0.72, ref: s });
  }
  for (const b of items.boxes) { if (b.carried || b.onLift || b.disposed || b.deck) continue; O.push({ x: b.mesh.position.x, z: b.mesh.position.z, r: 0.4, ref: b }); }
  for (const b of items.bags) { if (b.carried || b.disposed || b.deck) continue; O.push({ x: b.mesh.position.x, z: b.mesh.position.z, r: 0.45, ref: b }); }
  for (const L of lifts) { const ax = new THREE.Vector3(0.75, 0, 0).applyAxisAngle(new THREE.Vector3(0, 1, 0), L.yaw); O.push({ x: L.pos.x + ax.x, z: L.pos.z + ax.z, r: 0.85, ref: L }, { x: L.pos.x - ax.x, z: L.pos.z - ax.z, r: 0.85, ref: L }); }
  O.push({ x: items.world.skip.x, z: items.world.skip.z, r: 1.9, ref: 'skip' });
}
function isCarriedPallet(p, items) { if (items.jack.carrying === p) return true; for (const j of items.jacks || []) if (j.carrying === p) return true; return false; }

// the sheet's own rotation: the hall's square, turned a right angle when the 2.4 m side runs
// across the room instead of along it
function sheetQuat(along) {
  const q = hallQuat();
  if (along !== 'u') q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.PI / 2));
  return q;
}

// where the sheet in your hands would go: the reticle ray dropped onto the floor, snapped to the
// grid, with the reason it cannot go there. Run every frame while a sheet is held, so the ghost
// and the prompt always agree
function sheetAim(player, items, hit) {
  const world = items.world, p = player.camera.position;
  const fwd = player.camera.getWorldDirection(new THREE.Vector3());
  if (fwd.y > -0.02) return null;                                   // looking level or up: no floor in front
  const t = (world.floorY - p.y) / fwd.y;
  if (!(t > 0) || t > 40) return null;
  const at = p.clone().addScaledVector(fwd, t);
  // pointing at a THING, not the floor: only a laid sheet is looked through (you lay next to one)
  if (hit && hit.kind !== 'sheet' && hit.dist < t - 0.05) return null;
  if (Math.hypot(at.x - player.pos.x, at.z - player.pos.z) > SHEET_REACH) return { far: true };
  const h = worldToHall(at);
  if (h.u >= HALL.doorU - 0.02) return { concrete: true };
  const spot = snapSheet(h.u, h.d, items.sheetAlong);
  spot.why = sheetSpotWhy(world, spot.u, spot.d, spot.along);
  spot.ok = !spot.why;
  return spot;
}

// the ghost follows the aim every frame a sheet is held, and is hidden the rest of the time
function updateGhost(player, items, spot) {
  const g = items.ghost;
  if (!g) return;
  const held = player.carry && player.carry.type === 'sheet';
  if (!held || !spot || !spot.along) { g.visible = false; items.ghostSpot = null; return; }
  items.ghostSpot = spot;
  g.visible = true;
  g.quaternion.copy(sheetQuat(spot.along));
  g.position.copy(hallToWorld(spot.u, spot.d, items.world.floorY + 0.012));
  g.material.color.setHex(spot.ok ? 0x35d06a : 0xd94a3a);
}

// is a machine standing on this sheet? Then it does not come up
function liftOnSheet(items, rec) {
  const W = items.world;
  const hu = (rec.along === 'u' ? SHEET.long : SHEET.short) * 0.5 + 0.05;
  const hd = (rec.along === 'u' ? SHEET.short : SHEET.long) * 0.5 + 0.05;
  for (const L of (items.lifts && items.lifts.length ? items.lifts : [items.lift]).filter(Boolean)) {
    for (const w of W.liftWheels(L)) if (Math.abs(w.u - rec.u) <= hu && Math.abs(w.d - rec.d) <= hd) return true;
  }
  return false;
}

export function createItems(scene, world, camera, collide) {
  const items = { pallets: [], boxes: [], wraps: [], bags: [], lights: [], stacks: [], jack: null, scene, world, camera,
    // which way the next sheet lies. The default is 'd' (the 2.4 m side ACROSS the hall) so a
    // spine laid from the doors up the hall goes down crosswise, like a plank road
    sheetAlong: 'd', ghost: null, ghostSpot: null, lifts: [] };
  if (collide) collideWorldRef = collide;
  for (const [i, column] of COLUMNS.entries()) {
    const home = palletHome(i, world);
    const made = makePallet(column);
    made.group.position.copy(home);
    made.group.rotation.y = 0;
    scene.add(made.group);
    items.pallets.push({ type: 'pallet', column, boxes: 8, held: false, mesh: made.group, boxMeshes: made.boxes, home });
  }
  for (let i = 0; i < 4; i++) {
    const mesh = makeBag();
    // (2026-09-06) by the END wall, which moved east with the back bay. Four bags in a line make
    // a wall of their own on the plan, so they stand in the corner where nothing has to walk past
    mesh.position.copy(hallToWorld(70.0, 9.6 + i * 0.7, world.floorY + 0.41));
    scene.add(mesh);
    items.bags.push({ type: 'bag', wraps: 0, full: false, mesh });
  }
  // five pallets of floor protection in the back bay, past the two pallet rows: three on the
  // north side, two on the south, their long side ACROSS the corridor so the lane to the skip
  // (d 6 to 9) stays open. NOT in the aisle -- a stack there stands exactly where a person has
  // to stand to reach a light pallet, and on top of the crew's jacks (Claude, 2026-09-06, after
  // the inventory proof caught it) -- and not behind a pallet row, which is a wall to a walker
  for (const [u, d] of [[66.6, 4.6], [68.2, 4.6], [69.8, 4.6], [66.6, 10.4], [68.2, 10.4]]) {
    const home = hallToWorld(u, d, world.floorY);
    const made = makeStack('d');
    made.group.position.copy(home);
    scene.add(made.group);
    const stack = { type: 'stack', sheets: STACK_FULL, boxes: 0, mesh: made.group, pile: made.pile, home, quat: made.quat };
    updateStackPile(stack);
    items.stacks.push(stack);
  }
  items.updateStackPile = updateStackPile;
  // the crew put a board back the same way the player does: nearest stack that is not full
  items.returnSheet = (near) => returnSheet(items, null, near);
  // the ghost: where the sheet in your hands would land, green when it may, red when it may not
  const ghost = new THREE.Mesh(new THREE.BoxGeometry(SHEET.long, SHEET.thick, SHEET.short),
    new THREE.MeshBasicMaterial({ color: 0x35d06a, transparent: true, opacity: 0.45, depthWrite: false, toneMapped: false }));
  ghost.visible = false;
  ghost.renderOrder = 4;
  scene.add(ghost);
  items.ghost = ghost;
  const jackMesh = makeJack();
  jackMesh.position.copy(hallToWorld(65.0, 4.4, world.floorY));
  scene.add(jackMesh);
  items.jack = { type: 'jack', carrying: null, held: false, mesh: jackMesh };
  // for the crew (crew.js): their own jacks, boxes off a pallet without a carrier, loose wrap
  items.jacks = [];
  items.spawnJack = (pos) => { const m = makeJack(); m.position.copy(pos); scene.add(m); const j = { type: 'jack', carrying: null, held: false, mesh: m }; items.jacks.push(j); return j; };
  items.spawnBoxFor = (pallet) => { pallet.boxes--; updatePalletStack(pallet); const box = makeBoxObject(8); items.boxes.push(box); scene.add(box.mesh); return box; };
  items.updatePalletStack = updatePalletStack;
  items.makeWrap = () => meshBox(0xf4f4ee, 0.42, 0.08, 0.34, { transparent: true, opacity: 0.42 });
  items.makeSheetMesh = () => meshBox(0xc9a76a, SHEET.long, SHEET.thick, SHEET.short);   // the crew's carried board (crew.js settle)
  return items;
}

// what is left on each pallet of ply, from the save file (the laid sheets are world.js's job)
export function restoreStacks(items, saved) {
  const arr = saved && saved.stackSheets;
  if (!Array.isArray(arr)) return 0;
  for (const [i, s] of items.stacks.entries()) if (Number.isFinite(arr[i])) { s.sheets = Math.max(0, Math.min(STACK_FULL, arr[i])); updateStackPile(s); }
  return items.stacks.length;
}

export function nearestAction(player, lift, install, items) {
  // (2026-09-04) mid-climb nothing is on offer: the prompt says what is happening and a tap does nothing
  if (lift.anim) { if (items.ghost) items.ghost.visible = false; return { label: lift.anim.dir > 0 ? 'Climbing aboard' : 'Climbing down', run: null }; }
  const p = player.camera.position;
  // reach is measured on the floor plan: the eye is 1.7 m up, so a straight distance to a bag on
  // the floor was never inside 1.4 m (2026-09-04: nothing at a pallet was reachable)
  const near = (obj, r) => !obj.disposed && Math.hypot(obj.mesh.position.x - p.x, obj.mesh.position.z - p.z) < r && Math.abs(obj.mesh.position.y - p.y) < 3;
  const skipNear = Math.hypot(items.world.skip.x - p.x, items.world.skip.z - p.z) < 2.9;   // the skip's collision circle is 1.9: reach past it
  // the lift on the floor plan: the deck is a metre up, so a straight distance to it kept "Get on"
  // from showing until you stood inside the machine (2026-09-04)
  const liftNear = (r) => Math.hypot(lift.pos.x - p.x, lift.pos.z - p.z) < r;
  // (Lloyd, 2026-09-06: "the reticle should determine what option we are given. What the reticle
  // is looking at") a ray from the centre of the view finds the thing you are pointing at; that
  // thing and what is in your hands decide the prompt. Place-based prompts (the lift's controls
  // and door, letting go of a pallet) do not need a target
  const fwd = player.camera.getWorldDirection(new THREE.Vector3());
  const ray = new THREE.Raycaster(p.clone(), fwd, 0, 3.4);
  // (Claude, 2026-09-07) the crew are raycast targets now and every one wears a name tag, which is
  // a Sprite: three's Sprite.raycast reads raycaster.camera and throws on null without it
  ray.camera = player.camera;
  const targets = [], owner = new Map();
  const add = (mesh, kind, ref) => { if (mesh) { targets.push(mesh); owner.set(mesh, { kind, ref }); } };
  for (const l of items.lights) if (!l.carried) add(l.mesh, 'light', l);
  for (const b of items.boxes) if (!b.carried && !b.disposed) add(b.mesh, 'box', b);
  for (const b of items.bags) if (!b.carried && !b.disposed) add(b.mesh, 'bag', b);
  for (const w of items.wraps) if (!w.carried && !w.bagged) add(w.mesh, 'wrap', w);
  for (const pl of items.pallets) add(pl.mesh, 'pallet', pl);
  for (const st of items.stacks || []) add(st.mesh, 'stack', st);
  for (const sh of items.world.sheets || []) add(sh.mesh, 'sheet', sh);
  if (!items.jack.held) add(items.jack.mesh, 'jack', items.jack);
  // (Lloyd, 2026-09-06: "The player should be able to allocate tasks to the crew members") the
  // crew are things you can point at: look at one and ACTION opens its task sheet
  if (items.crew) for (const m of items.crew.members || []) add(m.mesh, 'crew', m);
  add(lift.group, 'lift', lift);
  add(items.world.skipMesh, 'skip', null);
  for (const c of items.world.columns) add(c.mesh, 'column', c);
  let hit = null;
  for (const h of ray.intersectObjects(targets, true)) { let o = h.object; while (o && !owner.has(o)) o = o.parent; if (o) { hit = Object.assign({ dist: h.distance, point: h.point }, owner.get(o)); break; } }
  // a thin thing (a bar is 45 mm wide) is hard to put a + on exactly, above all with a thumb: when
  // the ray misses everything, the nearest small item within about 8 degrees of it is the target
  if (!hit) {
    let best = null, ba = 0.14;
    const angleTo = (q) => { const v = q.clone().sub(p); const d = v.length(); return d > 0.05 ? Math.acos(THREE.MathUtils.clamp(v.dot(fwd) / d, -1, 1)) : Math.PI; };
    const consider = (mesh, kind, ref, pts) => { for (const q of pts) { const a = angleTo(q); const d = q.distanceTo(p); if (a < ba && d < 2.7) { ba = a; best = { kind, ref, dist: d, point: q }; } } };
    const barPts = (m) => { const ax = new THREE.Vector3(Math.sin(m.rotation.y), 0, Math.cos(m.rotation.y)); const out = []; for (let t = -0.7; t <= 0.7; t += 0.2) out.push(m.position.clone().addScaledVector(ax, t)); return out; };
    for (const l of items.lights) if (!l.carried) consider(l.mesh, 'light', l, barPts(l.mesh));
    for (const b of items.boxes) if (!b.carried && !b.disposed) consider(b.mesh, 'box', b, [b.mesh.position.clone().setY(b.mesh.position.y + 0.1)]);
    for (const b of items.bags) if (!b.carried && !b.disposed) consider(b.mesh, 'bag', b, [b.mesh.position.clone().setY(b.mesh.position.y + 0.3)]);
    for (const w of items.wraps) if (!w.carried && !w.bagged) consider(w.mesh, 'wrap', w, [w.mesh.position.clone()]);
    hit = best;
  }
  player.aim = hit;   // the HUD may want to name it
  const k = hit ? hit.kind : null, ref = hit ? hit.ref : null;
  const inReach = hit && hit.dist < 2.7;
  const stepsNear = (() => { const o = lift.offboardWorld(); return Math.hypot(o.x - p.x, o.z - p.z) < 1.7; })();
  const held = player.carry;
  const room = (type) => player.canTake(type);
  // the floor protection in your hands: where it would land, shown as a ghost every frame
  const spot = held && held.type === 'sheet' ? sheetAim(player, items, hit) : null;
  updateGhost(player, items, spot);

  // holding the controls: nothing else until you let go
  if (lift.aboard && lift.driving) return { label: 'Let go of the controls', run: () => lift.letGo() };

  // (Lloyd, 2026-09-06) TALKING TO THE CREW comes before everything the hands could be doing: you
  // can give a job to whoever you are looking at with a board or a box in your arms. The host hangs
  // the task sheet off items.talkTo; a host without one (main.js, the old standalone entry) offers
  // nothing rather than a prompt that does nothing when you press it (Claude, 2026-09-07)
  if (k === 'crew' && hit.dist < 3.5 && items.talkTo) return { label: `Talk to ${ref.name}<small>${ref.status || 'standing by'}</small>`, run: () => items.talkTo(ref) };

  // what is in your hands, against the thing in view
  if (held) {
    // a sheet takes both hands: it goes down on the floor, or back on a stack, and nothing else
    if (held.type === 'sheet') {
      if (k === 'stack' && inReach) return ref.sheets >= STACK_FULL ? { label: 'That stack is full', run: null, hint: true }
                                                                    : { label: 'Put the sheet back', run: () => putSheetBack(player, ref, items) };
      if (!spot) return { label: 'Point at the floor to lay the sheet', run: null, hint: true };
      if (spot.concrete) return { label: 'No boards needed: that floor is concrete', run: null, hint: true };
      if (spot.far) return { label: 'Too far: stand closer to lay the sheet', run: null, hint: true };
      return spot.ok ? { label: 'Lay the sheet here', run: () => layHeldSheet(player, items) }
                     : { label: 'No room for a sheet there', run: null, hint: true };
    }
    // (Claude, 2026-09-07) pointing at the ply with something else in the hands: the prompt answers
    // what the reticle is on, so it says why a sheet is not on offer instead of "Set down box"
    if (k === 'stack' && inReach && !items.jack.held) return { label: 'Hands full: a sheet takes both hands', run: null, hint: true };
    if (held.type === 'box' && k === 'lift' && !lift.aboard) return lift.height >= 0.3 ? { label: 'Lower the lift to load it', run: null } : lift.box ? { label: 'The deck already has a box', run: null } : { label: 'Put box on lift deck', run: () => putBoxOnLift(player, lift, items) };
    if ((held.type === 'box' || held.type === 'emptyBox' || (held.type === 'bag' && held.full)) && k === 'skip') return { label: `Dispose ${held.type === 'emptyBox' ? 'empty box' : held.type}`, run: () => disposeCarry(player, items) };
    if (held.type === 'wrap' && k === 'bag' && inReach) return ref.full ? { label: 'That bag is full', run: null } : { label: 'Bag the wrap', run: () => bagWrap(player, ref, items) };
    if (held.type === 'light' && k === 'column') {
      const slot = install.findFitSlot(player.pos, ref.label);
      if (slot) return { label: `Fit light ${slot.column} gap ${slot.gap}`, run: () => fitLight(slot, player, install, items) };
      const nx = install.nextSlotNear(player.pos, ref.label);
      if (nx && Math.abs(nx.dy) >= 1.1) { const up = nx.dy > 0; const m = Math.abs(nx.dy).toFixed(1);
        const advice = !lift.aboard ? (up ? 'Take the lift up to it' : 'Crouch to it') : up ? 'Raise the deck' : lift.height > 0.05 ? 'Lower the deck' : 'Get off: that one goes in from the floor';
        return { label: `Next light ${nx.slot.column} gap ${nx.slot.gap} is ${m} m ${up ? 'above' : 'below'} your hands<br>${advice}`, run: () => dropCarry(player, items), hint: true }; }
      if (nx) return { label: `Get closer to ${nx.slot.column} gap ${nx.slot.gap}`, run: null, hint: true };
      return { label: `Column ${ref.label} is done`, run: null, hint: true };
    }
  }

  // the thing in view, when there is room for it in the inventory
  {
    if (k === 'light' && inReach) return room(ref.type) ? { label: ref.type === 'wrapped' ? 'Pick up wrapped light' : 'Pick up light', run: () => pickUpLight(player, ref, items) } : { label: 'Hands full', run: null };
    if (k === 'box' && inReach && !room(ref.lights > 0 ? 'wrapped' : 'emptyBox')) return { label: 'Hands full', run: null };
    if (k === 'box' && inReach) {
      if (ref === lift.box && !lift.aboard) return lift.height < 0.3 ? { label: ref.lights > 0 ? 'Take box off the lift' : 'Take empty box off the lift', run: () => ref.lights > 0 ? takeBoxOffLift(player, lift, items) : takeEmptyLiftBox(player, lift, items) } : { label: 'Lower the lift to reach the box', run: null };
      if (ref === lift.box) return ref.lights > 0 ? { label: 'Take wrapped light from deck box', run: () => takeLightFromBox(player, ref, items) } : { label: 'Take empty box from lift', run: () => takeEmptyLiftBox(player, lift, items) };
      return ref.lights > 0 ? { label: 'Take wrapped light from box', run: () => takeLightFromBox(player, ref, items) } : { label: 'Take empty box', run: () => carryEmptyBox(player, ref, items) };
    }
    // (Lloyd, 2026-09-06: "be able to move the rubbish containers that we put the wrap in") any
    // bag, empty, part full or full, can be carried
    if (k === 'bag' && inReach) return !room('bag') ? { label: 'Hands full', run: null } : { label: ref.full ? 'Take rubbish bag (full)' : ref.wraps > 0 ? `Take rubbish bag (${ref.wraps}/8)` : 'Take empty bag', run: () => carry(player, ref) };
    if (k === 'wrap' && inReach) return room('wrap') ? { label: 'Pick up wrap', run: () => carry(player, ref) } : { label: 'Hands full', run: null };
    if (k === 'pallet' && hit.dist < 3.0 && !held) {
      if (items.jack.held && !items.jack.carrying) return ref.mesh.position.distanceTo(items.jack.mesh.position) < 1.25 ? (player.body && !player.body.canLift(15) ? { label: 'Too puffed to jack a pallet: rest a moment', run: null } : { label: `Lift ${ref.column} pallet`, run: () => items.jack.carrying = ref }) : { label: `Walk the jack under the ${ref.column} pallet`, run: null };
      if (ref.boxes <= 0) return { label: `${ref.column} pallet is empty`, run: null };
      return player.body && !player.body.canLift(10) ? { label: 'Too puffed to lift a box: rest a moment', run: null } : { label: `Take box from ${ref.column} pallet`, run: () => spawnBox(player, items, ref) };
    }
    // (Lloyd, 2026-09-06) the board stacks: a sheet off the top, or the whole pallet on the jack
    if (k === 'stack' && hit.dist < 3.0 && !held) {
      if (items.jack.held && !items.jack.carrying) return ref.mesh.position.distanceTo(items.jack.mesh.position) < 1.25 ? (player.body && !player.body.canLift(15) ? { label: 'Too puffed to jack a pallet: rest a moment', run: null } : { label: 'Lift the board stack', run: () => items.jack.carrying = ref }) : { label: 'Walk the jack under the board stack', run: null };
      if (ref.sheets <= 0) return { label: 'That board stack is empty', run: null, hint: true };
      if (!inReach) return { label: `Step up to the board stack (${ref.sheets} left)`, run: null, hint: true };
      if (!room('sheet')) return { label: 'Hands full: a sheet takes both hands', run: null, hint: true };
      return player.body && !player.body.canLift(10) ? { label: 'Too puffed to lift a sheet: rest a moment', run: null } : { label: `Take a sheet (${ref.sheets} left)`, run: () => takeSheet(player, ref, items) };
    }
    // a sheet already on the floor: it comes up again, unless a machine is parked on it
    if (k === 'sheet' && hit.dist < SHEET_TAKE && !held) {
      if (liftOnSheet(items, ref)) return { label: 'A lift is standing on it', run: null, hint: true };
      if (!room('sheet')) return { label: 'Hands full', run: null };
      return { label: 'Pick up the sheet', run: () => pickUpSheet(player, ref, items) };
    }
    if (k === 'sheet' && hit.dist < SHEET_TAKE && held && held.type !== 'sheet') return { label: 'Hands full', run: null };
    if (k === 'jack' && inReach && !items.jack.by && !held) return { label: 'Take pallet jack', run: () => items.jack.held = true };
    if (k === 'column' && !held) return { label: `Column ${ref.label}`, run: null, hint: true };
  }
  // the hands alone
  if (held) {
    if (held.type === 'wrapped') return { label: 'Unwrap light', run: () => unwrapLight(player, items) };
    if (held.type === 'light') return { label: lift.aboard ? 'Put light down on the deck' : 'Put light down', run: () => dropCarry(player, items) };
    if (held.type === 'box') return { label: lift.aboard ? 'Put box down on the deck' : 'Set down box', run: () => dropCarry(player, items) };
    if (held.type === 'emptyBox') return { label: 'Put empty box down', run: () => dropCarry(player, items) };
    if (held.type === 'bag') return { label: held.full ? 'Put rubbish bag down' : 'Put empty bag down', run: () => dropCarry(player, items) };
    if (held.type === 'wrap') return { label: 'Put wrap down', run: () => dropCarry(player, items) };
  }

  // the pallet jack in hand
  if (items.jack.held) { if (items.jack.carrying) return { label: 'Set pallet down', run: () => items.jack.carrying = null }; if (k !== 'pallet') return { label: 'Release pallet jack', run: () => items.jack.held = false }; }
  // the lift is a place: its controls and its door work from where you stand
  if (k === 'lift' && !lift.aboard) return lift.height >= 0.3 ? { label: 'Lift is up', run: null } : stepsNear ? { label: 'Get on lift', run: () => lift.board(player) } : { label: 'Get on from the back of the lift', run: null };
  if (lift.aboard && lift.atPanel()) return { label: 'Take the controls', run: () => lift.takeControls(player) };
  if (lift.aboard) {
    if (lift.height >= 0.3) return { label: 'Lower the lift from the controls to get off', run: null };
    return lift.atDoor() ? { label: 'Get off lift', run: () => lift.leave(player) } : { label: 'Walk to the back to get off, or to the controls to drive', run: null };
  }
  return { label: hit ? 'Nothing to do with that' : 'Point at something', run: null };
}

function updatePalletStack(pallet) {
  pallet.boxMeshes.forEach((m, i) => m.visible = i < pallet.boxes);
}

// ---- floor protection in the hands (Lloyd, 2026-09-06) ----
function takeSheet(player, stack, items) {
  if (stack.sheets <= 0) return;
  stack.sheets--;
  updateStackPile(stack);
  const mesh = makeCarrySheet();
  player.camera.add(mesh);
  player.stow({ type: 'sheet', mesh });
}
// (Claude, 2026-09-07) a sheet goes back on a pallet of ply that HAS ROOM, the given one first and
// otherwise the nearest that is not full. The 150 sheets in the game came off five stacks of 30, so
// somewhere always has room; a full stack used to swallow the board in your hands and the count
// went 150 -> 149. Returns the stack it went on, or null when every one of them is full
export function returnSheet(items, stack, near) {
  if (stack && stack.sheets < STACK_FULL) { stack.sheets++; updateStackPile(stack); return stack; }
  let best = null, bd = Infinity;
  for (const s of items.stacks) {
    if (s.sheets >= STACK_FULL) continue;
    const d = near ? s.mesh.position.distanceTo(near) : 0;
    if (d < bd) { bd = d; best = s; }
  }
  if (best) { best.sheets++; updateStackPile(best); }
  return best;
}
function putSheetBack(player, stack, items) {
  const it = player.carry;
  if (!it || it.type !== 'sheet') return;
  if (stack.sheets >= STACK_FULL) return;         // the prompt says so: a full stack takes nothing
  it.mesh.removeFromParent();
  items.scene.remove(it.mesh);
  returnSheet(items, stack);
  player.carry = null;
}
// F / DROP with a sheet in hand lays it where the ghost is; a 20 kg board is never tossed, so a
// bad spot does nothing and the prompt says why
export function layHeldSheet(player, items) {
  const it = player.carry, spot = items.ghostSpot;
  if (!it || it.type !== 'sheet' || !spot || !spot.ok) return false;
  laySheet(items.world, spot.u, spot.d, spot.along);
  it.mesh.removeFromParent();
  items.scene.remove(it.mesh);
  player.carry = null;
  if (items.ghost) items.ghost.visible = false;
  items.ghostSpot = null;
  return true;
}
function pickUpSheet(player, rec, items) {
  if (!liftSheetUp(items.world, rec)) return;
  const mesh = makeCarrySheet();
  player.camera.add(mesh);
  player.stow({ type: 'sheet', mesh });
}
// R on the desk, TURN on the phone: the same board, laid the other way
export function turnSheet(items) {
  items.sheetAlong = items.sheetAlong === 'u' ? 'd' : 'u';
  return items.sheetAlong;
}

function spawnBox(player, items, pallet) {
  pallet.boxes--;
  updatePalletStack(pallet);
  const box = makeBoxObject(8);
  items.boxes.push(box);
  items.scene.add(box.mesh);
  carry(player, box);
}

function takeLightFromBox(player, box, items) {
  box.lights--;
  if (box.mesh?.material?.color) box.mesh.material.color.setHex(box.lights > 0 ? 0x9a7b55 : 0x6f6250);
  const mesh = makeCarryLight(true);
  player.camera.add(mesh);
  player.stow({ type: 'wrapped', mesh });
  if (box.lights <= 0) box.type = 'emptyBox';
  saveLooseBoxPosition(box, items);
}

function putBoxOnLift(player, lift, items) {
  const box = player.carry;
  box.carried = false; box.onLift = true; box.vel = null;
  box.mesh.removeFromParent(); items.scene.add(box.mesh);
  // (2026-09-05) it goes down where you stand on the deck (or the nearest deck point from the floor), not the deck's centre
  const d = lift.toDeck(player.pos); d.x = THREE.MathUtils.clamp(d.x, -1.0, 0.5); d.y = THREE.MathUtils.clamp(d.y, -0.35, 0.35);
  box.deck = d; box.deckYaw = 0;
  lift.box = box;
  player.carry = null;
  lift.refresh();
}

function unwrapLight(player, items) {
  if (player.carry?.mesh) {
    player.carry.mesh.removeFromParent();
    items.scene.remove(player.carry.mesh);
  }
  const wrapMesh = meshBox(0xf4f4ee, 0.42, 0.08, 0.34, { transparent: true, opacity: 0.42 });
  wrapMesh.position.copy(player.camera.position).y = items.world.floorY + 0.05;
  items.scene.add(wrapMesh);
  items.wraps.push({ type: 'wrap', mesh: wrapMesh, bagged: false });
  const lightMesh = makeCarryLight(false);
  player.camera.add(lightMesh);
  player.carry = { type: 'light', mesh: lightMesh };
}

function fitLight(slot, player, install, items) {
  if (player.carry?.mesh) {
    player.carry.mesh.removeFromParent();
    items.scene.remove(player.carry.mesh);
  }
  install.fit(slot, player);
  player.carry = null;
}

function bagWrap(player, bag, items) {
  if (player.carry.mesh) {
    player.carry.mesh.removeFromParent();
    items.scene.remove(player.carry.mesh);
  }
  bag.wraps++;
  player.carry.bagged = true;
  if (bag.wraps >= 8) {
    bag.full = true;
    bag.type = 'bag';
    bag.mesh.material.color.setHex(0x41523d);
  }
  player.carry = null;
}

function carryEmptyBox(player, box) {
  box.type = 'emptyBox';
  carry(player, box);
}

function takeBoxOffLift(player, lift) {
  const box = lift.box;
  lift.box = null;
  box.onLift = false; box.deck = null;
  carry(player, box);
}

function takeEmptyLiftBox(player, lift) {
  const box = lift.box;
  lift.box = null;
  box.onLift = false; box.deck = null;
  box.type = 'emptyBox';
  carry(player, box);
}

function disposeCarry(player, items) {
  if (player.carry.mesh) {
    player.carry.mesh.removeFromParent();
    items.scene.remove(player.carry.mesh);
  }
  player.carry.disposed = true;
  player.carry = null;
}

function saveLooseBoxPosition(box, items) {
  if (box.lights <= 0 && !box.carried && !box.onLift) box.mesh.material.color.setHex(0x6f6250);
  if (!box.mesh.parent) items.scene.add(box.mesh);
}

// a loose light on the floor (or a deck): a 1.5 m bar lying flat, wrapped or bare
function pickUpLight(player, loose, items) {
  loose.mesh.removeFromParent();
  items.lights.splice(items.lights.indexOf(loose), 1);
  const mesh = makeCarryLight(loose.type === 'wrapped');
  player.camera.add(mesh);
  player.stow({ type: loose.type, mesh });
}

// true when something actually left the hands, so the caller only makes a noise when it did
export function dropCarry(player, items) {
  if (!player.carry) return false;
  const item = player.carry;
  // (Lloyd, 2026-09-06) a sheet is laid, never dropped: DROP puts it on the ghost's spot when the
  // spot is good and does nothing at all when it is not
  if (item.type === 'sheet') return layHeldSheet(player, items);
  if (item.type === 'light' || item.type === 'wrapped') {
    item.mesh.removeFromParent();
    const bar = makeBarMesh(item.type === 'wrapped');
    items.scene.add(bar);
    const light = { type: item.type, mesh: bar, carried: false };
    toss(light, player, 0.8, items); if (!(items.lift && items.lift.aboard)) bar.rotation.y += Math.PI / 2;   // the bar lies across the way you face
    items.lights.push(light);
    player.carry = null;
    return true;
  }
  if (item.mesh) {
    item.mesh.removeFromParent();
    items.scene.add(item.mesh);
    item.carried = false;
    toss(item, player, 0.9, items);
  }
  player.carry = null;
  return true;
}

export function updateItems(player, lift, items, dt = 0) {
  // (2026-09-05) every loose thing has its own physics: gravity, a landing, a slide to rest, and
  // the deck under it when it is over the deck
  if (dt > 0) { const bodies = bodiesOf(items); for (const o of bodies) stepBody(o, dt, items, lift, bodies); }
  if (items.jack.held && !items.jack.by) {
    items.jack.mesh.position.copy(player.camera.position).add(new THREE.Vector3(0, -1.35, -1.05).applyAxisAngle(new THREE.Vector3(0, 1, 0), player.yaw));
    items.jack.mesh.position.y = items.world.floorY;
    items.jack.mesh.rotation.y = player.yaw;
    if (items.jack.carrying) {
      // a board stack is twice a pallet's length: it rides ALONG the tines, further out, so it
      // does not sit in the player's shins (Lloyd, 2026-09-06)
      const stack = items.jack.carrying.type === 'stack';
      const off = new THREE.Vector3(0, 0.2, stack ? -0.95 : -0.55).applyAxisAngle(new THREE.Vector3(0, 1, 0), player.yaw);
      items.jack.carrying.mesh.position.copy(items.jack.mesh.position).add(off);
      items.jack.carrying.mesh.rotation.set(0, player.yaw + (stack ? Math.PI / 2 : 0), 0);
    }
  }
  if (lift.box) lift.refresh();
}

export function resetForNight(player, lift, items) {
  for (const pallet of items.pallets) { pallet.mesh.position.copy(pallet.home); pallet.mesh.rotation.y = 0; }
  // (Lloyd, 2026-09-06) the stacks go back to storage with the pallets; the LAID sheets stay
  // exactly where they are, because the protection is down for the whole job
  for (const stack of items.stacks) { stack.mesh.position.copy(stack.home); stack.mesh.quaternion.copy(stack.quat); }
  for (const [i, box] of items.boxes.entries()) {
    if (box.disposed) continue;
    box.carried = false;
    box.onLift = false; box.deck = null; box.vel = null;
    box.mesh.removeFromParent();
    items.scene.add(box.mesh);
    box.mesh.position.copy(hallToWorld(50.2 + (i % 6) * 0.62, 11.5 - Math.floor(i / 6) * 0.5, items.world.floorY + 0.2));
  }
  for (const [i, wrap] of items.wraps.entries()) {
    if (wrap.bagged) continue;
    wrap.mesh.position.copy(hallToWorld(64.6, 9.3 + (i % 8) * 0.12, items.world.floorY + 0.05));
  }
  for (const [i, l] of items.lights.entries()) { l.deck = null; l.vel = null; l.mesh.position.copy(hallToWorld(50.0 + (i % 6) * 0.3, 3.5 + Math.floor(i / 6) * 0.25, items.world.floorY + 0.05)); }
  for (const b of items.bags) { b.deck = null; b.vel = null; }
  for (const w of items.wraps) { w.deck = null; w.vel = null; }
  items.jack.deck = null; items.jack.vel = null;
  items.jack.held = false;
  items.jack.carrying = null;
  if (items.ghost) items.ghost.visible = false;
  items.ghostSpot = null;
  items.jack.mesh.position.copy(hallToWorld(65.0, 4.4, items.world.floorY));
  lift.pos.copy(hallToWorld(63.6, 6.6, items.world.floorY)); lift.yaw = 0; lift.aboard = false; lift.driving = false; lift.speed = 0; lift.steer = 0; lift.anim = null; lift.gate.rotation.y = 0; player.onLift = false; player.eye = 1.68;
  lift.height = 0;
  lift.box = null;
  lift.refresh();
  // a sheet still in the hands at 05:00 goes back on the nearest stack WITH ROOM, not into thin air
  for (const it of player.inv) if (it && it.type === 'sheet') returnSheet(items, null, player.pos);
  if (player.carry?.mesh) {
    player.carry.mesh.removeFromParent();
    items.scene.remove(player.carry.mesh);
  }
  player.carry = null;
  player.pos.copy(hallToWorld(52.0, 7.5, items.world.floorY));
}

export function cleanupClear(items, lift) {
  const left = [];
  // (2026-09-06) "out of the hall" is the door line, not a radius round the storage spot: the
  // corridor grew a back bay for the ply and a 12 m ball round the middle of it no longer reaches
  // the end wall, so bags stacked by it counted as left in the hall
  const outside = (m) => worldToHall(m.position).u > HALL.doorU - 0.5;
  if (!items.pallets.every((p) => outside(p.mesh))) left.push('pallets');
  // (Lloyd, 2026-09-06) the STACKS go back to storage like the pallets. The LAID sheets do not
  // count: the floor protection stays down for the whole job, the hall is closed for the works
  if (!items.stacks.every((s) => outside(s.mesh))) left.push('board stacks');
  if (!items.boxes.every((b) => b.disposed || (!b.carried && outside(b.mesh)))) left.push('boxes');
  if (!items.wraps.every((w) => w.bagged || outside(w.mesh))) left.push('wrap');
  if (!items.lights.every((l) => outside(l.mesh))) left.push('loose lights');
  if (lift.box && !outside(lift.box.mesh)) left.push('lift box');
  // (Lloyd) EVERYTHING leaves the hall by 05:00: the machine and the jack as much as the stock
  if (!outside(lift.group)) left.push('the scissor lift');
  if (!outside(items.jack.mesh)) left.push('the pallet jack');
  if (!items.bags.every((b) => b.disposed || outside(b.mesh))) left.push('rubbish bags');
  return { ok: left.length === 0, left };
}
