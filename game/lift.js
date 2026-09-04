import * as THREE from 'three';
import { hallToWorld } from './world.js';

export class Lift {
  constructor(scene, floorY) {
    this.floorY = floorY;
    this.pos = hallToWorld(63.6, 6.6, floorY);   // parked at the aisle's end, clear of both pallet rows
    this.yaw = 0;
    this.deckY = 0.85;
    this.height = 0;
    this.aboard = false;
    this.box = null;
    this.group = new THREE.Group();
    this.group.position.copy(this.pos);
    scene.add(this.group);
    this.build();
  }

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
    for (const x of [-0.85, 0.85]) for (const z of [-0.62, 0.62]) {
      const w = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 0.16, 14), rubber); w.rotation.x = Math.PI / 2; w.position.set(x, 0.22, z); this.base.add(w);
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
    const box = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.22, 0.2), dark); box.position.set(1.0, 1.0, 0.62); this.deck.add(box);
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
    if (this.box) this.box.mesh.position.copy(this.deckWorld()).add(new THREE.Vector3(0, 0.18, 0));
  }

  deckWorld() {
    return this.group.localToWorld(new THREE.Vector3(0, this.deckY + this.height + 0.1, 0));
  }

  contains(p) {
    const q = p.clone();
    this.group.worldToLocal(q);
    return Math.abs(q.x) < 1.55 && Math.abs(q.z) < 0.7 && Math.abs(p.y - (this.floorY + this.deckY + this.height)) < 0.9;
  }

  offboardWorld() {
    return this.group.localToWorld(new THREE.Vector3(1.95, this.deckY + this.height, 0));
  }

  update(dt, player, world, collide) {
    // aboard is set by ACTION (get on / get off), never by walking into the footprint
    if (this.aboard) {
      if (player.liftUp) this.height += dt * 0.5 * player.speedScale;
      if (player.liftDown) this.height -= dt * 0.5 * player.speedScale;
      this.height = THREE.MathUtils.clamp(this.height, 0, 11.6);
      const forward = (player.keys.has('KeyW') ? 1 : 0) - (player.keys.has('KeyS') ? 1 : 0) - player.move.y;
      const strafe = (player.keys.has('KeyD') ? 1 : 0) - (player.keys.has('KeyA') ? 1 : 0) + player.move.x;
      const v = new THREE.Vector3(strafe, 0, -forward).clampLength(0, 1).applyAxisAngle(new THREE.Vector3(0, 1, 0), player.yaw);
      this.pos.addScaledVector(v, dt * 1.7 * player.speedScale);
      collide(this.pos, 0.9, world, [this, this.box]);
      player.pos.x = this.pos.x;
      player.pos.z = this.pos.z;
      player.pos.y = this.floorY + this.deckY + this.height;
    }
    this.refresh();
  }
}
