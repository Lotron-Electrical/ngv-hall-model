import * as THREE from 'three';
import { hallToWorld } from './world.js';

export class Lift {
  constructor(scene, floorY) {
    this.floorY = floorY;
    this.pos = hallToWorld(51.2, 5.5, floorY);
    this.yaw = 0;
    this.deckY = 0.45;
    this.height = 0;
    this.aboard = false;
    this.box = null;
    this.group = new THREE.Group();
    this.group.position.copy(this.pos);
    scene.add(this.group);
    this.build();
  }

  build() {
    const mat = new THREE.MeshStandardMaterial({ color: 0xd2b66d, roughness: 0.55 });
    const railMat = new THREE.MeshStandardMaterial({ color: 0x69737f, roughness: 0.45 });
    const armMat = new THREE.MeshStandardMaterial({ color: 0x4f5964, roughness: 0.5 });
    this.base = new THREE.Mesh(new THREE.BoxGeometry(3, 0.25, 1.2), mat);
    this.deck = new THREE.Mesh(new THREE.BoxGeometry(3, 0.18, 1.2), mat);
    this.scissor = new THREE.Group();
    this.arms = [];
    for (const z of [-0.42, 0.42]) {
      for (let i = 0; i < 2; i++) {
        const arm = new THREE.Mesh(new THREE.BoxGeometry(0.08, 1.9, 0.07), armMat);
        arm.position.z = z;
        this.scissor.add(arm);
        this.arms.push({ arm, side: z, dir: i ? -1 : 1 });
      }
    }
    this.rails = new THREE.Group();
    for (const z of [-0.62, 0.62]) {
      const rail = new THREE.Mesh(new THREE.BoxGeometry(3.05, 0.08, 0.05), railMat);
      rail.position.set(0, 1.05, z);
      this.rails.add(rail);
    }
    for (const x of [-1.45, 1.45]) {
      const rail = new THREE.Mesh(new THREE.BoxGeometry(0.05, 1.1, 1.25), railMat);
      rail.position.set(x, 0.58, 0);
      this.rails.add(rail);
    }
    this.group.add(this.base, this.scissor, this.deck, this.rails);
    this.refresh();
  }

  refresh() {
    this.group.position.copy(this.pos);
    this.group.rotation.y = this.yaw;
    this.base.position.y = 0.12;
    this.deck.position.y = this.deckY + this.height;
    this.rails.position.y = this.deckY + this.height;
    const mid = this.deckY * 0.5 + this.height * 0.5;
    const angle = THREE.MathUtils.lerp(0.95, 0.18, this.height / 11.6);
    for (const a of this.arms) {
      a.arm.position.set(0, mid, a.side);
      a.arm.rotation.z = a.dir * angle;
      a.arm.scale.y = 0.95 + this.height * 0.08;
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
    this.aboard = this.contains(player.pos);
    if (this.aboard) {
      if (player.liftUp) this.height += dt * 0.5 * player.speedScale;
      if (player.liftDown) this.height -= dt * 0.5 * player.speedScale;
      this.height = THREE.MathUtils.clamp(this.height, 0, 11.6);
      const forward = (player.keys.has('KeyW') ? 1 : 0) - (player.keys.has('KeyS') ? 1 : 0) - player.move.y;
      const strafe = (player.keys.has('KeyD') ? 1 : 0) - (player.keys.has('KeyA') ? 1 : 0) + player.move.x;
      const v = new THREE.Vector3(strafe, 0, -forward).clampLength(0, 1).applyAxisAngle(new THREE.Vector3(0, 1, 0), player.yaw);
      this.pos.addScaledVector(v, dt * 1.7 * player.speedScale);
      collide(this.pos, 0.9, world);
      player.pos.x = this.pos.x;
      player.pos.z = this.pos.z;
      player.pos.y = this.floorY + this.deckY + this.height;
    }
    this.refresh();
  }
}
