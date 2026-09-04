import * as THREE from 'three';
import { hallToWorld } from './world.js';

const COLUMNS = ['N1','N2','N3','N4','N5','N6','S1','S2','S3','S4','S5','S6'];
const BOX = { x: 0.5, y: 0.34, z: 0.42 };

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

function makeCarryLight(wrapped) {
  const group = new THREE.Group();
  const bar = new THREE.Mesh(
    new THREE.BoxGeometry(0.08, 0.08, 1.5),
    wrapped
      ? mat(0xf4f4ee, 0.25, { transparent: true, opacity: 0.56 })
      : mat(0xffffff, 0.35, { emissive: 0xe4f5ff, emissiveIntensity: 0.55 })
  );
  group.add(bar);
  // held low and to the right, slanted away, so it does not fill the view (Lloyd's phone shot)
  group.position.set(0.42, -0.62, -1.0);
  group.rotation.set(0.35, -0.55, 0.1);
  return group;
}

function carry(player, item) {
  if (item.mesh) {
    item.mesh.removeFromParent();
    player.camera.add(item.mesh);
    item.mesh.position.set(0.34, -0.42, -0.9);
    item.mesh.rotation.set(0.06, -0.18, 0);
    item.mesh.visible = true;
  }
  item.carried = true;
  player.carry = item;
}

// two rows of six, N along the near wall and S along the far one, 2.3 m apart, labels to the aisle
function palletHome(i, world) { const row = i < 6 ? 0 : 1; return hallToWorld(51.6 + (i % 6) * 2.3, row ? 10.5 : 4.5, world.floorY); }

// the plan's obstacles for collideWorld, rebuilt every frame from what stands on the floor
export function refreshObstacles(items, lifts) {
  const O = items.world.obstacles; O.length = 0;
  for (const p of items.pallets) { if (isCarriedPallet(p, items)) continue; O.push({ x: p.mesh.position.x, z: p.mesh.position.z, r: 0.95, ref: p }); }
  for (const b of items.boxes) { if (b.carried || b.onLift || b.disposed) continue; O.push({ x: b.mesh.position.x, z: b.mesh.position.z, r: 0.4, ref: b }); }
  for (const b of items.bags) { if (b.carried || b.disposed) continue; O.push({ x: b.mesh.position.x, z: b.mesh.position.z, r: 0.45, ref: b }); }
  for (const L of lifts) { const ax = new THREE.Vector3(0.75, 0, 0).applyAxisAngle(new THREE.Vector3(0, 1, 0), L.yaw); O.push({ x: L.pos.x + ax.x, z: L.pos.z + ax.z, r: 0.85, ref: L }, { x: L.pos.x - ax.x, z: L.pos.z - ax.z, r: 0.85, ref: L }); }
  O.push({ x: items.world.skip.x, z: items.world.skip.z, r: 1.9, ref: 'skip' });
}
function isCarriedPallet(p, items) { if (items.jack.carrying === p) return true; for (const j of items.jacks || []) if (j.carrying === p) return true; return false; }

export function createItems(scene, world, camera) {
  const items = { pallets: [], boxes: [], wraps: [], bags: [], lights: [], jack: null, scene, world, camera };
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
    mesh.position.copy(hallToWorld(65.3, 9.5 + i * 0.7, world.floorY + 0.41));
    scene.add(mesh);
    items.bags.push({ type: 'bag', wraps: 0, full: false, mesh });
  }
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
  return items;
}

export function nearestAction(player, lift, install, items) {
  // (2026-09-04) mid-climb nothing is on offer: the prompt says what is happening and a tap does nothing
  if (lift.anim) return { label: lift.anim.dir > 0 ? 'Climbing aboard' : 'Climbing down', run: null };
  const p = player.camera.position;
  // reach is measured on the floor plan: the eye is 1.7 m up, so a straight distance to a bag on
  // the floor was never inside 1.4 m (2026-09-04: nothing at a pallet was reachable)
  const near = (obj, r) => !obj.disposed && Math.hypot(obj.mesh.position.x - p.x, obj.mesh.position.z - p.z) < r && Math.abs(obj.mesh.position.y - p.y) < 3;
  const skipNear = Math.hypot(items.world.skip.x - p.x, items.world.skip.z - p.z) < 2.9;   // the skip's collision circle is 1.9: reach past it
  // the lift on the floor plan: the deck is a metre up, so a straight distance to it kept "Get on"
  // from showing until you stood inside the machine (2026-09-04)
  const liftNear = (r) => Math.hypot(lift.pos.x - p.x, lift.pos.z - p.z) < r;

  if (player.carry?.type === 'box' && liftNear(2.4) && lift.height < 0.3 && !lift.box) return { label: 'Put box on lift deck', run: () => putBoxOnLift(player, lift, items) };
  if ((player.carry?.type === 'box' || player.carry?.type === 'emptyBox' || player.carry?.type === 'bag') && skipNear) return { label: `Dispose ${player.carry.type}`, run: () => disposeCarry(player, items) };
  if (player.carry?.type === 'box') return { label: 'Set down box', run: () => dropCarry(player, items) };
  if (player.carry?.type === 'emptyBox') return { label: 'Carry empty box to skip', run: null };
  if (player.carry?.type === 'wrapped') return { label: 'Unwrap light', run: () => unwrapLight(player, items) };
  if (player.carry?.type === 'light') {
    const slot = install.findFitSlot(lift.deckWorld());
    if (slot && lift.aboard) return { label: `Fit light ${slot.column} gap ${slot.gap}`, run: () => fitLight(slot, player, install, items) };
    // (Lloyd, 2026-09-04) a light in hand with nowhere to fit it goes DOWN on ACTION, here
    return { label: lift.aboard ? 'Put light down on the deck' : 'Put light down', run: () => dropCarry(player, items) };
  }
  if (player.carry?.type === 'wrap') {
    const bag = items.bags.find((b) => near(b, 1.4) && !b.full);
    if (bag) return { label: 'Bag the wrap', run: () => bagWrap(player, bag, items) };
    return { label: 'Find a rubbish bag', run: null };
  }

  // (Lloyd, 2026-09-04) on the deck you WALK: the controls are a place at the +x end you go to,
  // and while you hold them nothing else is offered. Let go and the deck is a floor again
  if (lift.aboard && lift.driving) return { label: 'Let go of the controls', run: () => lift.letGo() };
  if (lift.aboard && lift.box && lift.box.lights > 0 && lift.deckLocal.length() < 1.0) return { label: 'Take wrapped light from deck box', run: () => takeLightFromBox(player, lift.box, items) };
  if (lift.aboard && lift.box && lift.box.lights <= 0 && lift.deckLocal.length() < 1.0) return { label: 'Take empty box from lift', run: () => takeEmptyLiftBox(player, lift, items) };
  // (Lloyd, 2026-09-04) you get on from ONE end, the back, where the steps are
  const stepsNear = (() => { const o = lift.offboardWorld(); return Math.hypot(o.x - p.x, o.z - p.z) < 1.7; })();
  if (stepsNear && !lift.aboard && lift.height < 0.3) return { label: 'Get on lift', run: () => lift.board(player) };
  if (liftNear(2.3) && !lift.aboard && lift.height < 0.3) return { label: 'Get on from the back of the lift', run: null };
  if (lift.aboard && lift.atPanel()) return { label: 'Take the controls', run: () => lift.takeControls(player) };
  // off the lift only from the ground and from the back end, where the steps are: at height
  // the deck is the only floor there is
  if (lift.aboard) {
    if (lift.height >= 0.3) return { label: 'Lower the lift from the controls to get off', run: null };
    return lift.atDoor() ? { label: 'Get off lift', run: () => lift.leave(player) } : { label: 'Walk to the back to get off, or to the controls to drive', run: null };
  }

  // a light you put down comes first: it is the likelier thing to want back than the box beside it
  const loose = items.lights.find((l) => !l.carried && near(l, 1.4));
  if (loose) return { label: loose.type === 'wrapped' ? 'Pick up wrapped light' : 'Pick up light', run: () => pickUpLight(player, loose, items) };
  const box = items.boxes.find((b) => !b.carried && !b.onLift && !b.disposed && near(b, 1.25));
  if (box) return { label: box.lights > 0 ? 'Take wrapped light from box' : 'Take empty box', run: () => box.lights > 0 ? takeLightFromBox(player, box, items) : carryEmptyBox(player, box, items) };
  const wrap = items.wraps.find((w) => !w.carried && !w.bagged && near(w, 1.15));
  if (wrap) return { label: 'Pick up wrap', run: () => carry(player, wrap) };
  const fullBag = items.bags.find((b) => b.full && !b.carried && !b.disposed && near(b, 1.25));
  if (fullBag) return { label: 'Take rubbish bag', run: () => carry(player, fullBag) };

  if (items.jack.held) {
    if (items.jack.carrying) return { label: 'Set pallet down', run: () => items.jack.carrying = null };
    const pal = items.pallets.find((b) => b.boxes > 0 && b.mesh.position.distanceTo(items.jack.mesh.position) < 1.25);
    if (pal) return player.body && !player.body.canLift(15) ? { label: 'Too puffed to jack a pallet: rest a moment', run: null } : { label: `Lift ${pal.column} pallet`, run: () => items.jack.carrying = pal };
  }
  if (near(items.jack, 1.4) && !items.jack.by) return { label: items.jack.held ? 'Release pallet jack' : 'Take pallet jack', run: () => items.jack.held = !items.jack.held };

  const pallet = items.pallets.find((b) => b.boxes > 0 && near(b, 1.55));
  if (pallet) return player.body && !player.body.canLift(10) ? { label: 'Too puffed to lift a box: rest a moment', run: null } : { label: `Take box from ${pallet.column} pallet`, run: () => spawnBox(player, items, pallet) };
  return { label: 'No action nearby', run: null };
}

function updatePalletStack(pallet) {
  pallet.boxMeshes.forEach((m, i) => m.visible = i < pallet.boxes);
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
  player.carry = { type: 'wrapped', mesh };
  if (box.lights <= 0) box.type = 'emptyBox';
  saveLooseBoxPosition(box, items);
}

function putBoxOnLift(player, lift, items) {
  lift.box = player.carry;
  lift.box.carried = false;
  lift.box.onLift = true;
  lift.box.mesh.removeFromParent();
  items.scene.add(lift.box.mesh);
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

function takeEmptyLiftBox(player, lift) {
  const box = lift.box;
  lift.box = null;
  box.onLift = false;
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
  player.carry = { type: loose.type, mesh };
}

export function dropCarry(player, items) {
  if (!player.carry) return;
  const item = player.carry;
  if (item.type === 'light' || item.type === 'wrapped') {
    item.mesh.removeFromParent();
    const bar = makeCarryLight(item.type === 'wrapped').children[0];
    bar.rotation.set(0, 0, 0);
    const ahead = new THREE.Vector3(0, 0, -1.0).applyAxisAngle(new THREE.Vector3(0, 1, 0), player.yaw);
    bar.position.copy(player.pos).add(ahead); bar.position.y = player.pos.y + 0.05;
    bar.rotation.y = player.yaw + Math.PI / 2;
    items.scene.add(bar);
    const light = { type: item.type, mesh: bar, carried: false };
    // (2026-09-04) put down on the deck, it rides the deck: remember where in chassis terms
    if (player.onLift && items.lift) { const d = items.lift.toDeck(bar.position); if (Math.abs(d.x) < 1.3 && Math.abs(d.y) < 0.65) { light.onDeck = d; light.deckYaw = bar.rotation.y - items.lift.yaw; } }
    items.lights.push(light);
    player.carry = null;
    return;
  }
  if (item.mesh) {
    item.mesh.removeFromParent();
    items.scene.add(item.mesh);
    item.mesh.position.copy(player.camera.position).add(new THREE.Vector3(0, -1.0, -0.9).applyAxisAngle(new THREE.Vector3(0, 1, 0), player.yaw));
    item.mesh.position.y = items.world.floorY + (item.type === 'wrap' ? 0.05 : 0.2);
    item.mesh.rotation.set(0, player.yaw, 0);
    item.carried = false;
  }
  player.carry = null;
}

export function updateItems(player, lift, items) {
  if (items.jack.held && !items.jack.by) {
    items.jack.mesh.position.copy(player.camera.position).add(new THREE.Vector3(0, -1.35, -1.05).applyAxisAngle(new THREE.Vector3(0, 1, 0), player.yaw));
    items.jack.mesh.position.y = items.world.floorY;
    items.jack.mesh.rotation.y = player.yaw;
    if (items.jack.carrying) {
      const off = new THREE.Vector3(0, 0.2, -0.55).applyAxisAngle(new THREE.Vector3(0, 1, 0), player.yaw);
      items.jack.carrying.mesh.position.copy(items.jack.mesh.position).add(off);
      items.jack.carrying.mesh.rotation.y = player.yaw;
    }
  }
  if (lift.box) lift.refresh();
  for (const l of items.lights) {
    if (!l.onDeck || l.carried) continue;
    const p = lift.deckPoint(l.onDeck.x, l.onDeck.y); l.mesh.position.set(p.x, lift.floorY + lift.deckY + lift.height + 0.05, p.z); l.mesh.rotation.y = l.deckYaw + lift.yaw;
  }
}

export function resetForNight(player, lift, items) {
  for (const pallet of items.pallets) { pallet.mesh.position.copy(pallet.home); pallet.mesh.rotation.y = 0; }
  for (const [i, box] of items.boxes.entries()) {
    if (box.disposed) continue;
    box.carried = false;
    box.onLift = false;
    box.mesh.removeFromParent();
    items.scene.add(box.mesh);
    box.mesh.position.copy(hallToWorld(50.2 + (i % 6) * 0.62, 11.5 - Math.floor(i / 6) * 0.5, items.world.floorY + 0.2));
  }
  for (const [i, wrap] of items.wraps.entries()) {
    if (wrap.bagged) continue;
    wrap.mesh.position.copy(hallToWorld(64.6, 9.3 + (i % 8) * 0.12, items.world.floorY + 0.05));
  }
  for (const [i, l] of items.lights.entries()) l.mesh.position.copy(hallToWorld(50.0 + (i % 6) * 0.3, 3.5 + Math.floor(i / 6) * 0.25, items.world.floorY + 0.05));
  items.jack.held = false;
  items.jack.carrying = null;
  items.jack.mesh.position.copy(hallToWorld(65.0, 4.4, items.world.floorY));
  lift.pos.copy(hallToWorld(63.6, 6.6, items.world.floorY)); lift.yaw = 0; lift.aboard = false; lift.driving = false; lift.speed = 0; lift.steer = 0; lift.anim = null; lift.gate.rotation.x = 0; player.onLift = false; player.eye = 1.68;
  lift.height = 0;
  lift.box = null;
  lift.refresh();
  if (player.carry?.mesh) {
    player.carry.mesh.removeFromParent();
    items.scene.remove(player.carry.mesh);
  }
  player.carry = null;
  player.pos.copy(hallToWorld(52.0, 7.5, items.world.floorY));
}

export function cleanupClear(items, lift) {
  const left = [];
  const outside = (m) => {
    const dStorage = m.position.distanceTo(items.world.storage);
    const dSkip = m.position.distanceTo(items.world.skip);
    return dStorage < 12 || dSkip < 5;
  };
  if (!items.pallets.every((p) => outside(p.mesh))) left.push('pallets');
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
