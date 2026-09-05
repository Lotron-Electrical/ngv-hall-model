import * as THREE from 'three';
import { hallToWorld, worldToHall, HALL } from './world.js';

// (Lloyd, 2026-09-04: "the scissor lift should drive more like a real scissor lift", and
// "once we're on the scissor lift, we should walk up to the control panel and then choose to
// drive or not") Being ABOARD and DRIVING are two different things now. Aboard, you walk the
// deck like a floor: the box, a light you put down and the rails all ride with you. At the
// control box (the +x end) ACTION takes the controls; only then does the left stick drive the
// machine and UP/DOWN move the deck. ACTION again lets go, and you are back to walking the deck
// with your hands free for lights. The machine itself is a slab scissor: it steers with its front
// wheels (no turning on the spot, like a car), ramps up and brakes when you let go, runs at
// walking pace stowed and creeps once the deck is up.
export class Lift {
  constructor(scene, floorY) {
    this.floorY = floorY;
    this.pos = hallToWorld(63.6, 6.6, floorY);   // parked at the aisle's end, clear of both pallet rows
    this.yaw = 0;                                 // the chassis heading; forward is local +x
    // (2026-09-04) the stowed deck sits 1.25 m up, like a real 26-footer: the folded scissor
    // stack needs the room under it, and the two step treads at the back need the rise
    this.deckY = Lift.DECK_Y;
    this.anim = null;                             // the boarding / climbing-down timeline while it runs
    this.height = 0;
    this.aboard = false;
    this.driving = false;
    this.deckLocal = new THREE.Vector2(-0.7, 0);  // where you stand on the deck (chassis coordinates)
    this.speed = 0;                               // m/s along the heading, negative in reverse
    this.steer = 0;                               // front-wheel angle, radians
    // (Lloyd, 2026-09-05: "a fast and slow mode for the scissor") slow is 40 % of the drive and
    // half the deck's rate, for lining up on a column. Q or the button toggles it
    this.mode = 'fast';
    this.vmax = 0;                                // the drive limit this frame, for the wheel indicator
    this.atDoorway = false;                       // within the doorway's reach (the crouch, the deck guard)
    this.box = null;
    this.group = new THREE.Group();
    this.group.position.copy(this.pos);
    scene.add(this.group);
    this.build();
  }

  static DECK = { x: 1.1, z: 0.45 };              // the walkable half-extents of the deck
  static PANEL = new THREE.Vector2(0.72, 0.22);   // where you stand to drive, facing the box on the corner
  static DOOR = new THREE.Vector2(-0.8, 0);       // where you step on and off (the back end)
  static DECK_Y = 1.25;                           // the deck plate's centre above the floor, stowed
  static LADDER = { x: -1.27, rungs: [0.28, 0.55, 0.82, 1.09] };   // the vertical ladder flush on the back of the chassis (Genie / JLG photos)
  static EYE = 1.68;                              // standing eye height
  static GATE_OPEN = Math.PI / 2;                 // the door fully open, lying along the deck

  // (Lloyd, 2026-09-04: Genie reference photos) a Genie-style slab scissor: blue chassis on four
  // wheels, a grey stack of crossed arms that flattens as it rises, a blue deck with a full rail
  // cage and a control box at one end
  build() {
    const blue = new THREE.MeshStandardMaterial({ color: 0x1b6fd8, roughness: 0.45, metalness: 0.2 });
    const grey = new THREE.MeshStandardMaterial({ color: 0x8d949c, roughness: 0.55, metalness: 0.3 });
    const dark = new THREE.MeshStandardMaterial({ color: 0x1d2024, roughness: 0.8 });
    const rubber = new THREE.MeshStandardMaterial({ color: 0x2a2a2a, roughness: 0.95 });
    this.base = new THREE.Group();
    const chassis = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.5, 1.15), blue); chassis.position.y = 0.45; this.base.add(chassis);
    // each wheel hangs in a hub: the hub turns for steering (front pair only), the wheel spins on
    // its axle inside it. The cylinder is pre-rotated so its axle is the hub's z
    this.wheels = [];
    for (const x of [-0.85, 0.85]) for (const z of [-0.62, 0.62]) {
      const hub = new THREE.Group(); hub.position.set(x, 0.22, z);
      const geo = new THREE.CylinderGeometry(0.22, 0.22, 0.16, 14); geo.rotateX(Math.PI / 2);
      const w = new THREE.Mesh(geo, rubber); hub.add(w); this.base.add(hub);
      this.wheels.push({ hub, w, front: x > 0 });
    }
    const tray = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.06, 0.95), dark); tray.position.y = 0.73; this.base.add(tray);
    this.scissor = new THREE.Group();
    this.arms = [];
    this.N = 5;                         // five crossed pairs, like the GS-2646 stack
    for (let i = 0; i < this.N; i++) for (const z of [-0.4, 0.4]) for (const dir of [1, -1]) {
      const arm = new THREE.Mesh(new THREE.BoxGeometry(0.08, 1.28, 0.08), grey);
      this.scissor.add(arm); this.arms.push({ arm, i, z, dir });
    }
    // (Lloyd, 2026-09-04, Genie + JLG photos: "see the steps on the back?") the steps are a
    // VERTICAL ladder flush on the back face of the chassis, rungs between the wheels, two
    // stiles, nothing sticking out behind the machine
    const LD = Lift.LADDER;
    for (const z of [-0.26, 0.26]) { const st = new THREE.Mesh(new THREE.BoxGeometry(0.05, 1.0, 0.05), grey); st.position.set(LD.x, 0.68, z); this.base.add(st); }
    for (const y of LD.rungs) { const r = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.04, 0.52), grey); r.position.set(LD.x, y, 0); this.base.add(r); }
    this.deck = new THREE.Group();
    const plate = new THREE.Mesh(new THREE.BoxGeometry(2.5, 0.14, 1.2), blue); plate.position.y = 0; this.deck.add(plate);
    const rail = (sx, sy, sz, x, y, z) => { const m = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), blue); m.position.set(x, y, z); this.deck.add(m); };
    // (Lloyd, 2026-09-04: "a kick plate that goes all around, except for the door because the
    // door has its own") the cage: top rail 1.1, mid rail 0.55 and a 0.12 kick plate on the
    // plate's edge, along both sides and the front end; the back end is two short panels either
    // side of the DOOR, which is the centre third (z -0.2..0.2) and carries its own three
    const kick = (sx, sz, x, z) => rail(sx, 0.12, sz, x, 0.13, z);
    for (const z of [-0.58, 0.58]) { rail(2.5, 0.05, 0.05, 0, 1.1, z); rail(2.5, 0.04, 0.04, 0, 0.55, z); kick(2.5, 0.03, 0, z); }
    rail(0.05, 0.05, 1.2, 1.23, 1.1, 0); rail(0.04, 0.04, 1.2, 1.23, 0.55, 0); kick(0.03, 1.13, 1.23, 0);   // front end, the plate butts the side plates
    for (const z of [-0.395, 0.395]) { rail(0.05, 0.05, 0.34, -1.23, 1.1, z); rail(0.04, 0.04, 0.34, -1.23, 0.55, z); kick(0.03, 0.34, -1.23, z); }   // back panels, post to door post
    for (const z of [-0.2, 0.2]) rail(0.05, 1.1, 0.05, -1.23, 0.55, z);   // the door posts
    // (Lloyd, 2026-09-04: "make that back section just a door", "the door will be in the centre
    // 1/3rd wide") a full-height door hinged on the z -0.2 post, swinging INTO the deck
    // (rotation.y, GATE_OPEN = a right angle: it then lies along the deck at z -0.2, clear of
    // everything). Its own top bar, mid bar and kick plate; stiles 5 mm clear of both posts
    this.gate = new THREE.Group(); this.gate.position.set(-1.23, 0, -0.2); this.deck.add(this.gate);
    const door = (sx, sy, sz, x, y, z) => { const m = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), blue); m.position.set(x, y, z); this.gate.add(m); };
    for (const z of [0.05, 0.35]) door(0.04, 0.97, 0.04, 0, 0.615, z);
    door(0.04, 0.05, 0.34, 0, 1.1, 0.2); door(0.04, 0.04, 0.34, 0, 0.55, 0.2); door(0.03, 0.12, 0.34, 0, 0.13, 0.2);
    for (const x of [-1.23, -0.41, 0.41, 1.23]) for (const z of [-0.58, 0.58]) rail(0.05, 1.1, 0.05, x, 0.55, z);
    for (const z of [-0.58, 0.58]) rail(0.05, 1.1, 0.05, 1.23, 0.55, z);
    // (Lloyd, 2026-09-04, Genie photo) the control box hangs on the INSIDE corner of the rail at
    // the front end: a blue hood hooked over the top rail, open towards the deck, the dark
    // console with its joystick and red stop button tilted up at whoever stands at the corner
    this.panel = new THREE.Group(); this.panel.position.set(1.12, 0.96, 0.42); this.deck.add(this.panel);
    const sheet = (sx, sy, sz, x, y, z, m = blue) => { const q = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), m); q.position.set(x, y, z); this.panel.add(q); return q; };
    sheet(0.02, 0.3, 0.24, 0.09, 0.05, 0);                 // back plate, against the end rail
    sheet(0.2, 0.02, 0.24, 0, 0.19, 0);                    // top
    sheet(0.2, 0.3, 0.02, 0, 0.05, -0.12); sheet(0.2, 0.3, 0.02, 0, 0.05, 0.12);   // sides
    sheet(0.08, 0.02, 0.24, 0.14, 0.19, 0); sheet(0.02, 0.08, 0.24, 0.18, 0.16, 0);   // the hook over the rail
    const con = sheet(0.16, 0.06, 0.2, -0.02, -0.06, 0, dark); con.rotation.z = 0.5;    // console, face up towards the deck
    const stick = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.016, 0.14, 8), dark); stick.position.set(-0.06, 0.02, 0.03); stick.rotation.z = 0.5; this.panel.add(stick);
    const knob = new THREE.Mesh(new THREE.SphereGeometry(0.022, 8, 8), dark); knob.position.set(-0.095, 0.085, 0.03); this.panel.add(knob);
    const stop = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.02, 10), new THREE.MeshStandardMaterial({ color: 0xd8241c, roughness: 0.5 })); stop.position.set(-0.04, -0.005, -0.055); stop.rotation.z = 0.5; this.panel.add(stop);
    this.rails = new THREE.Group();   // kept for callers that reference it
    this.group.add(this.base, this.scissor, this.deck, this.rails);
    this.refresh();
  }

  refresh() {
    this.group.position.copy(this.pos);
    this.group.rotation.y = this.yaw;
    const top = this.deckY + this.height;          // the deck plate's centre
    this.deck.position.y = top;
    // the stack fills the space between the chassis tray (0.81) and the underside of the deck
    // (top - 0.12): each of the N pairs takes an equal share, and the arm angle follows from its
    // fixed length. (2026-09-04) the old floor of 0.2 m on the span put the folded arms THROUGH
    // the deck plate: the stack now stays inside its slot however low the deck sits
    const span = Math.max(0.05, top - 0.12 - 0.81), h = span / this.N, L = 1.28;
    const ang = Math.asin(Math.min(1, h / L));      // from the horizontal
    for (const a of this.arms) {
      a.arm.position.set(0, 0.81 + h * (a.i + 0.5), a.z);
      a.arm.rotation.z = a.dir * (Math.PI / 2 - ang);
    }
    for (const W of this.wheels) W.hub.rotation.y = W.front ? -this.steer : 0;
    this.group.updateMatrixWorld(true);
    // (2026-09-05) a box with deck coordinates rides where it was set down; the old centre placement is the fallback
    if (this.box) { if (this.box.deck) { const p = this.deckPoint(this.box.deck.x, this.box.deck.y); this.box.mesh.position.set(p.x, this.floorY + this.deckY + this.height + 0.07 + 0.17, p.z); this.box.mesh.rotation.y = (this.box.deckYaw || 0) + this.yaw; } else this.box.mesh.position.copy(this.deckWorld()).add(new THREE.Vector3(0, 0.18, 0)); }
  }

  deckWorld() {
    return this.group.localToWorld(new THREE.Vector3(0, this.deckY + this.height + 0.1, 0));
  }

  // a point on the deck, chassis coordinates -> world
  deckPoint(x, z) {
    return this.group.localToWorld(new THREE.Vector3(x, this.deckY + this.height, z));
  }

  // a world point -> deck coordinates (x along the chassis, z across), or null when it is not on
  // the deck
  toDeck(p) {
    const q = this.group.worldToLocal(p.clone());
    return new THREE.Vector2(q.x, q.z);
  }

  contains(p) {
    const q = p.clone();
    this.group.worldToLocal(q);
    return Math.abs(q.x) < 1.55 && Math.abs(q.z) < 0.7 && Math.abs(p.y - (this.floorY + this.deckY + this.height)) < 0.9;
  }

  offboardWorld() {
    return this.group.localToWorld(new THREE.Vector3(-2.0, this.deckY + this.height, 0));
  }

  // you stand within reach of the control box (the +x end)
  atPanel() { return this.deckLocal.distanceTo(Lift.PANEL) < 0.75; }
  // you stand at the back, where the steps are
  atDoor() { return this.deckLocal.x < -0.1; }

  // (Lloyd, 2026-09-04: "an animation of climbing up on to the scissor lift") getting on is a
  // climb, not a teleport: walk to the foot of the ladder, up it as the door swings open, step
  // through onto the deck, and the door closes behind you.
  // Getting off runs the same path backwards. Nothing you press does anything until it is over.
  // `instant` is for scripts and tests that just want to be aboard
  board(player, instant = false) {
    this.aboard = true; this.driving = false; this.speed = 0;
    player.onLift = true;
    if (instant) { this.deckLocal.copy(Lift.DOOR); player.eye = Lift.EYE; this.place(player); return; }
    const q = this.group.worldToLocal(player.pos.clone());
    this.startAnim(1, { x: q.x, z: q.z, y: 0 }, player);
  }
  leave(player, instant = false) {
    if (instant) { this.finishLeave(player); return; }
    this.driving = false; this.speed = 0; this.steer = 0;
    this.startAnim(-1, { x: this.deckLocal.x, z: this.deckLocal.y, y: this.deckY }, player);
  }
  finishLeave(player) {
    this.aboard = false; this.driving = false; this.speed = 0; this.steer = 0; this.anim = null;
    player.onLift = false; player.eye = Lift.EYE;
    player.pos.copy(this.offboardWorld()); player.pos.y = this.floorY;
    this.gate.rotation.y = 0;
  }

  // the climb as keyframes in chassis coordinates: x along, y feet height above the floor (the
  // lift's own height is added on top), eye the camera above the feet, gate 0 down .. 1 up.
  // dir 1 climbs aboard, -1 climbs down (the same frames, walked backwards). The first segment
  // walks from wherever you stand to the frame the path begins at
  startAnim(dir, from, player) {
    const D = this.deckY, LD = Lift.LADDER;
    const frames = [
      { x: -2.0, y: 0, eye: Lift.EYE, gate: 0, dt: 0.5 },        // foot of the ladder (offboardWorld)
      { x: LD.x - 0.3, y: 0, eye: Lift.EYE, gate: 0, dt: 1.4 },  // hands on the rungs
      { x: LD.x - 0.3, y: D - 0.3, eye: Lift.EYE, gate: 1, dt: 0.7 },   // up the ladder as the door swings open
      { x: -0.9, y: D, eye: Lift.EYE, gate: 1, dt: 0.6 },        // through the door onto the deck, standing (it is full height)
      { x: Lift.DOOR.x, y: D, eye: Lift.EYE, gate: 0, dt: 0 }     // standing, the gate dropped
    ];
    if (dir < 0) frames.reverse();
    // each frame's dt is the time to reach the NEXT frame; walking backwards the same pairs keep
    // their durations
    if (dir < 0) for (let i = 0; i < frames.length - 1; i++) frames[i].dt = frames[i + 1].dt || 1.2;
    const first = { x: from.x, z: from.z, y: from.y, eye: player.eye, gate: this.gate.rotation.y / Lift.GATE_OPEN, dt: Math.max(0.2, Math.hypot(from.x - frames[0].x, from.z) / 1.5) };
    frames.unshift(first);
    this.anim = { dir, frames, i: 0, t: 0 };
    this.stepAnim(0, player);
  }

  stepAnim(dt, player) {
    const A = this.anim;
    A.t += dt;
    while (A.i < A.frames.length - 1 && A.t >= A.frames[A.i].dt) { A.t -= A.frames[A.i].dt; A.i++; }
    const done = A.i >= A.frames.length - 1;
    const a = A.frames[A.i], b = done ? a : A.frames[A.i + 1];
    const u = done ? 1 : THREE.MathUtils.smoothstep(A.t / a.dt, 0, 1);
    const L = (p, q) => p + (q - p) * u;
    const x = L(a.x, b.x), y = L(a.y, b.y), z = L(a.z || 0, b.z || 0), eye = L(a.eye, b.eye), gate = L(a.gate, b.gate);
    this.deckLocal.set(x, z);
    const p = this.group.localToWorld(new THREE.Vector3(x, y + this.height, z));
    player.pos.set(p.x, this.floorY + y + this.height, p.z);
    player.eye = eye;
    this.gate.rotation.y = Lift.GATE_OPEN * gate;
    // you face along the lift for the climb, whichever way you were looking
    const want = this.yaw - Math.PI / 2;
    const d = Math.atan2(Math.sin(want - player.yaw), Math.cos(want - player.yaw));
    player.yaw += d * Math.min(1, dt * 4);
    if (done) { if (A.dir < 0) this.finishLeave(player); else { this.anim = null; this.deckLocal.copy(Lift.DOOR); player.eye = Lift.EYE; this.place(player); } }
  }
  takeControls(player) { this.driving = true; this.deckLocal.copy(Lift.PANEL); this.place(player); }
  toggleMode() { this.mode = this.mode === 'fast' ? 'slow' : 'fast'; return this.mode; }
  // how far the machine stands from the doorway's wall line, along the hall (metres, signed: negative in the hall)
  doorDist() { return worldToHall(this.pos).u - HALL.doorU; }
  letGo() { this.driving = false; this.speed = 0; }

  place(player) {
    const p = this.deckPoint(this.deckLocal.x, this.deckLocal.y);
    player.pos.set(p.x, this.floorY + this.deckY + this.height, p.z);
  }

  // stick + keys as (forward, strafe) in the player's look frame
  input(player) {
    const forward = (player.keys.has('KeyW') ? 1 : 0) - (player.keys.has('KeyS') ? 1 : 0) - player.move.y;
    const strafe = (player.keys.has('KeyD') ? 1 : 0) - (player.keys.has('KeyA') ? 1 : 0) + player.move.x;
    return { forward: THREE.MathUtils.clamp(forward, -1, 1), strafe: THREE.MathUtils.clamp(strafe, -1, 1) };
  }

  update(dt, player, world, collide) {
    // aboard is set by ACTION (get on / get off), never by walking into the footprint
    if (this.anim) this.stepAnim(dt, player);
    else if (this.aboard && this.driving) this.drive(dt, player, world, collide);
    else if (this.aboard) this.walkDeck(dt, player);
    else if (this.speed) this.speed = 0;
    // (Lloyd, 2026-09-05: "when we are on the scissor and going out the doors, we should duck")
    // the header bar sits 3 m up and a standing eye on the stowed deck is 2.93: within 2.2 m of
    // the doorway anyone aboard crouches to an eye of 0.95 above the deck, and stands again past it
    this.atDoorway = this.aboard && !this.anim && Math.abs(this.doorDist()) < 2.2;
    if (this.aboard && !this.anim) player.eye = THREE.MathUtils.damp(player.eye, this.atDoorway ? 0.95 : Lift.EYE, 7, dt);
    this.refresh();
  }

  // walking the deck: the stick moves you in the look frame, the deck's edge is the rail
  walkDeck(dt, player) {
    const { forward, strafe } = this.input(player);
    const v = new THREE.Vector3(strafe, 0, -forward).clampLength(0, 1).applyAxisAngle(new THREE.Vector3(0, 1, 0), player.yaw - this.yaw);
    this.deckLocal.x = THREE.MathUtils.clamp(this.deckLocal.x + v.x * dt * 1.5 * player.speedScale, -Lift.DECK.x, Lift.DECK.x);
    this.deckLocal.y = THREE.MathUtils.clamp(this.deckLocal.y + v.z * dt * 1.5 * player.speedScale, -Lift.DECK.z, Lift.DECK.z);
    this.place(player);
  }

  // at the controls: forward/back is the drive joystick, left/right the steer, UP/DOWN the deck.
  // Genie GS-2646 figures: 3.5 km/h stowed, 0.8 km/h raised, wheelbase about 1.8 m
  drive(dt, player, world, collide) {
    const scale = player.speedScale, slow = this.mode === 'slow';
    if (player.liftUp) this.height += dt * 0.5 * scale * (slow ? 0.5 : 1);
    if (player.liftDown) this.height -= dt * 0.5 * scale * (slow ? 0.5 : 1);
    this.height = THREE.MathUtils.clamp(this.height, 0, 11.6);

    const { forward, strafe } = this.input(player);
    // the deck up = creep speed: the limit eases in over the first half metre of lift
    const raised = THREE.MathUtils.smoothstep(this.height, 0.3, 0.9);
    const vmax = THREE.MathUtils.lerp(0.97, 0.22, raised) * scale * (slow ? 0.4 : 1);
    this.vmax = vmax;
    const target = forward * vmax;
    // the drive ramps up over about a second and brakes harder than it accelerates when the
    // stick is let go (hydrostatic drive: no coasting)
    const rate = Math.abs(target) > Math.abs(this.speed) ? 0.9 : 1.8;
    this.speed = THREE.MathUtils.damp(this.speed, target, rate * 3, dt);
    if (Math.abs(this.speed) < 0.005 && target === 0) this.speed = 0;
    // the front wheels swing towards the stick over a moment; the machine only turns while it
    // rolls, because that is all steering wheels can do
    const steerMax = 0.6;
    this.steer = THREE.MathUtils.damp(this.steer, -strafe * steerMax, 6, dt);
    const wheelbase = 1.7;
    const dyaw = (this.speed * dt / wheelbase) * Math.tan(this.steer);
    this.yaw += dyaw;
    player.yaw += dyaw;                            // the deck turns under you, and you with it

    const heading = new THREE.Vector3(Math.cos(this.yaw), 0, -Math.sin(this.yaw));
    const before = this.pos.clone();
    if (this.speed === 0) { this.place(player); return; }   // parked is parked: no push, no slide
    this.pos.addScaledVector(heading, this.speed * dt);
    const wanted = this.pos.clone();
    collide(this.pos, 0.9, world, [this, this.box]);
    // pushed back against the travel = bumped into something, and the machine stops; a sideways
    // nudge (sliding along a wall) is not a bump
    // (2026-09-04) head-on means the push points mostly back along the travel; a glancing push
    // off a pallet corner slides the machine along instead of wedging it
    const push = this.pos.clone().sub(wanted);
    if (push.lengthSq() > 1e-6 && push.dot(heading) * Math.sign(this.speed || 1) < -0.6 * push.length()) this.speed = 0;
    // the doorway takes a stowed machine only: with the deck up the rail cage meets the header,
    // so the machine stops at the wall line and the prompt says why (index.html reads blocked)
    { const d0 = worldToHall(before).u - HALL.doorU, d1 = this.doorDist();
      if (this.height > 0.45 && Math.abs(d1) < 1.3 && Math.abs(d1) < Math.abs(d0)) { this.pos.copy(before); this.speed = 0; this.blocked = 'Lower the deck to pass the doorway'; }
      else this.blocked = null; }
    this.travelled = (this.travelled || 0) + this.pos.distanceTo(before);
    for (const W of this.wheels) W.w.rotation.z -= (this.speed * dt) / 0.22;
    this.place(player);
  }
}
