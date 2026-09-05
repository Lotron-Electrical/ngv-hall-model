import * as THREE from 'three';
import { hallToWorld, worldToHall, HALL } from './world.js';
import { Lift } from './lift.js';
import { Avatar } from './avatar.js';

// THE CREW (Lloyd, 2026-09-04). Solo on the prototype column. Once a column is done a HELPER
// joins and works your column: jacks its pallet in from the corridor, carries boxes to the
// column foot and onto your lift deck when it is down, bags the wrap and runs full bags to the
// skip. Once a second column is done a TEAM OF TWO joins with their own lift and does whole
// columns on their own the same way you did: pallet in, boxes to the foot, one on the lift
// fitting, one feeding; and every column done after that brings another team (up to three).
// The crew tire with the clock like you do (no stamina, they pace themselves), and at 04:30
// they pack up: lifts, jacks and pallets back through the doors.

const FEET_OUT = 2.0;             // the pallet stands this far off a column, toward the middle
const PACK_UP = 28.5 * 60;        // 04:30 on the night clock (minutes from midnight)


// where a column's pallet stands: off the shaft toward the hall's middle line
function footSpot(col) {
  const hd = worldToHall(col.pos);
  const d = hd.d < 7.5 ? hd.d + FEET_OUT : hd.d - FEET_OUT;
  return hallToWorld(hd.u, d, col.pos.y);
}

// a column with work left: nearest to `from` among those not finished (and not claimed)
function pickColumn(install, world, from, claimed) {
  let best = null, bd = Infinity;
  for (const col of world.columns) {
    if (claimed.has(col.label)) continue;
    const left = install.slots.some((s) => s.column === col.label && !install.fitted.has(s.id));
    if (!left) continue;
    const d = col.pos.distanceTo(from);
    if (d < bd) { bd = d; best = col; }
  }
  return best;
}

class Worker {
  constructor(scene, world, color, name) {
    this.scene = scene; this.world = world; this.name = name;
    // (2026-09-05) the crew wear the articulated character model (avatar.js), name tag and all
    this.av = new Avatar(color, name); this.mesh = this.av.group; scene.add(this.mesh);
    this.pos = this.mesh.position; this.yaw = 0;
    this.carry = null;             // a box object, a bag, or a pallet (via the jack)
    this.jack = null;              // the jack group when this worker has it
    this.speed = 2.1;
  }
  place(p) { this.pos.copy(p); this.pos.y = this.world.floorY; }
  ignore() { const out = []; if (this.carry) out.push(this.carry); if (this.jack && this.jack.carrying) out.push(this.jack.carrying); if (this.lift) out.push(this.lift); return out; }
  // walk toward a point on the floor; true once within `reach`
  walkTo(target, dt, collide, scale, reach = 0.9) {
    const dx = target.x - this.pos.x, dz = target.z - this.pos.z, dist = Math.hypot(dx, dz);
    if (dist < reach) { this.av.walk(dt, 0); return true; }
    const step = Math.min(dist, this.speed * scale * dt);
    this.pos.x += dx / dist * step; this.pos.z += dz / dist * step;
    this.yaw = Math.atan2(dx, dz); this.mesh.rotation.y = this.yaw;
    collide(this.pos, 0.3, this.world, this.ignore());
    this.av.floorY = this.world.floorY;
    this.av.walk(dt, dt > 0 ? step / dt : 0);   // the legs swing at the pace, and the bob comes with them
    return false;
  }
  // what is carried rides in front of the chest, the jack and its pallet trail behind
  settle() {
    this.av.setCarry(this.carry ? this.carry.type : null, false);   // arms forward; the item itself rides in front (below)
    if (this.carry && this.carry.mesh) {
      const ahead = new THREE.Vector3(0, 1.05, 0.45).applyAxisAngle(new THREE.Vector3(0, 1, 0), this.yaw);
      this.carry.mesh.position.copy(this.pos).add(ahead); this.carry.mesh.rotation.y = this.yaw;
    }
    if (this.jack) {
      const back = new THREE.Vector3(0, 0, -1.0).applyAxisAngle(new THREE.Vector3(0, 1, 0), this.yaw);
      this.jack.mesh.position.copy(this.pos).add(back); this.jack.mesh.position.y = this.world.floorY; this.jack.mesh.rotation.y = this.yaw + Math.PI;
      if (this.jack.carrying) { this.jack.carrying.mesh.position.copy(this.jack.mesh.position).add(new THREE.Vector3(0, 0.2, 0.55).applyAxisAngle(new THREE.Vector3(0, 1, 0), this.yaw + Math.PI)); this.jack.carrying.mesh.rotation.y = this.yaw; }
    }
  }
}

export class Crew {
  constructor(scene, world, items, install, collide, playerLift) {
    this.scene = scene; this.world = world; this.items = items; this.install = install; this.collide = collide; this.playerLift = playerLift;
    this.helper = null; this.teams = []; this.toasts = [];
    this.names = ['Dave', 'Priya', 'Marco', 'Jules', 'Tom', 'Aisha', 'Ben'];
    this.corridorSpot = (i) => hallToWorld(64.8 - (i % 2) * 0.8, 6.2 + Math.floor(i / 2) * 0.8, world.floorY);
  }

  toast(msg) { this.toasts.push(msg); }
  takeName() { return this.names.shift() || 'Crew'; }

  // called every frame; unlocks follow the columns done
  update(dt, clock, player, columnsDone) {
    const packing = clock.minute >= PACK_UP;
    const scale = 1 - Math.max(0, Math.min(1, (clock.minute / 60 - 25) / 4)) * 0.45;   // the crew tire with the clock
    if (columnsDone >= 1 && !this.helper) {
      this.helper = new Worker(this.scene, this.world, 0xff7a1a, this.takeName()); this.helper.place(this.corridorSpot(0));
      this.helper.state = 'idle'; this.toast(`${this.helper.name} has joined you as a helper`);
    }
    const teamsWanted = Math.min(3, Math.max(0, columnsDone - 1));
    while (this.teams.length < teamsWanted) {
      const i = this.teams.length;
      const a = new Worker(this.scene, this.world, 0xffd21a, this.takeName()), b = new Worker(this.scene, this.world, 0xffd21a, this.takeName());
      a.place(this.corridorSpot(2 + i * 2)); b.place(this.corridorSpot(3 + i * 2));
      const lift = new Lift(this.scene, this.world.floorY); lift.pos.copy(hallToWorld(56.5 + i * 3.4, 8.4, this.world.floorY)); lift.home = lift.pos.clone(); lift.refresh();
      const jack = this.items.spawnJack(hallToWorld(56.5 + i * 3.4, 6.4, this.world.floorY));
      a.lift = lift;
      this.teams.push({ a, b, lift, jack, column: null, state: 'idle', timer: 0, run: null });
      this.toast(`A team of two has joined: ${a.name} and ${b.name}, with their own lift`);
    }
    const claimed = new Set(this.teams.map((t) => t.column && t.column.label).filter(Boolean));
    if (this.helper) this.updateHelper(dt, scale, packing, player, claimed);
    for (const t of this.teams) this.updateTeam(t, dt, scale, packing, claimed, player);
  }

  // every crew member's feet, for the doors
  points() { const p = []; if (this.helper) p.push(this.helper.pos); for (const t of this.teams) { p.push(t.a.pos, t.b.pos, t.lift.pos); } return p; }

  // ---- the helper: works whichever column the player's lift is nearest ----
  updateHelper(dt, scale, packing, player, claimed) {
    const H = this.helper, I = this.items, L = this.playerLift;
    const col = pickColumn(this.install, this.world, L.pos, claimed);
    const pallet = col && I.pallets.find((p) => p.column === col.label);
    const foot = col && footSpot(col);
    const inHall = (m) => worldToHall(m.position).u < HALL.doorU - 0.5;
    const walk = (to, reach) => H.walkTo(to, dt, this.collide, scale, reach);
    H.settle();
    // pack-up: whatever is in hand goes home, then the helper stands by the doors
    if (packing) {
      if (H.jack && H.jack.carrying) { if (walk(this.corridorSpot(0), 1.2)) { H.jack.carrying = null; H.jack.held = false; H.jack = null; } return; }
      if (H.carry) { if (walk(this.corridorSpot(1), 1.0)) this.putDown(H, this.corridorSpot(1)); return; }
      if (H.jack) { if (walk(this.corridorSpot(0), 1.0)) { H.jack.held = false; H.jack = null; } return; }
      walk(hallToWorld(50.5, 7.5, this.world.floorY), 0.8); return;
    }
    if (!col) { walk(hallToWorld(46, 7.5, this.world.floorY), 1.0); return; }
    // 1. a pallet on the jack goes to the foot, whichever side of the doors it is on (2026-09-04:
    // it used to be dropped in the doorway the moment it counted as "in the hall")
    if (H.jack && H.jack.carrying) {
      if (walk(foot, 1.0)) { pallet && pallet === H.jack.carrying ? pallet.mesh.position.copy(foot) : H.jack.carrying.mesh.position.copy(H.jack.mesh.position); H.jack.carrying.mesh.rotation.y = 0; H.jack.carrying = null; H.jack.held = false; I.jack.by = null; H.jack = null; }
      return;
    }
    // the column's pallet is still in the corridor and has boxes: fetch the jack, then the pallet
    if (pallet && pallet.boxes > 0 && !inHall(pallet.mesh) && (!I.jack.held || H.jack) && !H.carry) {
      if (!H.jack) { if (walk(I.jack.mesh.position, 1.0)) { H.jack = I.jack; I.jack.held = true; I.jack.by = 'helper'; } return; }
      if (walk(pallet.mesh.position, 1.5)) H.jack.carrying = pallet;
      return;
    }
    if (H.jack) { H.jack.held = false; I.jack.by = null; H.jack = null; }
    // 2. a box in hand: onto the player's deck if it is down and near, else to the foot
    if (H.carry && H.carry.type === 'box') {
      const deckDown = L.height < 0.3 && !L.box && L.pos.distanceTo(foot) < 8;
      if (deckDown) { if (walk(L.pos, 1.9)) { L.box = H.carry; H.carry.carried = false; H.carry.onLift = true; H.carry = null; L.refresh(); } return; }
      if (walk(foot, 1.3)) this.putDown(H, foot.clone().add(new THREE.Vector3(0.9, 0, 0.6)));
      return;
    }
    // 3. wrap on the floor near the column: bag it; a full bag: to the skip
    if (H.carry && H.carry.type === 'bag') { if (walk(this.world.skip, 2.6)) { H.carry.disposed = true; H.carry.mesh.removeFromParent(); H.carry = null; } return; }
    if (H.carry && H.carry.type === 'wrap') { const bag = I.bags.find((b) => !b.full && !b.disposed); if (!bag) { this.putDown(H, H.pos); return; } if (walk(bag.mesh.position, 1.2)) { bag.wraps++; H.carry.bagged = true; H.carry.mesh.removeFromParent(); H.carry = null; if (bag.wraps >= 8) { bag.full = true; bag.mesh.material.color.setHex(0x41523d); } } return; }
    const wrap = I.wraps.find((w) => !w.bagged && !w.carried && inHall(w.mesh));
    const fullBag = I.bags.find((b) => b.full && !b.disposed && !b.carried);
    const openAtFoot = I.boxes.filter((b) => !b.carried && !b.onLift && !b.disposed && b.lights > 0 && b.mesh.position.distanceTo(foot) < 3).length;
    // 4. keep the foot stocked: up to two open boxes, from the pallet at the foot (or the corridor)
    if (pallet && pallet.boxes > 0 && openAtFoot < 2 && !L.box) {
      if (walk(pallet.mesh.position, 1.4)) { const box = I.spawnBoxFor(pallet); H.carry = box; box.carried = true; }
      return;
    }
    if (fullBag) { if (walk(fullBag.mesh.position, 1.2)) { H.carry = fullBag; fullBag.carried = true; } return; }
    if (wrap) { if (walk(wrap.mesh.position, 1.0)) { H.carry = wrap; wrap.carried = true; } return; }
    // 5. a box at the foot and the deck down and empty: load it
    const spare = I.boxes.find((b) => !b.carried && !b.onLift && !b.disposed && b.lights > 0 && b.mesh.position.distanceTo(foot) < 3);
    if (spare && L.height < 0.3 && !L.box && L.pos.distanceTo(foot) < 8) { if (walk(spare.mesh.position, 1.0)) { H.carry = spare; spare.carried = true; } return; }
    walk(foot.clone().add(new THREE.Vector3(-1.2, 0, -1.0)), 0.6);
  }

  putDown(W, at) {
    const it = W.carry; if (!it) return;
    it.mesh.position.copy(at); it.mesh.position.y = this.world.floorY + (it.type === 'wrap' ? 0.05 : it.type === 'bag' ? 0.41 : 0.2); it.mesh.rotation.set(0, W.yaw, 0);
    it.carried = false; W.carry = null;
  }

  // ---- a team: their own column, their own lift, start to finish ----
  updateTeam(T, dt, scale, packing, claimed, player) {
    const I = this.items, { a, b, lift, jack } = T;
    a.settle(); b.settle();
    const walkA = (to, reach) => a.walkTo(to, dt, this.collide, scale, reach);
    const walkB = (to, reach) => b.walkTo(to, dt, this.collide, scale, reach);
    const home = lift.home;
    if (packing) {
      // the fitter brings the lift down and drives it home; the feeder takes the pallet back
      lift.height = Math.max(0, lift.height - dt * 0.5 * scale);
      if (lift.height <= 0.01) { const d = home.clone().sub(lift.pos); d.y = 0; const dist = d.length(); if (dist > 0.2) { lift.pos.addScaledVector(d.normalize(), Math.min(dist, 1.5 * scale * dt)); this.collide(lift.pos, 0.9, this.world, [lift]); } }
      lift.refresh(); a.place(lift.pos.clone().add(new THREE.Vector3(0, 0, 0))); a.mesh.position.y = this.world.floorY + lift.deckY + lift.height;
      const pallet = T.column && I.pallets.find((p) => p.column === T.column.label);
      if (pallet && worldToHall(pallet.mesh.position).u < HALL.doorU) {
        if (!b.jack) { if (walkB(jack.mesh.position, 1.0)) { b.jack = jack; jack.held = true; } return; }
        if (!b.jack.carrying) { if (walkB(pallet.mesh.position, 1.5)) b.jack.carrying = pallet; return; }
        if (walkB(pallet.home, 1.5)) { pallet.mesh.position.copy(pallet.home); pallet.mesh.rotation.y = 0; b.jack.carrying = null; b.jack.held = false; b.jack = null; }
        return;
      }
      if (b.jack) { b.jack.held = false; b.jack = null; }
      walkB(this.corridorSpot(3), 0.8);
      return;
    }
    if (!T.column) { const c = pickColumn(this.install, this.world, home, claimed); if (!c) return; T.column = c; claimed.add(c.label); T.state = 'pallet'; T.box = 8; }
    const col = T.column, foot = footSpot(col), pallet = I.pallets.find((p) => p.column === col.label);
    const done = !this.install.slots.some((s) => s.column === col.label && !this.install.fitted.has(s.id));
    if (done) { claimed.delete(col.label); T.column = null; T.state = 'idle'; this.toast(`${a.name} and ${b.name} finished column ${col.label}`); return; }
    // the feeder (b): pallet to the foot, then stands by
    if (b.jack && b.jack.carrying) { if (walkB(foot, 1.0)) { b.jack.carrying.mesh.position.copy(foot); b.jack.carrying.mesh.rotation.y = 0; b.jack.carrying = null; b.jack.held = false; b.jack = null; } }
    else if (pallet && pallet.boxes > 0 && worldToHall(pallet.mesh.position).u > HALL.doorU - 0.5) {
      if (!b.jack) { if (walkB(jack.mesh.position, 1.0)) { b.jack = jack; jack.held = true; } }
      else if (walkB(pallet.mesh.position, 1.5)) b.jack.carrying = pallet;
    } else { if (b.jack) { b.jack.held = false; b.jack = null; } walkB(foot.clone().add(new THREE.Vector3(1.4, 0, 1.2)), 0.6); }
    const stocked = pallet && worldToHall(pallet.mesh.position).u < HALL.doorU - 0.5;
    // the fitter (a): on the lift; the lift goes to the next slot, rises to it, fits a light every few seconds
    const runs = this.install.runs.filter((r) => r.column === col.label);
    // one RUN at a time, bottom to top, then the next face: the lift settles once per run instead
    // of driving round the column for every light
    let slot = null; for (const r of runs) { const s = this.install.nextForRun(r); if (s) { slot = s; break; } }
    if (!slot) return;
    const target = col.pos.clone().addScaledVector(slot.normal, 1.75); target.y = this.world.floorY;   // off the shaft's axis along the face normal, the same spot for the whole run
    const want = THREE.MathUtils.clamp(slot.center.y - this.world.floorY - lift.deckY - 0.4, 0, 11.6);
    const d = target.clone().sub(lift.pos); d.y = 0; const dist = d.length();
    if (dist > 0.35) {
      // travel low: come down first, then drive
      if (lift.height > 0.05) lift.height = Math.max(0, lift.height - dt * 0.5 * scale);
      else { lift.pos.addScaledVector(d.normalize(), Math.min(dist, 1.4 * scale * dt)); this.collide(lift.pos, 0.9, this.world, [lift]); }
    } else if (Math.abs(lift.height - want) > 0.05) {
      lift.height += Math.sign(want - lift.height) * Math.min(Math.abs(want - lift.height), dt * 0.5 * scale);
    } else if (stocked || T.box > 0) {
      T.timer += dt * scale;
      if (T.timer > 7) {                       // unwrap and fit: about seven seconds a light, slower when tired
        T.timer = 0;
        if (T.box <= 0) { if (pallet && pallet.boxes > 0) { pallet.boxes--; I.updatePalletStack(pallet); T.box = 8; } else return; }
        T.box--; this.install.fit(slot, { carry: null });
        const wrapMesh = I.makeWrap(); wrapMesh.position.copy(foot).add(new THREE.Vector3((Math.random() - 0.5) * 1.5, 0, (Math.random() - 0.5) * 1.5)); wrapMesh.position.y = this.world.floorY + 0.05; this.scene.add(wrapMesh); I.wraps.push({ type: 'wrap', mesh: wrapMesh, bagged: false });
      }
    }
    lift.refresh();
    a.pos.copy(lift.pos); a.mesh.position.y = this.world.floorY + lift.deckY + lift.height + 0.07;
  }

  // the night's end: everything of the crew's back in the corridor
  resetForNight() {
    if (this.helper) { this.helper.carry = null; this.helper.jack = null; this.helper.place(this.corridorSpot(0)); }
    for (const [i, t] of this.teams.entries()) { t.lift.height = 0; t.lift.pos.copy(t.lift.home); t.lift.refresh(); t.a.place(this.corridorSpot(2 + i * 2)); t.b.place(this.corridorSpot(3 + i * 2)); t.b.jack = null; t.jack.held = false; t.jack.carrying = null; t.jack.mesh.position.copy(hallToWorld(56.5 + i * 3.4, 6.4, this.world.floorY)); t.timer = 0; }
  }

  // for the clean-up check: any crew gear left in the hall
  leftInHall() {
    const out = [];
    const inHall = (m) => worldToHall(m.position).u < HALL.doorU - 0.5;
    for (const t of this.teams) { if (inHall(t.lift.group)) out.push('a team lift'); if (inHall(t.jack.mesh)) out.push('a team jack'); }
    return out;
  }
}
