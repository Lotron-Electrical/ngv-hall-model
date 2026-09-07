import * as THREE from 'three';
import { hallToWorld, worldToHall, HALL, SHEET, snapSheet, sheetCells, sheetRect, sheetSpotWhy, laySheet, protectedAt } from './world.js';
import { Lift } from './lift.js';
import { Avatar } from './avatar.js';

// THE CREW (Lloyd, 2026-09-06: "Can we also add crew from the start. The player should be able to
// allocate tasks to the crew members"). Five of them are in the corridor at 17:00 with two lifts
// and two jacks of their own, and every one does exactly what you tell it: fit a column, feed a
// column, lay the boards out to a column, bring the pallets in, run the rubbish, help you, or
// stand by. Nobody unlocks by columns done any more and nobody picks their own job. Assignments
// stay put across nights; only where everyone stands is reset.
// In a crew room (net.js) the people ARE the crew, so index.html stops calling update() and the
// five stand where they are.

export const CREW_NAMES = ['Dave', 'Priya', 'Marco', 'Jules', 'Tom'];
// one vest each, so a dot in the panel and the figure in the hall are the same person
export const CREW_VESTS = [0xff7a1a, 0xffd21a, 0x33d17a, 0x3aa0ff, 0xff4fa3];
// the task menu, in the order the sheet draws it. `column` = it needs a target; `hall` = the
// target may also be the whole hall
export const TASKS = [
  { id: 'standby', label: 'Stand by', column: false },
  { id: 'fit', label: 'Fit column', column: true },
  { id: 'feed', label: 'Feed column', column: true },
  { id: 'boards', label: 'Lay boards to', column: true, hall: true },
  { id: 'pallets', label: 'Bring pallets in', column: false },
  { id: 'rubbish', label: 'Rubbish', column: false },
  { id: 'help', label: 'Help me', column: false }
];
export const WHOLE_HALL = 'ALL';

// how far off a column its pallet stands (see footSpot). 2.0 m left a 0.5 m slot between the
// column's circle (0.55) and the pallet's (0.95), and a person is 0.6 m wide on the plan: a feeder
// that walked in there before the pallet arrived was pinned for the night. 2.4 m leaves 0.3 m of
// clearance either side of a walker
const FEET_OUT = 2.4;
const PACK_UP = 28.5 * 60;        // 04:30 on the night clock (minutes from midnight)
// the doorway waypoint (crossGoal / walkVia): how near counts as standing at it, and how well
// lined up on the middle counts as ready to walk through. `reach` MUST stay well under `lined`, or
// a walker that stops just inside the reach but still outside the line-up never moves again
// (Claude, 2026-09-07: reach 0.7 against a 0.5 line-up froze the feeder 0.6 m short of the door
// with a whole team standing behind it). `lined` stays under 0.95: half a 2.5 m opening less the
// walker's own 0.3 m, so a lined-up walker is inside the leaves, not pressed on a jamb
const CROSS = { reach: 0.55, lined: 0.85 };
// how far off a column's foot a board still counts as part of its patch
const PATCH_R = 2.6;
// (Claude, 2026-09-07) HOW NEAR "AT THE COLUMN" IS. The last metre round a shaft cannot be
// boarded at all: a sheet must clear the column by 0.6 m, and every grid cell that touches the
// ring is refused for that reason, so no machine can ever park on the run's own spot. The fitter
// that is THIS near the shaft has arrived: it stops pushing at the last metre and works from
// where it stands. Measured to the SHAFT, not to the run's spot -- a machine on the spine beside
// a column is 3.2 m off it and was missing a 3.6 m test on the spot by four centimetres
const PARK_R = 4.6;
// how long a machine tries for a spot it cannot reach before it settles for where it stands
const PARK_WAIT = 6, PARK_AGAIN = 2;
// getting on or off a machine takes a second of ladder, so nobody ever jumps (see climbOn)
const CLIMB = 1.0;


// where a column's pallet stands: BESIDE the shaft, along the hall, on the door side.
// (Claude, 2026-09-07) it used to stand 2.4 m off the column toward the middle, which is exactly
// where the floor protection runs: a 1.9 m pallet circle parked at d 6.2 covers most of the road
// on d 7.5, and every machine driving past it was pushed off the boards and wedged. Along u it is
// the same walk from the column and it is clear of the lane
function footSpot(col) {
  const hd = worldToHall(col.pos);
  return hallToWorld(Math.min(HALL.doorU - 2.0, hd.u + FEET_OUT), hd.d, col.pos.y);
}

// does a sheet laid here have this hall point on it?
function sheetHolds(s, p) {
  const hu = (s.along === 'u' ? SHEET.long : SHEET.short) * 0.5;
  const hd = (s.along === 'u' ? SHEET.short : SHEET.long) * 0.5;
  return Math.abs(p.u - s.u) <= hu && Math.abs(p.d - s.d) <= hd;
}

// (Lloyd, 2026-09-06: floor protection) the next cell of ply the machine needs. The board goes
// UNDER the wheel that has run out of floor, and which cell that is matters: two wheels on an axle
// stand 1.24 m apart, so one 2.4 m sheet holds the pair only when it is laid between them, and the
// cell nearest the blocked wheel is often the one that holds it alone. So every cell that reaches
// the wheel is scored by how many wheels it would put on ply (bare ones counting double) and the
// best one that may actually be laid wins. (Claude, 2026-09-07: the feeder used to snap to the
// wheel's own nearest grid line, lay the board BESIDE that wheel, and the team never entered the
// hall.) Past the wheel the search walks the line the machine is travelling and takes the first
// uncovered cell, so the path comes out a plank road across the way it drives
function nextBoardSpot(world, from, lift, target) {
  const a = worldToHall(lift.pos), b = worldToHall(target);
  const du = b.u - a.u, dd = b.d - a.d, len = Math.hypot(du, dd) || 1;
  const along = Math.abs(du) >= Math.abs(dd) ? 'd' : 'u';    // laid across the direction of travel
  const wheels = world.liftWheels ? world.liftWheels(lift) : [];
  const bare = wheels.filter((w) => !protectedAt(world, w.u, w.d));
  // the board is turned the way the machine travels by preference, but a board the other way up
  // beats no board at all: near the doors the swinging leaves rule out one of the two (2026-09-07)
  const score = (s) => bare.filter((w) => sheetHolds(s, w)).length * 2 + wheels.filter((w) => sheetHolds(s, w)).length + (s.along === along ? 0.5 : 0);
  const cells = sheetCells(from.u, from.d, along).concat(sheetCells(from.u, from.d, along === 'd' ? 'u' : 'd'))
    .map((s) => ({ s, n: score(s) }))
    .sort((x, y) => y.n - x.n || (Math.abs(x.s.u - a.u) + Math.abs(x.s.d - a.d)) - (Math.abs(y.s.u - a.u) + Math.abs(y.s.d - a.d)));
  if (from.u < HALL.doorU - 0.02) for (const c of cells) if (!sheetSpotWhy(world, c.s.u, c.s.d, c.s.along)) return c.s;
  // none of them may be laid: the next cell up the line, but only within three cells of the
  // machine. A board further off than that carries no wheel of this move and is ply thrown away
  const stepU = du / len, stepD = dd / len;
  for (let s = 0.4; s <= 3.6; s += 0.4) {
    const u = from.u + stepU * s, d = from.d + stepD * s;
    if (u >= HALL.doorU - 0.02) continue;
    if (protectedAt(world, u, d)) continue;
    const spot = snapSheet(u, d, along);
    if (!sheetSpotWhy(world, spot.u, spot.d, spot.along)) return spot;
  }
  return null;   // nowhere to put it: the worker holds its board rather than stack ply on ply
}

// a column with work left: nearest to `from` among those not finished (and not claimed)
function pickColumn(install, world, from, claimed) {
  let best = null, bd = Infinity;
  for (const col of world.columns) {
    if (claimed && claimed.has(col.label)) continue;
    const left = install.slots.some((s) => s.column === col.label && !install.fitted.has(s.id));
    if (!left) continue;
    const d = col.pos.distanceTo(from);
    if (d < bd) { bd = d; best = col; }
  }
  return best;
}

class Worker {
  constructor(scene, world, color, name) {
    this.scene = scene; this.world = world; this.name = name; this.colour = color;
    // (2026-09-05) the crew wear the articulated character model (avatar.js), name tag and all
    this.av = new Avatar(color, name); this.mesh = this.av.group; scene.add(this.mesh);
    this.pos = this.mesh.position; this.yaw = 0;
    this.carry = null;             // a box object, a bag, a wrap or a ply sheet
    this.jack = null;              // the jack this one is pushing
    this.lift = null;              // the crew lift it has taken out
    this.helpLift = null;          // the machine of whoever it is working around
    this.onDeck = false;
    this.speed = 2.1;
    // (Lloyd, 2026-09-06) what you told it to do, and what it is doing about it right now
    this.assign = { task: 'standby', target: null };
    this.status = 'standing by';
    this.run = null; this.timer = 0; this.stall = 0; this.boards = 0;
    this.climb = null;             // the second on the ladder, on or off (crew.js climbOn/climbOff)
  }
  place(p) { this.pos.copy(p); this.pos.y = this.world.floorY; this.av.floorY = this.world.floorY; }
  ignore() { const out = []; if (this.carry) out.push(this.carry); if (this.jack && this.jack.carrying) out.push(this.jack.carrying); if (this.lift) out.push(this.lift); if (this.offLift) out.push(this.offLift); if (this.helpLift) out.push(this.helpLift); return out; }
  // standing on the spot, legs settling
  idle(dt) { this.av.floorY = this.world.floorY; this.pos.y = this.world.floorY; this.av.walk(dt, 0); }
  // walk toward a point on the floor; true once within `reach`
  walkTo(target, dt, collide, scale, reach = 0.9) {
    const dx = target.x - this.pos.x, dz = target.z - this.pos.z, dist = Math.hypot(dx, dz);
    if (dist < reach) { this.av.walk(dt, 0); this.pinned = 0; return true; }
    const step = Math.min(dist, this.speed * scale * dt);
    const x0 = this.pos.x, z0 = this.pos.z;
    this.pos.x += dx / dist * step; this.pos.z += dz / dist * step;
    this.yaw = Math.atan2(dx, dz); this.mesh.rotation.y = this.yaw;
    collide(this.pos, 0.3, this.world, this.ignore());
    // (Claude, 2026-09-07) PINNED. Two circles that a walker cannot pass between held a worker
    // still for the rest of the night, standing on the spot with its errand a metre away. A step
    // that goes nowhere for a second becomes a SIDESTEP: the same pace ACROSS the way it was
    // heading, which walks it out of the slot and round the thing in it. If that side is shut too
    // it tries the other after a couple of seconds
    const moved = Math.hypot(this.pos.x - x0, this.pos.z - z0);
    this.pinned = moved < step * 0.35 ? (this.pinned || 0) + dt : 0;
    if (this.pinned > 0.9) {
      if (this.pinned > 3.0) { this.pinned = 0.9; this.side = -(this.side || 1); }
      const s = this.side || (this.side = 1);
      this.pos.x += (dz / dist) * step * s; this.pos.z += -(dx / dist) * step * s;
      collide(this.pos, 0.3, this.world, this.ignore());
    }
    this.av.floorY = this.world.floorY;
    this.av.walk(dt, dt > 0 ? step / dt : 0);   // the legs swing at the pace, and the bob comes with them
    return false;
  }
  // what is carried rides in front of the chest, the jack and its pallet trail behind
  settle() {
    // (Claude, 2026-09-07) the machine you have just climbed off is not a wall for a few paces:
    // stepping off puts you at the foot of the ladder, INSIDE its own plan circles, and at a
    // column that is a slot too narrow to walk out of. It stops being ignored once you are clear
    if (this.offLift && this.pos.distanceTo(this.offLift.pos) > 3.0) this.offLift = null;
    this.av.setCarry(this.carry ? this.carry.type : null, false);   // arms forward; the item itself rides in front (below)
    if (this.carry && this.carry.mesh) {
      // a 2.4 m ply sheet is carried flat at hip height with its long side ALONG the walk, so it
      // does not sweep the room as the feeder turns (Lloyd, 2026-09-06)
      const sheet = this.carry.type === 'sheet';
      const ahead = new THREE.Vector3(0, sheet ? 0.9 : 1.05, sheet ? 0.55 : 0.45).applyAxisAngle(new THREE.Vector3(0, 1, 0), this.yaw);
      this.carry.mesh.position.copy(this.pos).add(ahead); this.carry.mesh.rotation.y = this.yaw + (sheet ? Math.PI / 2 : 0);
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
    this.scene = scene; this.world = world; this.items = items; this.install = install;
    this.collide = collide; this.playerLift = playerLift;
    this.toasts = []; this.said = new Set();
    this.members = []; this.lifts = []; this.jacks = [];
    // THE AISLE (Claude, 2026-09-07). The corridor's two pallet rows leave 4.1 m of clear floor
    // between them and a scissor lift's plan circles take 2.0 m of it, so the crew's machines park
    // down the MIDDLE of that band: about a metre of lane is left either side of them, which is a
    // walker's width, and both pallet rows can still be reached. Parked against one row instead,
    // a lift left a 14 cm slot beside it and a walker that aimed straight through was stuck there
    // for the night. The five wait in the north lane, 5 m back from the doorway so they do not
    // hold the doors open all shift
    this.corridorSpot = (i) => hallToWorld(58.6 - Math.floor(i / 2) * 1.3, 8.5 + (i % 2) * 0.7, world.floorY);
    for (const [i, name] of CREW_NAMES.entries()) {
      const W = new Worker(scene, world, CREW_VESTS[i], name);
      W.index = i;
      W.place(this.corridorSpot(i));
      this.members.push(W);
    }
    // TWO crew lifts and TWO crew jacks, in storage from the start. A lift is a shared tool: the
    // first fitter who needs one takes a free one, and it goes back on the list where it stands
    for (let i = 0; i < 2; i++) {
      const L = new Lift(scene, world.floorY);
      L.pos.copy(hallToWorld(59.5 + i * 3.5, 7.35 + i * 0.3, world.floorY));
      L.home = L.pos.clone(); L.by = null; L.crew = true;
      L.noSpot = 0; L.parked = false; L.parkedAt = null; L.stuckCol = null;
      L.refresh();
      this.lifts.push(L);
      const j = items.spawnJack(hallToWorld(60.0 + i * 3.5, 8.9, world.floorY));
      j.home = j.mesh.position.clone();
      this.jacks.push(j);
    }
  }

  toast(msg) { this.toasts.push(msg); }
  // a line that must be said once, not every frame (a stall, an empty stack, no free machine)
  sayOnce(key, msg) { if (this.said.has(key)) return false; this.said.add(key); this.toast(msg); return true; }
  byName(name) { return this.members.find((m) => m.name === name) || null; }
  columnOf(label) { return this.world.columns.find((c) => c.label === label) || null; }
  inHall(mesh) { return worldToHall(mesh.position).u < HALL.doorU - 0.5; }

  // ---- assigning ----
  // the ONE way a task is given out (the task sheet, the panel and any script go through here):
  // whatever the member was doing is put down sensibly first
  assignTask(who, task, target = null) {
    const W = typeof who === 'string' ? this.byName(who) : who;
    if (!W) return null;
    const T = TASKS.find((t) => t.id === task) || TASKS[0];
    if (T.column && !target) return null;
    this.dropWork(W);
    W.assign = { task: T.id, target: T.column ? target : null };
    W.status = 'standing by';
    W.run = null; W.timer = 0; W.stall = 0; W.plan = null; W.planFor = null; W.fetching = false; W.worked = false;
    W.jackWait = 0; W.skipJacks = null; W.blockedFor = 0; W.liftWait = 0; W.liftBest = Infinity;
    this.said.delete('nolift:' + W.name);
    this.toast(`${W.name}: ${this.taskText(W.assign)}`);
    return W;
  }

  // the words for an assignment, for the toast and the panel row
  taskText(a) {
    if (!a) return 'stand by';
    switch (a.task) {
      case 'fit': return `fit ${a.target}`;
      case 'feed': return `feed ${a.target}`;
      case 'boards': return `boards to ${a.target === WHOLE_HALL ? 'the whole hall' : a.target}`;
      case 'pallets': return 'bring pallets in';
      case 'rubbish': return 'rubbish';
      case 'help': return 'help me';
      default: return 'stand by';
    }
  }

  // reassigned mid-job: a box or a bag goes down where it stands, a jacked pallet is set down, a
  // board in the hands is laid if the spot is good and otherwise goes back on a stack. The MACHINE
  // is not dropped here -- it comes down first and the member climbs off (parkLift)
  dropWork(W) {
    // told to do something else halfway up the ladder: he lets go and stands on the floor where he
    // is. The machine stays ignored by the collider until he is clear of it (settle, offLift)
    if (W.climb) { W.offLift = W.climb.L; W.climb = null; W.onDeck = false; W.pos.y = this.world.floorY; W.av.floorY = this.world.floorY; }
    if (W.carry) this.putDown(W, W.pos.clone());
    if (W.jack) this.dropJack(W, true); else this.unclaimJacks(W);
    this.unclaimLoads(W);
    W.helpLift = null;
  }

  // ---- shared tools ----
  freeLift() { return this.lifts.find((L) => !L.by) || null; }
  takeLift(W) { const L = this.freeLift(); if (!L) return null; L.by = W; W.lift = L; W.onDeck = false; return L; }
  // the machine is left where it stands with the deck down: it comes down, the member climbs off,
  // and the lift goes back on the free list. True once the member has both feet on the floor.
  // (Claude, 2026-09-07) A MAN WHO IS NOT ON IT DOES NOT COME BACK TO IT. Reassigning a fitter who
  // was away down the hall fetching a box used to snap him to the ladder foot -- 11 m in one 50 ms
  // frame. He is already standing on the floor: the deck still comes down and the machine still
  // goes back on the list, but he stays exactly where he is
  parkLift(W, dt, scale) {
    const L = W.lift;
    if (!L) return true;
    L.height = Math.max(0, L.height - dt * 0.5 * scale);
    L.refresh();
    if (W.onDeck) {
      W.status = 'stepping off the lift';
      this.rideDeck(W);
      if (L.height > 0.01) return false;
      this.climbOff(W, L);
      return false;
    }
    this.releaseLift(W, L);
    return true;
  }
  // the machine goes back on the free list where it stands, deck down
  releaseLift(W, L) {
    W.onDeck = false; W.fetching = false; W.run = null;
    L.by = null; L.needBoards = null; L.parked = false; L.parkedAt = null; L.noSpot = 0; L.stallToast = false; L.stuckCol = null;
    W.lift = null; W.offLift = L;
  }
  rideDeck(W) {
    const L = W.lift; if (!L) return;
    W.pos.copy(L.pos);
    W.mesh.position.y = this.world.floorY + L.deckY + L.height + 0.07;
    W.av.floorY = W.mesh.position.y;
    W.mesh.rotation.y = W.yaw = L.yaw + Math.PI / 2;
  }
  // (Claude, 2026-09-07) THE LADDER. Getting on used to be a snap: the walk stopped up to 1.3 m
  // short of the ladder foot, which is itself 2 m behind the chassis centre, and the next line put
  // the man on the deck -- a 3 m jump in one frame, and 1.3 m of it straight up. Now it takes a
  // second, the way the player's own boarding animation does: he slides along the machine and up
  // the ladder, and nothing else he does happens while it runs (update)
  climbOn(W, L, say) { W.climb = { L, up: true, t: 0, from: W.pos.clone(), say: say || 'walking to the lift' }; }
  climbOff(W, L) { W.climb = { L, up: false, t: 0, from: W.pos.clone(), say: 'stepping off the lift' }; }
  stepClimb(W, dt) {
    const C = W.climb, L = C.L;
    C.t += dt;
    const k = Math.min(1, C.t / CLIMB);
    const foot = L.offboardWorld(); foot.y = this.world.floorY;
    const deckY = this.world.floorY + L.deckY + L.height + 0.07;
    const to = C.up ? L.pos : foot;
    const y0 = C.up ? this.world.floorY : deckY, y1 = C.up ? deckY : this.world.floorY;
    W.pos.x = C.from.x + (to.x - C.from.x) * k;
    W.pos.z = C.from.z + (to.z - C.from.z) * k;
    W.pos.y = y0 + (y1 - y0) * k;
    W.av.floorY = W.pos.y;
    W.mesh.rotation.y = W.yaw = L.yaw + Math.PI / 2;
    W.av.walk(dt, 0);
    W.status = C.say;
    if (k < 1) return;
    W.climb = null;
    if (C.up) { W.onDeck = true; W.fetching = false; this.rideDeck(W); }
    else { W.onDeck = false; W.place(foot); }
  }
  // a jack nobody else has claimed: one of the crew's two, or the player's when he is not holding
  // it. `by` is set the moment it is chosen, so two members never walk at the same one -- and the
  // one this member ALREADY claimed comes back first. (Claude, 2026-09-07: without that last line
  // a worker walking to a jack claimed a second one on the next frame, then the third, then found
  // none free and stood still for the rest of the night with all three reserved to him)
  allJacks() { return this.items.jack ? this.jacks.concat([this.items.jack]) : this.jacks.slice(); }
  // the crew's own first, and of those the NEAREST: taking them in build order sent a man in the
  // corridor's east end back to the west end past everybody else's machines
  reserveJack(W) {
    const mine = this.allJacks().find((j) => j.by === W.name);
    if (mine) return mine;
    const skip = W.skipJacks || [];
    const free = this.allJacks().filter((j) => !j.by && !j.held && !skip.includes(j));
    free.sort((a, b) => (this.jacks.includes(b) ? 1 : 0) - (this.jacks.includes(a) ? 1 : 0)
      || a.mesh.position.distanceTo(W.pos) - b.mesh.position.distanceTo(W.pos));
    if (!free.length) { W.skipJacks = null; return null; }   // none left: forget the grudges and try again next frame
    free[0].by = W.name;
    return free[0];
  }
  // walk to the claimed jack and pick it up. True once it is in his hands.
  // (Claude, 2026-09-07) A JACK HE CANNOT GET AT. One member claimed the player's jack in the far
  // corner of the store, could not thread the pallet rows to it, and stood there for the rest of
  // the night with the last pallet of the pack-up still out in the hall and two free jacks beside
  // him. Twelve seconds of getting nowhere and the claim goes back, with that jack off HIS list
  fetchJack(W, dt, scale) {
    if (W.jack) return true;
    const j = this.reserveJack(W);
    if (!j) { W.jackWait = 0; W.idle(dt); return false; }
    if (this.walkVia(W, j.mesh.position, dt, scale, 1.0)) { W.jack = j; j.held = true; W.jackWait = 0; W.skipJacks = null; return true; }
    W.jackWait = (W.jackWait || 0) + dt;
    if (W.jackWait > 12) { j.by = null; W.jackWait = 0; (W.skipJacks = W.skipJacks || []).push(j); }
    return false;
  }
  dropJack(W, setPalletDown = false) {
    const j = W.jack;
    this.unclaimJacks(W);
    if (!j) return;
    if (setPalletDown && j.carrying) { this.setDown(j.carrying, j.mesh.position); j.carrying = null; }
    j.held = false; j.by = null; W.jack = null;
  }
  // a claim that never turned into a pick-up is let go: nobody keeps a jack reserved for a job
  // they have moved on from
  unclaimJacks(W) { for (const j of this.allJacks()) if (j.by === W.name && j !== W.jack) { j.by = null; j.held = false; } }
  // the same for a pallet or a stack claimed for the pack-up run (strayLoad)
  unclaimLoads(W) { for (const p of (this.items.pallets || []).concat(this.items.stacks || [])) if (p.by === W.name && (!W.jack || W.jack.carrying !== p)) p.by = null; }
  jackHome(j) { return j.home || hallToWorld(68.0, 4.4, this.world.floorY); }

  putDown(W, at) {
    const it = W.carry; if (!it) return;
    // (Claude, 2026-09-07) A BOARD IS NOT A BOX. Every "put down what you are holding" path -- a
    // reassignment, a column finished under a worker, the pallet run, standing by -- used to drop
    // a 2.4 m ply sheet on the floor like a carton: the mesh lay there in neither world.sheets nor
    // a stack, and the hall's 150 sheets quietly became 149. It goes down as floor protection
    // where he stands if the spot is good, and otherwise back on a pallet of ply
    if (it.type === 'sheet') { this.dropSheet(W); return; }
    it.mesh.position.copy(at); it.mesh.position.y = this.world.floorY + (it.type === 'wrap' ? 0.05 : it.type === 'bag' ? 0.41 : 0.2); it.mesh.rotation.set(0, W.yaw, 0);
    it.carried = false; W.carry = null;
  }

  // the board in the hands, put away on the spot: laid where he stands when that cell is free,
  // else handed back to the nearest stack. The count of ply in the hall never changes here
  dropSheet(W) {
    const h = worldToHall(W.pos), spot = snapSheet(h.u, h.d, 'd');
    if (h.u < HALL.doorU && !sheetSpotWhy(this.world, spot.u, spot.d, spot.along)) laySheet(this.world, spot.u, spot.d, spot.along);
    else if (this.items.returnSheet) this.items.returnSheet(W.pos);
    if (W.carry.mesh) W.carry.mesh.removeFromParent();
    W.carry = null;
  }

  nearestStack(from) {
    let best = null, bd = Infinity;
    for (const s of this.items.stacks || []) { if (s.sheets <= 0) continue; const d = s.mesh.position.distanceTo(from); if (d < bd) { bd = d; best = s; } }
    return best;
  }

  // ---- walking ----
  // where a machine nobody is driving actually steers for this frame: back on to the middle line,
  // through the doorway, clear of it, up the spine, then off across the column's patch
  travelGoal(lift, target) {
    const a = worldToHall(lift.pos), b = worldToHall(target);
    const mid = (u) => hallToWorld(u, HALL.doorD, this.world.floorY);
    // (Claude, 2026-09-07) BACK ON THE ROAD FIRST. A machine standing at a column and heading out
    // is off the spine, on its column's patch: it returns to the middle line at its own u before
    // it starts down the hall, because that is where the ply is
    if (a.u < HALL.doorU - 3.4 && b.u >= HALL.doorU && Math.abs(a.d - HALL.doorD) > 0.6) return mid(a.u);
    // the doorway is 2.5 m wide and a straight line from the corridor to a column misses it: a
    // machine on the wrong side of the door line lines up on the opening first (2.2 m out, on the
    // centre line), drives through it, and only then heads for the column (2026-09-06: without
    // this the crew wedge on the wall)
    if ((a.u < HALL.doorU) !== (b.u < HALL.doorU)) {
      const side = a.u < HALL.doorU ? -1 : 1;
      const off = Math.abs(a.d - HALL.doorD) > 0.25 ? 2.2 * side : -1.6 * side;
      return hallToWorld(HALL.doorU + off, HALL.doorD, this.world.floorY);
    }
    if (a.u >= HALL.doorU) return target;                       // both in the corridor: concrete, drive straight
    // (Claude, 2026-09-07) CLEAR THE DOORWAY BEFORE TURNING OFF. A machine that starts across the
    // room the moment its nose is inside drags its back corner over the door line, and the board
    // it needs there cannot be laid: the leaves swing over that strip of floor. So it drives up
    // the middle until the whole chassis is 3.4 m in
    if (a.u > HALL.doorU - 3.4 && b.u < HALL.doorU - 3.4) return mid(HALL.doorU - 3.6);
    // FOLLOW THE SPINE. The protection is a road up the middle of the hall with a patch at each
    // column: a machine that cuts the corner drives straight off it. So it stays on the middle
    // line until it is level with the column, then turns off across the patch
    if (Math.abs(b.u - a.u) > 2.4) return mid(b.u);
    return target;
  }
  // the same for a person: the opening is 2.5 m of a 15 m wall, so a walker whose errand is on
  // the other side of the door line aims at the middle of it first instead of pressing on a jamb
  crossGoal(from, target) {
    const a = worldToHall(from), b = worldToHall(target);
    if ((a.u < HALL.doorU) === (b.u < HALL.doorU)) return target;
    const side = a.u < HALL.doorU ? -1 : 1;
    const off = Math.abs(a.d - HALL.doorD) > CROSS.lined ? 1.2 * side : -1.2 * side;
    return hallToWorld(HALL.doorU + off, HALL.doorD, this.world.floorY);
  }
  // walk to `to`, by way of the doorway when it is on the other side. True only on arriving at
  // the errand itself, never at the waypoint. CROSS.reach is what "standing at the waypoint"
  // means, and it is tighter than the line-up on purpose (see CROSS above)
  walkVia(W, to, dt, scale, reach) {
    const goal = this.crossGoal(W.pos, to);
    const there = W.walkTo(goal, dt, this.collide, scale, goal === to ? reach : CROSS.reach);
    return goal === to && there;
  }

  // every crew member's feet and every machine of theirs, for the doors
  points() { const p = []; for (const m of this.members) p.push(m.pos); for (const L of this.lifts) p.push(L.pos); return p; }

  // ---- the frame ----
  update(dt, clock, player, columnsDone) {
    const packing = clock.minute >= PACK_UP;
    const scale = 1 - Math.max(0, Math.min(1, (clock.minute / 60 - 25) / 4)) * 0.45;   // the crew tire with the clock
    this.packing = packing;
    // one pass over the 768 slots a frame, not one per member: how far each column has got
    this.stats = new Map();
    for (const s of this.install.slots) {
      let e = this.stats.get(s.column);
      if (!e) { e = { n: 0, total: 0 }; this.stats.set(s.column, e); }
      e.total++;
      if (this.install.fitted.has(s.id)) e.n++;
    }
    for (const W of this.members) {
      W.settle();
      if (W.climb) { this.stepClimb(W, dt); continue; }   // a second on the ladder, and nothing else
      if (packing) this.packUp(W, dt, scale);
      else this.runTask(W, dt, scale, player);
    }
  }

  columnDone(label) { const e = this.stats && this.stats.get(label); return !!e && e.n >= e.total; }
  columnCount(label) { const e = this.stats && this.stats.get(label); return e ? `${e.n}/${e.total}` : '0/0'; }

  runTask(W, dt, scale, player) {
    switch (W.assign.task) {
      case 'fit': return this.doFit(W, dt, scale);
      case 'feed': return this.doFeed(W, dt, scale, player);
      case 'boards': return this.doBoards(W, dt, scale);
      case 'pallets': return this.doPallets(W, dt, scale);
      case 'rubbish': return this.doRubbish(W, dt, scale);
      case 'help': return this.doHelp(W, dt, scale, player);
      default: return this.doStandby(W, dt, scale);
    }
  }

  // the job is over: back on standby, with a line to say so
  finish(W, msg) {
    if (msg) this.toast(msg);
    W.assign = { task: 'standby', target: null };
    W.status = 'standing by';
    W.run = null; W.plan = null; W.planFor = null;
  }

  // ---- 1. stand by: out of the way, by the doors ----
  doStandby(W, dt, scale) {
    if (W.lift && !this.parkLift(W, dt, scale)) return;
    if (W.carry) { this.putDown(W, W.pos.clone()); return; }
    if (W.jack) { W.status = 'putting the jack back'; if (this.walkVia(W, this.jackHome(W.jack), dt, scale, 1.0)) this.dropJack(W, true); return; }
    W.status = 'standing by';
    W.helpLift = null;
    this.walkVia(W, this.corridorSpot(W.index), dt, scale, 0.8);
  }

  // ---- 2. the FITTER: a machine, a column, run by run bottom to top ----
  doFit(W, dt, scale) {
    const col = this.columnOf(W.assign.target);
    if (!col) { this.finish(W, null); return; }
    if (this.columnDone(col.label)) { this.finish(W, W.worked ? `${W.name} finished column ${col.label}` : null); W.worked = false; return; }
    // a free machine, or a stand and a line about it
    if (!W.lift) {
      if (!this.takeLift(W)) { W.status = 'waiting for a lift'; this.sayOnce('nolift:' + W.name, `No free lift for ${W.name}`); W.idle(dt); return; }
      this.said.delete('nolift:' + W.name);
    }
    const L = W.lift, foot = footSpot(col);
    // he has not climbed on yet; `fetching` means he is off the deck ON PURPOSE (a box run), and
    // that is not the same thing as never having been aboard
    if (!W.onDeck && !W.fetching) {
      W.status = 'walking to the lift';
      if (this.walkVia(W, L.offboardWorld(), dt, scale, 1.3)) this.climbOn(W, L);
      return;
    }
    // ONE RUN at a time, bottom to top, then the next face: the machine settles once per run
    // instead of driving round the column for every light. Two fitters on one column take
    // different runs, so they never fight over the same bar
    const runs = this.install.runs.filter((r) => r.column === col.label);
    if (W.run && !this.install.nextForRun(W.run)) W.run = null;
    if (!W.run) {
      const taken = new Set(this.members.filter((m) => m !== W && m.run).map((m) => m.run));
      W.run = runs.find((r) => this.install.nextForRun(r) && !taken.has(r)) || null;
    }
    const slot = W.run && this.install.nextForRun(W.run);
    // (Claude, 2026-09-07) NOBODY IS SNAPPED ONTO A DECK HE IS NOT ON. Every run on the column
    // taken by the other fitter and this one away fetching a box: rideDeck pulled him off the
    // floor and onto the machine in one frame -- six metres along the hall and 1.3 m into the air.
    // On the deck he waits on the deck; on the floor he walks back to the ladder like anyone else
    if (!slot) { W.status = 'standing by'; if (W.onDeck) this.rideDeck(W); else W.fetching = false; return; }
    const target = col.pos.clone().addScaledVector(slot.normal, 1.75); target.y = this.world.floorY;
    L.target = target;
    L.goal = this.travelGoal(L, target);   // the feeder boards toward the SAME point the machine steers for
    const flat = Math.hypot(target.x - L.pos.x, target.z - L.pos.z);
    const atCol = Math.hypot(col.pos.x - L.pos.x, col.pos.z - L.pos.z);
    // (Claude, 2026-09-07) PARKED. A machine that cannot get the last metre -- because the cell
    // that would carry its wheels lies through the shaft, or because the column's own pallet
    // stands in the way -- works from where it is instead of pushing at it all night. A new run's
    // target unparks it and it tries again.
    // The test used to be "within 3.6 m of the run's own spot", and a lone fitter on N6 stood on
    // the spine 3.64 m off it saying `waiting for boards near N6` for the rest of the night with
    // nobody assigned to boards (the skeptic's D3). It is measured to the SHAFT now: a machine
    // this near the column has arrived, whichever face the next run is on. Once one face has
    // beaten it, it gives the next one a shorter try (PARK_AGAIN), so a column is not eight
    // separate waits -- but it does still try, because a boards worker may have laid more ply
    if (L.parked && (!L.parkedAt || L.parkedAt.distanceTo(target) > 0.5)) { L.parked = false; L.noSpot = 0; W.stall = 0; }
    // somebody IS bringing the ply: then the only thing that parks the machine is that worker
    // reporting there is nowhere left to lay it (`noSpot`). The stall clock is for a fitter with
    // nobody coming -- it must not cut across a feeder who is halfway through the road
    const helper = this.members.some((m) => m !== W && ((m.assign.task === 'feed' && m.assign.target === col.label)
      || (m.assign.task === 'boards' && (m.assign.target === col.label || m.assign.target === WHOLE_HALL))));
    const patience = L.stuckCol === col.label ? PARK_AGAIN : PARK_WAIT;
    if (!L.parked && atCol < PARK_R && ((L.noSpot || 0) > 5 || (!helper && W.stall > patience))) {
      L.parked = true; L.parkedAt = target.clone(); L.needBoards = null; L.stuckCol = col.label;
      L.stallToast = false;
    }
    // a machine drives with its driver aboard: while he is down fetching a box it stands still
    const travelling = flat > 0.35 && !L.parked && W.onDeck;
    if (travelling) {
      // travel low: come down first, then drive, and only ever onto floor protection
      if (L.height > 0.05) { L.height = Math.max(0, L.height - dt * 0.5 * scale); W.status = `rolling to ${col.label}`; }
      else if (L.roll(L.goal, 1.4 * scale * dt, this.world, this.collide)) { W.status = `rolling to ${col.label}`; W.stall = 0; L.stallToast = false; L.stuckCol = null; }
      else if (L.needBoards) {
        W.status = `waiting for boards near ${col.label}`;
        W.stall += dt;
        if (W.stall > 4 && !L.stallToast) { L.stallToast = true; this.toast(`${W.name}'s lift is waiting for boards near ${col.label}`); }
      } else {
        W.status = `rolling to ${col.label}`; W.stall += dt;
        // (Claude, 2026-09-07) nose to nose with another machine parked in the corridor: a head-on
        // push is exactly cancelled by the drive, so it eases ACROSS and goes round. Only on the
        // concrete, where a step sideways costs no ply
        if (W.stall > 1.5 && worldToHall(L.pos).u > HALL.doorU) {
          if (W.stall > 5) { W.stall = 1.5; W.sideL = -(W.sideL || 1); }
          const dir = L.goal.clone().sub(L.pos); dir.y = 0; dir.normalize();
          const across = new THREE.Vector3(-dir.z, 0, dir.x).multiplyScalar(W.sideL || 1);
          L.roll(L.pos.clone().addScaledVector(across, 2.5), 1.4 * scale * dt, this.world, this.collide);
        }
      }
      L.refresh(); this.rideDeck(W);
      return;
    }
    W.stall = 0;
    // at the run: the deck rises to the bar, then a light goes in about every seven seconds
    const want = THREE.MathUtils.clamp(slot.center.y - this.world.floorY - L.deckY - 0.4, 0, 11.6);
    const box = L.box && L.box.lights > 0 ? L.box : null;
    if (!box) { this.getBox(W, dt, scale, col, foot); return; }
    // the same rule: a fitter down on the floor when the feeder loads his deck walks back to the
    // ladder and climbs it. Reaching the fitting code below off the deck teleported him onto it
    if (!W.onDeck) { W.status = 'fetching boxes'; if (this.walkVia(W, L.offboardWorld(), dt, scale, 1.7)) this.climbOn(W, L, 'walking to the lift'); return; }
    W.worked = true;
    if (Math.abs(L.height - want) > 0.05) {
      L.height += Math.sign(want - L.height) * Math.min(Math.abs(want - L.height), dt * 0.5 * scale);
      W.status = `fitting ${col.label} (${this.columnCount(col.label)})`;
      L.refresh(); this.rideDeck(W);
      return;
    }
    W.timer += dt * scale;
    W.status = `fitting ${col.label} (${this.columnCount(col.label)})`;
    if (W.timer > 7) {                       // unwrap and fit: about seven seconds a light, slower when tired
      W.timer = 0;
      box.lights--;
      this.install.fit(slot, { carry: null });
      const wrapMesh = this.items.makeWrap();
      wrapMesh.position.copy(foot).add(new THREE.Vector3((Math.random() - 0.5) * 1.5, 0, (Math.random() - 0.5) * 1.5));
      wrapMesh.position.y = this.world.floorY + 0.05;
      this.scene.add(wrapMesh);
      this.items.wraps.push({ type: 'wrap', mesh: wrapMesh, bagged: false });
      if (box.lights <= 0) this.emptyBoxOff(L, foot);
    }
    L.refresh(); this.rideDeck(W);
  }

  // the empty carton comes off the deck and goes on the floor at the foot, so the feeder (or you)
  // can put a full one up. A deck with an empty box on it can take nothing
  emptyBoxOff(L, foot) {
    const b = L.box; if (!b) return;
    L.box = null;
    b.onLift = false; b.deck = null; b.vel = null; b.carried = false; b.type = 'emptyBox';
    if (b.mesh) { if (b.mesh.material && b.mesh.material.color) b.mesh.material.color.setHex(0x6f6250); b.mesh.position.copy(foot).add(new THREE.Vector3(0.9, 0, 0.9)); b.mesh.position.y = this.world.floorY + 0.17; }
    L.refresh();
  }

  // the fitter's stock: the box on the deck, then an open one at the foot, then the column's own
  // pallet. The long walk to a pallet still in the corridor is his only when nobody is feeding him
  getBox(W, dt, scale, col, foot) {
    const I = this.items, L = W.lift;
    if (L.box) { this.emptyBoxOff(L, foot); return; }
    // (Claude, 2026-09-07) A CARTON ALREADY IN HIS HANDS GOES UP FIRST. The stock test below used
    // to run ahead of this: taking the LAST carton off a pallet empties it, so the next frame told
    // a fitter walking back with that carton that there was nothing to fetch, and he climbed on
    // holding it and sat there for the rest of the night. A column stopped dead at 56 of 64
    if (W.carry && W.carry.type === 'box') {
      W.status = 'fetching boxes';
      const load = () => { const b = W.carry; b.carried = false; b.onLift = true; b.deck = null; b.vel = null; L.box = b; W.carry = null; L.refresh(); };
      if (W.onDeck) { load(); this.rideDeck(W); return; }
      if (this.walkVia(W, L.offboardWorld(), dt, scale, 1.7)) { load(); this.climbOn(W, L, 'fetching boxes'); }
      return;
    }
    const feeder = this.members.find((m) => m !== W && m.assign.task === 'feed' && m.assign.target === col.label);
    const spare = I.boxes.find((b) => !b.carried && !b.onLift && !b.disposed && !b.deck && b.lights > 0 && b.mesh.position.distanceTo(foot) < 3.2);
    const pallet = I.pallets.find((p) => p.column === col.label);
    const palletIn = pallet && this.inHall(pallet.mesh);
    const fromPallet = pallet && pallet.boxes > 0 && (palletIn || !feeder);
    if (!spare && !fromPallet) {
      // somebody else is bringing it: wait on the deck rather than walk the hall for nothing
      W.status = feeder ? 'waiting for boxes' : 'fetching boxes';
      if (W.onDeck) { this.rideDeck(W); return; }
      if (this.walkVia(W, L.offboardWorld(), dt, scale, 1.7)) this.climbOn(W, L, W.status);
      return;
    }
    W.status = 'fetching boxes';
    if (L.height > 0.01) { L.height = Math.max(0, L.height - dt * 0.6 * scale); L.refresh(); if (W.onDeck) this.rideDeck(W); return; }
    if (W.onDeck) { this.climbOff(W, L); W.fetching = true; W.offLift = L; return; }
    // anything else in his hands (an empty carton he was left holding) goes on the floor first
    if (W.carry) { this.putDown(W, W.pos.clone()); return; }
    const to = spare ? spare.mesh.position : pallet.mesh.position;
    if (this.walkVia(W, to, dt, scale, spare ? 1.0 : 1.5)) {
      if (spare) { W.carry = spare; spare.carried = true; }
      else { const b = I.spawnBoxFor(pallet); W.carry = b; b.carried = true; }
    }
  }

  // ---- 3. the FEEDER: the pallet in, boxes on the deck, wrap in a bag, boards when the machine
  // has run out of floor ----
  doFeed(W, dt, scale, player) {
    const I = this.items, col = this.columnOf(W.assign.target);
    if (!col) { this.finish(W, null); return; }
    if (this.columnDone(col.label)) { this.finish(W, null); return; }
    if (W.lift && !this.parkLift(W, dt, scale)) return;
    const foot = footSpot(col), pallet = I.pallets.find((p) => p.column === col.label);
    const fitter = this.members.find((m) => m !== W && m.assign.task === 'fit' && m.assign.target === col.label && m.lift);
    const L = fitter ? fitter.lift : this.playerLift;
    W.helpLift = fitter ? fitter.lift : null;
    const walk = (to, reach) => this.walkVia(W, to, dt, scale, reach);
    // BOARDS FIRST: a pallet at the foot is no use if the machine cannot reach the column
    if (fitter && this.layAhead(W, fitter, dt, scale)) return;
    // a pallet in the air comes down at the foot, whichever side of the doors it is on
    if (W.jack && W.jack.carrying) {
      W.status = `bringing the ${col.label} pallet in`;
      if (walk(foot, 1.0)) { const p = W.jack.carrying; p.mesh.position.copy(foot); p.mesh.rotation.y = 0; W.jack.carrying = null; this.dropJack(W); }
      return;
    }
    if (pallet && pallet.boxes > 0 && !this.inHall(pallet.mesh) && !W.carry) {
      W.status = `bringing the ${col.label} pallet in`;
      if (!W.jack) { this.fetchJack(W, dt, scale); return; }
      if (walk(pallet.mesh.position, 1.5)) W.jack.carrying = pallet;
      return;
    }
    if (W.jack) this.dropJack(W);
    // a box in hand: onto the deck when it is down and empty, else to the foot
    if (W.carry && (W.carry.type === 'box' || W.carry.type === 'emptyBox')) {
      W.status = `feeding ${col.label}`;
      const near = L && L.pos.distanceTo(foot) < (fitter ? 12 : 8);
      if (W.carry.type === 'box' && L && near && L.height < 0.3 && !L.box) {
        if (walk(L.pos, 1.9)) { L.box = W.carry; W.carry.carried = false; W.carry.onLift = true; W.carry.deck = null; W.carry = null; L.refresh(); }
        return;
      }
      if (walk(foot, 1.3)) this.putDown(W, foot.clone().add(new THREE.Vector3(0.9, 0, 0.6)));
      return;
    }
    if (this.doRubbishHands(W, dt, scale)) return;
    // keep two open boxes at the foot, and the deck loaded
    const openAtFoot = I.boxes.filter((b) => !b.carried && !b.onLift && !b.disposed && b.lights > 0 && b.mesh.position.distanceTo(foot) < 3.2);
    const deckWants = L && L.height < 0.3 && !L.box && L.pos.distanceTo(foot) < (fitter ? 12 : 8);
    if (deckWants && openAtFoot.length) {
      W.status = `feeding ${col.label}`;
      const b = openAtFoot[0];
      if (walk(b.mesh.position, 1.0)) { W.carry = b; b.carried = true; }
      return;
    }
    if (pallet && pallet.boxes > 0 && (openAtFoot.length < 2 || deckWants) && this.inHall(pallet.mesh)) {
      W.status = `feeding ${col.label}`;
      if (walk(pallet.mesh.position, 1.4)) { const b = I.spawnBoxFor(pallet); W.carry = b; b.carried = true; }
      return;
    }
    if (this.doRubbishFloor(W, dt, scale, foot, 6.0, false)) return;
    W.status = `feeding ${col.label}`;
    this.walkVia(W, foot.clone().add(new THREE.Vector3(1.4, 0, 1.2)), dt, scale, 0.6);
  }

  // the boards another worker's machine is waiting on: one sheet a trip, laid at the cell that puts the
  // blocked wheel (and the one beside it) on ply. True while this is the job in hand
  layAhead(W, fitter, dt, scale) {
    const L = fitter.lift, WD = this.world;
    if (!WD.protectedAt) return false;                          // an older world with no boards in it
    if (W.jack && W.jack.carrying) return false;                // a pallet in the air comes down first
    if (W.carry && W.carry.type !== 'sheet') return false;      // hands already full of something else
    if (!W.carry && !L.needBoards) return false;
    if (W.jack) this.dropJack(W);
    W.status = `laying boards to ${fitter.assign.target}`;
    if (!W.carry) { this.fetchSheet(W, dt, scale); return true; }
    // where the machine is actually steering this frame, so the boards go down across the way it
    // is really about to travel
    const from = L.needBoards || worldToHall(L.pos);
    const spot = nextBoardSpot(WD, from, L, L.goal || L.target || L.pos);
    // (Claude, 2026-09-07) NOWHERE TO PUT IT. The last metre to a column cannot always be boarded:
    // the cell that would carry the wheels lies through the shaft, and the grid has no other. The
    // feeder does not stand there holding a board all night -- it takes it back to a stack, and
    // the fitter parks the machine where it stands and gets on with the lights
    if (!spot) {
      L.noSpot = (L.noSpot || 0) + dt;
      if (L.noSpot > 5) this.putSheetBack(W, dt, scale);
      return true;
    }
    L.noSpot = 0;
    if (this.walkVia(W, hallToWorld(spot.u, spot.d, WD.floorY), dt, scale, 1.8)) {
      laySheet(WD, spot.u, spot.d, spot.along);
      if (W.carry.mesh) W.carry.mesh.removeFromParent();
      W.carry = null; W.boards++; L.needBoards = null;
    }
    return true;
  }

  // one board off the nearest pallet of ply that still has some
  fetchSheet(W, dt, scale) {
    const st = this.nearestStack(W.pos);
    if (!st) { this.sayOnce('noply', 'Out of boards: the stacks are empty'); W.idle(dt); return false; }
    // stand at the stack's aisle side, not on top of it: its own plan circles hold a walker about
    // 1.6 m off the middle of it, which a reach measured to the centre never resolves
    const h = worldToHall(st.mesh.position);
    const spot = hallToWorld(h.u, h.d + (h.d < 7.5 ? 1.3 : -1.3), this.world.floorY);
    if (this.walkVia(W, spot, dt, scale, 0.9)) {
      st.sheets--;
      if (this.items.updateStackPile) this.items.updateStackPile(st);
      const mesh = this.items.makeSheetMesh();
      this.scene.add(mesh);
      W.carry = { type: 'sheet', mesh, carried: true };
      this.said.delete('noply');
      return true;
    }
    return false;
  }
  // the board in the hands goes back on a pallet of ply that has room
  putSheetBack(W, dt, scale) {
    const st = this.nearestStack(W.pos) || (this.items.stacks || [])[0];
    if (!st) return;
    const h = worldToHall(st.mesh.position);
    if (this.walkVia(W, hallToWorld(h.u, h.d + (h.d < 7.5 ? 1.3 : -1.3), this.world.floorY), dt, scale, 0.9)) {
      if (W.carry.mesh) W.carry.mesh.removeFromParent();
      W.carry = null;
      if (this.items.returnSheet) this.items.returnSheet(W.pos);
    }
  }

  // ---- 4. the BOARDS worker: the protection path out to a column, or the whole hall ----
  // (a) the SPINE runs up the middle of the hall on d 7.5 from the door line to the column, one
  // 2.4 x 1.2 board across the way you drive every 1.2 m. (b) the PATCH is every grid cell within
  // 2.6 m of the column's foot that the shaft does not stand in, covered with boards that butt on
  // to the spine. Nearest the doors first, so the road is continuous as it grows
  boardPlan(target) {
    const G = SHEET.grid, U0 = HALL.doorU, out = [];
    const cols = target === WHOLE_HALL ? this.world.columns.slice() : [this.columnOf(target)].filter(Boolean);
    if (!cols.length) return out;
    cols.sort((a, b) => worldToHall(b.pos).u - worldToHall(a.pos).u);   // nearest the doors first
    const far = Math.min(...cols.map((c) => worldToHall(c.pos).u));
    const clash = (s) => out.some((o) => { const a = sheetRect(s), b = sheetRect(o); return Math.abs(s.u - o.u) < a.hu + b.hu - 0.02 && Math.abs(s.d - o.d) < a.hd + b.hd - 0.02; });
    for (let k = 0; k < 40; k++) {
      const u = U0 - G * (k + 0.5);
      if (u < far - 0.6) break;
      const s = { u, d: HALL.doorD, along: 'd' };
      if (this.staticOk(s) && !clash(s)) out.push(s);
    }
    for (const col of cols) for (const s of this.patch(col)) if (this.staticOk(s) && !clash(s)) out.push(s);
    return out;
  }

  // a board may stand here whatever else is on the floor today: inside the hall and clear of every
  // column shaft. Pallets, boxes and bags come and go, so they are checked when it is laid, not now
  staticOk(s) {
    const r = sheetRect(s);
    if (r.u0 < -0.001 || r.u1 > HALL.doorU + 0.001 || r.d0 < -0.001 || r.d1 > HALL.depth + 0.001) return false;
    for (const c of this.world.columns) {
      const h = worldToHall(c.pos);
      const qu = Math.max(r.u0, Math.min(h.u, r.u1)), qd = Math.max(r.d0, Math.min(h.d, r.d1));
      if (Math.hypot(h.u - qu, h.d - qd) < 0.6) return false;
    }
    return true;
  }

  patch(col) {
    const G = SHEET.grid, U0 = HALL.doorU, h = worldToHall(col.pos), want = [], out = [];
    for (let k = 0; k < 40; k++) {
      const cu = U0 - G * (k + 0.5);
      if (Math.abs(cu - h.u) > PATCH_R + G) continue;
      for (let m = 0; m < 12; m++) {
        const cd = 0.3 + G * (m + 0.5);
        if (Math.hypot(cu - h.u, cd - h.d) > PATCH_R) continue;
        // the shaft: a cell it stands in is left out, because a board there would lie through it
        if (Math.abs(cu - h.u) < G * 0.5 + 0.6 && Math.abs(cd - h.d) < G * 0.5 + 0.6) continue;
        want.push({ u: cu, d: cd });
      }
    }
    const key = (c) => c.u.toFixed(2) + ',' + c.d.toFixed(2);
    const done = new Set();
    // the cells nearest the middle of the hall first: those are the ones that join the spine
    want.sort((a, b) => Math.abs(a.d - HALL.doorD) - Math.abs(b.d - HALL.doorD) || b.u - a.u);
    for (const c of want) {
      if (done.has(key(c))) continue;
      let best = null, bn = -1;
      for (const along of ['d', 'u']) for (const s of sheetCells(c.u, c.d, along)) {
        if (!this.staticOk(s)) continue;
        const r = sheetRect(s);
        const cells = want.filter((q) => q.u > r.u0 && q.u < r.u1 && q.d > r.d0 && q.d < r.d1);
        if (!cells.some((q) => key(q) === key(c))) continue;
        const n = cells.length * 2 - cells.filter((q) => done.has(key(q))).length * 3 + (along === 'd' ? 0.5 : 0);
        if (n > bn) { bn = n; best = { s, cells }; }
      }
      if (!best) continue;
      out.push(best.s);
      for (const q of best.cells) done.add(key(q));
    }
    return out;
  }

  // a planned spot counts as done when its middle is on ply, or when somebody else's board is
  // already lying across it (the player's own path, or a spine laid for another column)
  covered(s) {
    for (const x of this.world.sheets) if (sheetHolds(x, s)) return true;
    return sheetSpotWhy(this.world, s.u, s.d, s.along) === 'sheet';
  }

  doBoards(W, dt, scale) {
    const target = W.assign.target;
    if (W.lift && !this.parkLift(W, dt, scale)) return;
    if (W.jack) this.dropJack(W);
    if (W.carry && W.carry.type !== 'sheet') { this.putDown(W, W.pos.clone()); return; }
    if (W.planFor !== target) { W.plan = this.boardPlan(target); W.planFor = target; }
    const missing = W.plan.filter((s) => !this.covered(s));
    const name = target === WHOLE_HALL ? 'the hall' : target;
    if (!missing.length) {
      if (W.carry) { this.putSheetBack(W, dt, scale); W.status = `laying boards to ${name} (0 to go)`; return; }
      this.finish(W, `${W.name}: boards down to ${name}`);
      return;
    }
    W.status = `laying boards to ${name} (${missing.length} to go)`;
    if (!W.carry) { this.fetchSheet(W, dt, scale); return; }
    // the first missing spot that may actually be laid today; a spot with a pallet standing on it
    // is skipped and comes round again when the pallet moves
    const spot = missing.find((s) => !sheetSpotWhy(this.world, s.u, s.d, s.along));
    // (Claude, 2026-09-07) every spot that is left is blocked by something that is not moving --
    // the column's own pallet, most often. A worker does not stand there with a board for the rest
    // of the night: after twenty seconds those spots come off the plan and the job is finished
    if (!spot) {
      W.blockedFor = (W.blockedFor || 0) + dt;
      if (W.blockedFor > 20) { W.plan = W.plan.filter((s) => !missing.includes(s)); W.blockedFor = 0; }
      W.idle(dt);
      return;
    }
    W.blockedFor = 0;
    if (this.walkVia(W, hallToWorld(spot.u, spot.d, this.world.floorY), dt, scale, 1.8)) {
      laySheet(this.world, spot.u, spot.d, spot.along);
      if (W.carry.mesh) W.carry.mesh.removeFromParent();
      W.carry = null; W.boards++;
    }
  }

  // ---- 5. bring the pallets in ----
  doPallets(W, dt, scale) {
    const I = this.items;
    if (W.lift && !this.parkLift(W, dt, scale)) return;
    if (W.carry) { this.putDown(W, W.pos.clone()); return; }
    if (W.jack && W.jack.carrying) {
      const p = W.jack.carrying, col = this.columnOf(p.column), foot = col ? footSpot(col) : p.home;
      W.status = `bringing the ${p.column} pallet in`;
      if (this.walkVia(W, foot, dt, scale, 1.0)) { p.mesh.position.copy(foot); p.mesh.rotation.y = 0; W.jack.carrying = null; }
      return;
    }
    // nearest the doors first, skipping the columns that are finished and the pallets already in
    const jobs = I.pallets.filter((p) => p.boxes > 0 && !this.inHall(p.mesh) && !this.columnDone(p.column))
      .sort((a, b) => worldToHall(this.columnOf(b.column).pos).u - worldToHall(this.columnOf(a.column).pos).u);
    if (!jobs.length) { if (W.jack) { W.status = 'putting the jack back'; if (this.walkVia(W, this.jackHome(W.jack), dt, scale, 1.0)) this.dropJack(W); return; } this.finish(W, `${W.name}: the pallets are in`); return; }
    const p = jobs[0];
    W.status = `bringing the ${p.column} pallet in`;
    if (!W.jack) { this.fetchJack(W, dt, scale); return; }
    if (this.walkVia(W, p.mesh.position, dt, scale, 1.5)) W.jack.carrying = p;
  }

  // ---- 6. rubbish: wrap into bags, full bags to the skip ----
  doRubbish(W, dt, scale) {
    if (W.lift && !this.parkLift(W, dt, scale)) return;
    if (W.jack) this.dropJack(W);
    if (this.doRubbishHands(W, dt, scale)) return;
    if (this.doRubbishFloor(W, dt, scale, null, 0)) return;
    // nothing to pick up: wait in the middle of the hall, well clear of the machines
    W.status = 'running rubbish';
    this.walkVia(W, hallToWorld(40, 9.6, this.world.floorY), dt, scale, 1.2);
  }

  // what is already in the hands: a bag to the skip, a wrap into a bag
  doRubbishHands(W, dt, scale) {
    const I = this.items;
    if (!W.carry) return false;
    if (W.carry.type === 'bag') {
      if (W.carry.full) {
        W.status = 'running rubbish';
        if (this.walkVia(W, this.world.skip, dt, scale, 2.6)) { W.carry.disposed = true; W.carry.mesh.removeFromParent(); W.carry = null; }
      } else {
        // an empty bag is being carried into the hall for the wrap to go in
        W.status = 'bagging wrap';
        const wrap = I.wraps.find((w) => !w.bagged && !w.carried && this.inHall(w.mesh));
        const to = wrap ? wrap.mesh.position : hallToWorld(40, 9.6, this.world.floorY);
        if (this.walkVia(W, to, dt, scale, 1.6)) this.putDown(W, W.pos.clone());
      }
      return true;
    }
    if (W.carry.type === 'wrap') {
      W.status = 'bagging wrap';
      const bag = I.bags.find((b) => !b.full && !b.disposed && !b.carried && this.inHall(b.mesh))
        || I.bags.find((b) => !b.full && !b.disposed && !b.carried);
      if (!bag) { this.putDown(W, W.pos.clone()); return true; }
      if (this.walkVia(W, bag.mesh.position, dt, scale, 1.2)) {
        bag.wraps++; W.carry.bagged = true; W.carry.mesh.removeFromParent(); W.carry = null;
        if (bag.wraps >= 8) { bag.full = true; bag.mesh.material.color.setHex(0x41523d); }
      }
      return true;
    }
    return false;
  }

  // what is on the floor: a full bag to run, a loose wrap to bag, an empty bag to bring in
  doRubbishFloor(W, dt, scale, near, radius, fetchBag = true) {
    const I = this.items;
    const inRange = (m) => (!near || m.position.distanceTo(near) < radius) && this.inHall(m);
    const fullBag = I.bags.find((b) => b.full && !b.disposed && !b.carried && inRange(b.mesh));
    if (fullBag) { W.status = 'running rubbish'; if (this.walkVia(W, fullBag.mesh.position, dt, scale, 1.2)) { W.carry = fullBag; fullBag.carried = true; } return true; }
    const wrap = I.wraps.find((w) => !w.bagged && !w.carried && inRange(w.mesh));
    if (!wrap) return false;
    const open = I.bags.find((b) => !b.full && !b.disposed && !b.carried && this.inHall(b.mesh));
    if (!open) {
      // no bag open in the hall: fetch an empty one from the corridor first. A feeder does not
      // leave its column for that -- it is a job for whoever is on the rubbish
      if (!fetchBag) return false;
      const spare = I.bags.find((b) => !b.full && !b.disposed && !b.carried);
      if (spare) { W.status = 'bagging wrap'; if (this.walkVia(W, spare.mesh.position, dt, scale, 1.2)) { W.carry = spare; spare.carried = true; } return true; }
      return false;
    }
    W.status = 'bagging wrap';
    if (this.walkVia(W, wrap.mesh.position, dt, scale, 1.0)) { W.carry = wrap; wrap.carried = true; }
    return true;
  }

  // ---- 7. help me: whichever column the player's lift is nearest ----
  doHelp(W, dt, scale, player) {
    const I = this.items, L = this.playerLift;
    if (W.lift && !this.parkLift(W, dt, scale)) return;
    const col = pickColumn(this.install, this.world, L.pos, null);
    if (!col) { W.status = 'helping you'; this.walkVia(W, hallToWorld(46, 7.5, this.world.floorY), dt, scale, 1.0); return; }
    const foot = footSpot(col), pallet = I.pallets.find((p) => p.column === col.label);
    const walk = (to, reach) => this.walkVia(W, to, dt, scale, reach);
    W.status = 'helping you';
    if (W.jack && W.jack.carrying) {
      if (walk(foot, 1.0)) { const p = W.jack.carrying; p.mesh.position.copy(foot); p.mesh.rotation.y = 0; W.jack.carrying = null; this.dropJack(W); }
      return;
    }
    if (pallet && pallet.boxes > 0 && !this.inHall(pallet.mesh) && !W.carry) {
      if (!W.jack) { this.fetchJack(W, dt, scale); return; }
      if (walk(pallet.mesh.position, 1.5)) W.jack.carrying = pallet;
      return;
    }
    if (W.jack) this.dropJack(W);
    if (W.carry && (W.carry.type === 'box' || W.carry.type === 'emptyBox')) {
      const deckDown = L.height < 0.3 && !L.box && L.pos.distanceTo(foot) < 8;
      if (W.carry.type === 'box' && deckDown) { if (walk(L.pos, 1.9)) { L.box = W.carry; W.carry.carried = false; W.carry.onLift = true; W.carry.deck = null; W.carry = null; L.refresh(); } return; }
      if (walk(foot, 1.3)) this.putDown(W, foot.clone().add(new THREE.Vector3(0.9, 0, 0.6)));
      return;
    }
    if (this.doRubbishHands(W, dt, scale)) { W.status = 'helping you'; return; }
    const openAtFoot = I.boxes.filter((b) => !b.carried && !b.onLift && !b.disposed && b.lights > 0 && b.mesh.position.distanceTo(foot) < 3.2);
    if (pallet && pallet.boxes > 0 && openAtFoot.length < 2 && !L.box && this.inHall(pallet.mesh)) {
      if (walk(pallet.mesh.position, 1.4)) { const b = I.spawnBoxFor(pallet); W.carry = b; b.carried = true; }
      return;
    }
    if (this.doRubbishFloor(W, dt, scale, null, 0, false)) { W.status = 'helping you'; return; }
    if (openAtFoot.length && L.height < 0.3 && !L.box && L.pos.distanceTo(foot) < 8) {
      if (walk(openAtFoot[0].mesh.position, 1.0)) { W.carry = openAtFoot[0]; openAtFoot[0].carried = true; }
      return;
    }
    walk(foot.clone().add(new THREE.Vector3(-1.2, 0, -1.0)), 0.6);
  }

  // ---- 04:30: everything of the crew's goes back through the doors ----
  packUp(W, dt, scale) {
    W.status = 'packing up';
    // (Claude, 2026-09-07) A MACHINE WITH NOBODY'S NAME ON IT. A fitter reassigned mid-column
    // leaves his lift standing in the hall, free -- and at 04:30 nothing was coming for it, so it
    // stood there past 05:00 and the night's check read `a crew lift`. Whoever is free and
    // empty-handed claims it, walks out to it and takes it home
    if (!W.lift && !W.carry && !(W.jack && W.jack.carrying)) {
      const stray = this.lifts.find((M) => !M.by && this.inHall(M.group));
      if (stray) { stray.by = W; W.lift = stray; W.onDeck = false; W.liftWait = 0; W.liftBest = Infinity; }
    }
    const L = W.lift;
    if (L) {
      // the deck comes down, then the machine drives home along the boards it came in on. If it is
      // somehow off them and blocked for a couple of seconds it rolls anyway: nothing of the
      // crew's is left standing in the hall at 05:00
      L.height = Math.max(0, L.height - dt * 0.5 * scale);
      L.refresh();
      const home = L.pos.distanceTo(L.home) <= 0.4;
      // he has to be ON it to take it home: nobody drives a machine from the floor beside it, and
      // a member who is not aboard is never moved to it (the skeptic's D1)
      if (!W.onDeck) {
        if (home) { this.releaseLift(W, L); return; }
        if (L.height > 0.01) { W.idle(dt); return; }
        if (this.walkVia(W, L.offboardWorld(), dt, scale, 1.3)) { this.climbOn(W, L); W.liftWait = 0; return; }
        // he is not getting any nearer to it: rather than leave a machine standing in the hall
        // past 05:00, it goes home on its own after twenty seconds of that (the pack-up's `force`
        // roll is the same last resort)
        const gap = W.pos.distanceTo(L.pos);
        if (gap < (W.liftBest === undefined ? Infinity : W.liftBest) - 0.5) { W.liftBest = gap; W.liftWait = 0; }
        else W.liftWait = (W.liftWait || 0) + dt;
        if (W.liftWait > 20) {
          const goal = this.travelGoal(L, L.home);
          if (!L.roll(goal, 1.5 * scale * dt, this.world, this.collide)) L.roll(goal, 1.5 * scale * dt, this.world, this.collide, true);
          L.refresh();
        }
        return;
      }
      if (L.height <= 0.01 && !home) {
        const goal = this.travelGoal(L, L.home);
        if (L.roll(goal, 1.5 * scale * dt, this.world, this.collide)) W.stall = 0;
        else { W.stall += dt; if (W.stall > 2) L.roll(goal, 1.5 * scale * dt, this.world, this.collide, true); }
      } else if (L.height <= 0.01) { this.climbOff(W, L); return; }
      L.refresh();
      this.rideDeck(W);
      return;
    }
    if (W.jack && W.jack.carrying) {
      const p = W.jack.carrying;
      if (this.walkVia(W, p.home, dt, scale, 1.5)) { this.setDown(p, p.home); W.jack.carrying = null; }
      return;
    }
    if (W.carry) {
      if (W.carry.type === 'sheet') { this.putSheetBack(W, dt, scale); return; }
      if (W.carry.type === 'bag' && W.carry.full) { if (this.walkVia(W, this.world.skip, dt, scale, 2.6)) { W.carry.disposed = true; W.carry.mesh.removeFromParent(); W.carry = null; } return; }
      if (this.walkVia(W, this.corridorSpot(W.index), dt, scale, 1.0)) this.putDown(W, W.pos.clone());
      return;
    }
    // (Lloyd's brief, "jacks and pallets back, stacks back if a jack is free") EVERYTHING THE CREW
    // WHEELED IN GOES OUT AGAIN. The pack-up used to walk home only a pallet that was already in
    // the air, so twelve pallets stood at twelve column feet all night and the night's clean-up
    // read "pallets" every time (the skeptic's D2). Whoever is free claims the nearest one, takes
    // a jack to it and runs it back to its storage spot
    const load = this.strayLoad(W);
    if (load) {
      W.status = load.column ? `taking the ${load.column} pallet back` : 'taking the ply back';
      // every jack is out with somebody else: he lets the claim go rather than stand on it, and
      // walks out. Whoever brings a jack back picks this one up on their next trip
      if (!W.jack) { if (!this.allJacks().some((j) => (!j.by || j.by === W.name) && !j.held)) { load.by = null; W.status = 'packing up'; this.walkVia(W, this.corridorSpot(W.index), dt, scale, 0.8); return; } this.fetchJack(W, dt, scale); return; }
      if (this.walkVia(W, load.mesh.position, dt, scale, 1.5)) W.jack.carrying = load;
      return;
    }
    if (W.jack) { if (this.walkVia(W, this.jackHome(W.jack), dt, scale, 1.0)) this.dropJack(W); return; }
    // (Claude, 2026-09-07) A JACK LEFT AT A COLUMN. A feeder sets its jack down at the foot when
    // the pallet is in, which is right; but nothing of the crew's may be in the hall at 05:00, so
    // at pack-up whoever is free walks the strays out. The claim stops two of them fetching one
    const stray = this.allJacks().find((j) => j.by === W.name && !j.held)
      || this.allJacks().find((j) => !j.by && !j.held && this.inHall(j.mesh));
    if (stray) { stray.by = W.name; if (this.walkVia(W, stray.mesh.position, dt, scale, 1.0)) { W.jack = stray; stray.held = true; } return; }
    this.walkVia(W, this.corridorSpot(W.index), dt, scale, 0.8);
  }

  // a pallet is set down square on the floor; a stack of ply keeps the turn it was built with
  setDown(p, at) {
    p.mesh.position.copy(at);
    if (p.quat) p.mesh.quaternion.copy(p.quat); else p.mesh.rotation.y = 0;
    p.by = null;
  }
  // is anybody's jack already under this one?
  onAJack(p) { return this.allJacks().some((j) => j.carrying === p); }
  // the nearest pallet of lights or of ply still standing in the hall at pack-up, claimed by name
  // so two of them never walk at the same one
  strayLoad(W) {
    const all = (this.items.pallets || []).concat(this.items.stacks || []);
    const mine = all.find((p) => p.by === W.name);
    if (mine) { if (this.inHall(mine.mesh) && !this.onAJack(mine)) return mine; mine.by = null; }
    let best = null, bd = Infinity;
    for (const p of all) {
      if (p.by || !this.inHall(p.mesh) || this.onAJack(p)) continue;
      const d = p.mesh.position.distanceTo(W.pos);
      if (d < bd) { bd = d; best = p; }
    }
    if (best) best.by = W.name;
    return best;
  }

  // the night's end: everything of the crew's back in the corridor. The ASSIGNMENTS stay: you
  // told them what to do and tomorrow they carry on with it
  resetForNight() {
    for (const [i, W] of this.members.entries()) {
      if (W.carry) {
        // a board still in the hands goes back on the nearest stack WITH ROOM, never a 31st sheet
        if (W.carry.type === 'sheet' && this.items.returnSheet) this.items.returnSheet(W.pos);
        if (W.carry.mesh) W.carry.mesh.removeFromParent();
        if (W.carry.carried !== undefined) W.carry.carried = false;
        W.carry = null;
      }
      if (W.jack) this.dropJack(W); else this.unclaimJacks(W);
      this.unclaimLoads(W);
      W.climb = null; W.jackWait = 0; W.skipJacks = null; W.blockedFor = 0; W.liftWait = 0; W.liftBest = Infinity;
      W.lift = null; W.onDeck = false; W.fetching = false; W.helpLift = null; W.offLift = null; W.run = null; W.timer = 0; W.stall = 0; W.worked = false;
      W.plan = null; W.planFor = null;
      W.status = 'standing by';
      W.place(this.corridorSpot(i));
    }
    for (const [i, L] of this.lifts.entries()) {
      L.height = 0; L.pos.copy(L.home); L.yaw = 0; L.by = null; L.box = null;
      L.needBoards = null; L.noSpot = 0; L.parked = false; L.parkedAt = null; L.stallToast = false; L.stuckCol = null;
      L.refresh();
    }
    for (const j of this.jacks) { j.held = false; j.by = null; j.carrying = null; j.mesh.position.copy(this.jackHome(j)); }
    if (this.items.jack && this.items.jack.by) { this.items.jack.by = null; this.items.jack.held = false; }
    this.said.clear();
  }

  // for the clean-up check: any crew gear left in the hall
  leftInHall() {
    const out = [];
    for (const L of this.lifts) if (this.inHall(L.group)) out.push('a crew lift');
    for (const j of this.jacks) if (this.inHall(j.mesh)) out.push('a crew jack');
    return out;
  }
}
