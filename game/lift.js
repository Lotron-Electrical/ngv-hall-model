import * as THREE from 'three';
import { hallToWorld } from './world.js';

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
    this.deckY = 0.85;
    this.height = 0;
    this.aboard = false;
    this.driving = false;
    this.deckLocal = new THREE.Vector2(-0.7, 0);  // where you stand on the deck (chassis coordinates)
    this.speed = 0;                               // m/s along the heading, negative in reverse
    this.steer = 0;                               // front-wheel angle, radians
    this.box = null;
    this.group = new THREE.Group();
    this.group.position.copy(this.pos);
    scene.add(this.group);
    this.build();
  }

  static DECK = { x: 1.1, z: 0.45 };              // the walkable half-extents of the deck
  static PANEL = new THREE.Vector2(0.72, 0.22);   // where you stand to drive, facing the box on the corner
  static DOOR = new THREE.Vector2(-0.8, 0);       // where you step on and off (the back end)

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
      const arm = new THREE.Mesh(new THREE.BoxGeometry(0.09, 1.28, 0.06), grey);
      this.scissor.add(arm); this.arms.push({ arm, i, z, dir });
    }
    this.deck = new THREE.Group();
    const plate = new THREE.Mesh(new THREE.BoxGeometry(2.5, 0.14, 1.2), blue); plate.position.y = 0; this.deck.add(plate);
    const rail = (sx, sy, sz, x, y, z) => { const m = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), blue); m.position.set(x, y, z); this.deck.add(m); };
    for (const z of [-0.58, 0.58]) { rail(2.5, 0.05, 0.05, 0, 1.1, z); rail(2.5, 0.04, 0.04, 0, 0.55, z); rail(2.5, 0.12, 0.03, 0, 0.13, z); }
    for (const x of [-1.23, 1.23]) { rail(0.05, 0.05, 1.2, x, 1.1, 0); rail(0.04, 0.04, 1.2, x, 0.55, 0); }
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
    this.deckY = 0.85;
    this.refresh();
  }

  refresh() {
    this.group.position.copy(this.pos);
    this.group.rotation.y = this.yaw;
    const top = this.deckY + this.height;          // the deck plate's centre
    this.deck.position.y = top;
    // the stack fills the space between the chassis tray (0.76) and the deck: each of the N
    // pairs takes an equal share, and the arm angle follows from its fixed length
    const span = Math.max(0.2, top - 0.07 - 0.76), h = span / this.N, L = 1.28;
    const ang = Math.asin(Math.min(1, h / L));      // from the horizontal
    for (const a of this.arms) {
      a.arm.position.set(0, 0.76 + h * (a.i + 0.5), a.z);
      a.arm.rotation.z = a.dir * (Math.PI / 2 - ang);
    }
    for (const W of this.wheels) W.hub.rotation.y = W.front ? -this.steer : 0;
    this.group.updateMatrixWorld(true);
    if (this.box) this.box.mesh.position.copy(this.deckWorld()).add(new THREE.Vector3(0, 0.18, 0));
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

  board(player) {
    this.aboard = true; this.driving = false; this.speed = 0;
    this.deckLocal.copy(Lift.DOOR);
    player.onLift = true;
    this.place(player);
  }
  leave(player) {
    this.aboard = false; this.driving = false; this.speed = 0; this.steer = 0;
    player.onLift = false;
    player.pos.copy(this.offboardWorld()); player.pos.y = this.floorY;
  }
  takeControls(player) { this.driving = true; this.deckLocal.copy(Lift.PANEL); this.place(player); }
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
    if (this.aboard && this.driving) this.drive(dt, player, world, collide);
    else if (this.aboard) this.walkDeck(dt, player);
    else if (this.speed) this.speed = 0;
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
    const scale = player.speedScale;
    if (player.liftUp) this.height += dt * 0.5 * scale;
    if (player.liftDown) this.height -= dt * 0.5 * scale;
    this.height = THREE.MathUtils.clamp(this.height, 0, 11.6);

    const { forward, strafe } = this.input(player);
    // the deck up = creep speed: the limit eases in over the first half metre of lift
    const raised = THREE.MathUtils.smoothstep(this.height, 0.3, 0.9);
    const vmax = THREE.MathUtils.lerp(0.97, 0.22, raised) * scale;
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
    this.pos.addScaledVector(heading, this.speed * dt);
    const wanted = this.pos.clone();
    collide(this.pos, 0.9, world, [this, this.box]);
    // pushed back against the travel = bumped into something, and the machine stops; a sideways
    // nudge (sliding along a wall) is not a bump
    const push = this.pos.clone().sub(wanted);
    if (push.lengthSq() > 1e-6 && push.dot(heading) * Math.sign(this.speed || 1) < -1e-4) this.speed = 0;
    this.travelled = (this.travelled || 0) + this.pos.distanceTo(before);
    for (const W of this.wheels) W.w.rotation.z -= (this.speed * dt) / 0.22;
    this.place(player);
  }
}
