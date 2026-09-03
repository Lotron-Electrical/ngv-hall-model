import * as THREE from 'three';

const SLOT_LEN = 1.5;

export class Install {
  constructor(scene, runsData, saved) {
    this.scene = scene;
    this.runs = [];
    this.slots = [];
    this.fitted = new Set(saved?.fitted || []);
    this.mat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xd7ecff, emissiveIntensity: 0.9, roughness: 0.35 });
    this.ghost = new THREE.MeshStandardMaterial({ color: 0x34404c, emissive: 0x101820, emissiveIntensity: 0.18, transparent: true, opacity: 0.35 });
    this.build(runsData);
  }

  build(data) {
    for (const run of data.runs) {
      const points = run.points.map((p) => new THREE.Vector3(p[0], p[1], p[2]));
      const slots = this.slotsForRun(points);
      const record = { ...run, points, slots };
      this.runs.push(record);
      for (const slot of slots) {
        slot.column = run.column;
        slot.gap = run.gap;
        slot.id = `${run.column}-${run.gap}-${slot.index}`;
        slot.normal = new THREE.Vector3(run.normal[0], run.normal[1], run.normal[2]).normalize();
        if (this.fitted.has(slot.id)) this.drawSlot(slot);
        this.slots.push(slot);
      }
    }
  }

  slotsForRun(points) {
    const slots = [];
    let target = SLOT_LEN * 0.5;
    let walked = 0;
    for (let i = 1; i < points.length && slots.length < 8; i++) {
      const a = points[i - 1], b = points[i];
      const seg = b.clone().sub(a);
      const len = seg.length();
      while (walked + len >= target && slots.length < 8) {
        const t = (target - walked) / len;
        const center = a.clone().lerp(b, t);
        const tangent = seg.clone().normalize();
        slots.push({ index: slots.length, center, tangent });
        target += SLOT_LEN;
      }
      walked += len;
    }
    return slots;
  }

  nextForRun(run) {
    return run.slots.find((s) => !this.fitted.has(s.id));
  }

  findFitSlot(eye) {
    let best = null;
    let dist = Infinity;
    for (const run of this.runs) {
      const slot = this.nextForRun(run);
      if (!slot) continue;
      const d = slot.center.distanceTo(eye);
      if (d < 1.8 && d < dist) {
        best = slot;
        dist = d;
      }
    }
    return best;
  }

  fit(slot, player) {
    this.fitted.add(slot.id);
    this.drawSlot(slot);
    this.lastFit = slot;
    player.carry = null;
    return true;
  }

  drawSlot(slot) {
    const geom = new THREE.BoxGeometry(0.055, SLOT_LEN, 0.055);
    const mesh = new THREE.Mesh(geom, this.mat);
    mesh.position.copy(slot.center).addScaledVector(slot.normal, 0.035);
    const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), slot.tangent.clone().normalize());
    mesh.quaternion.copy(q);
    this.scene.add(mesh);
    slot.mesh = mesh;
  }

  counts() {
    const byColumn = new Map();
    for (const slot of this.slots) byColumn.set(slot.column, (byColumn.get(slot.column) || 0) + (this.fitted.has(slot.id) ? 1 : 0));
    let columnsDone = 0;
    for (const n of byColumn.values()) if (n >= 64) columnsDone++;
    return { fitted: this.fitted.size, total: this.slots.length, columnsDone };
  }

  saveShape() {
    return { fitted: [...this.fitted] };
  }
}
