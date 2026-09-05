import * as THREE from 'three';
import { FixtureSet, slotBasis, BASE_OFF } from './fixture.js';

const SLOT_LEN = 1.5;
// the strip's white die, the same colour hallmat.js lights the room with
const WHITE = new THREE.Color(1.0, 0.93, 0.82);
const GREEN = new THREE.Color(0.15, 1.0, 0.35);
const GUIDE_KEY = 'ngv-install-guide';
const PULSE_HZ = 1.2;

// THE GUIDE (Lloyd, 2026-09-04): where the next light goes, without reading the hall. Every
// empty slot stands as a pulsing red bar and every finished one pulses green, so a glance down a
// shaft says what is left. One InstancedMesh for the bars, a fitted slot's own fixture colour for
// the green: no extra geometry per light.
class GuideBoxes {
  constructor(scene, slots) {
    this.slots = slots;
    this.scene = scene;
    this.mesh = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1),
      new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, toneMapped: false, blending: THREE.AdditiveBlending, depthWrite: false }), slots.length);
    this.mesh.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(slots.length * 3), 3);
    this.mesh.instanceColor.setUsage(THREE.DynamicDrawUsage);
    this.mesh.frustumCulled = false;   // same reason as the fixture set: the matrices change
    this.mesh.visible = false;
    scene.add(this.mesh);
    this.vis = new Array(slots.length).fill(true);
    const M = new THREE.Matrix4(), p = new THREE.Vector3(), sc = new THREE.Vector3();
    const t = new THREE.Vector3(), b = new THREE.Vector3(), nn = new THREE.Vector3();
    this._M = M; this._p = p; this._sc = sc; this._t = t; this._b = b; this._nn = nn;
    for (let i = 0; i < slots.length; i++) this.write(i);
    this.mesh.instanceMatrix.needsUpdate = true;
  }

  write(i) {
    const s = this.slots[i], M = this._M;
    if (!this.vis[i]) { M.makeScale(0, 0, 0); this.mesh.setMatrixAt(i, M); return; }
    const { t, b, nn } = slotBasis(s, this._t, this._b, this._nn);
    M.makeBasis(b, t, nn);
    this._p.copy(s.center).addScaledVector(nn, BASE_OFF);
    this._sc.set(0.09, s.len || SLOT_LEN, 0.09);
    M.setPosition(this._p); M.scale(this._sc);
    this.mesh.setMatrixAt(i, M);
  }

  show(i, visible) {
    if (this.vis[i] === !!visible) return;
    this.vis[i] = !!visible;
    this.write(i);
    this.mesh.instanceMatrix.needsUpdate = true;
  }

  pulse(v) {
    const a = this.mesh.instanceColor.array;
    for (let i = 0; i < this.slots.length; i++) { a[i * 3] = v; a[i * 3 + 1] = v * 0.07; a[i * 3 + 2] = v * 0.05; }
    this.mesh.instanceColor.needsUpdate = true;
  }

  dispose() { this.scene.remove(this.mesh); this.mesh.geometry.dispose(); this.mesh.material.dispose(); }
}

export class Install {
  constructor(scene, runsData, saved) {
    this.scene = scene;
    this.runs = [];
    this.slots = [];
    this.fitted = new Set(saved?.fitted || []);
    this.build(runsData);
    // the fitted light is the proposal sim's fixture, built once for every slot in the hall
    this.fx = new FixtureSet(scene, this.slots);
    this.guides = new GuideBoxes(scene, this.slots);
    for (const [i, slot] of this.slots.entries()) {
      slot.i = i;
      this.fx.setColour(i, WHITE);
      if (this.fitted.has(slot.id)) { this.fx.show(i, true); this.guides.show(i, false); }
    }
    // (Lloyd, 2026-09-05: "they are black until turned on") a column is powered up when its last
    // bar goes in, the crew's test-fire; a saved game comes back with its finished columns lit
    this.powered = new Set();
    for (const c of new Set(this.slots.map((s) => s.column))) if (this.columnComplete(c)) this.powerColumn(c);
    let g = null;
    try { g = localStorage.getItem(GUIDE_KEY); } catch (e) { g = null; }
    this.guide = g === null ? true : g === '1';
    this.guides.mesh.visible = this.guide;
    this.t = 0;
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
        slots.push({ index: slots.length, center, tangent, len: SLOT_LEN });
        target += SLOT_LEN;
      }
      walked += len;
    }
    return slots;
  }

  nextForRun(run) {
    return run.slots.find((s) => !this.fitted.has(s.id));
  }

  // (Lloyd, 2026-09-05: "I can't seem to put the light on the column when I am on the scissor
  // lift") reach used to be a 1.8 m ball round the DECK'S CENTRE, which the lowest bar sits under
  // and the rest sit above unless the deck is almost level with them. Reach is the hands now: the
  // next bar of a run is fittable when it is within FLAT m on the plan of where you stand and
  // within RISE m up or down of your hands (1.2 m above your feet), on the deck or on the floor
  static FLAT = 2.0;
  static RISE = 1.1;
  static HANDS = 1.2;
  findFitSlot(feet) {
    let best = null, dist = Infinity;
    for (const run of this.runs) {
      const slot = this.nextForRun(run);
      if (!slot) continue;
      const flat = Math.hypot(slot.center.x - feet.x, slot.center.z - feet.z), dy = slot.center.y - (feet.y + Install.HANDS);
      if (flat < Install.FLAT && Math.abs(dy) < Install.RISE && flat < dist) { best = slot; dist = flat; }
    }
    return best;
  }
  // the nearest run's next bar when none is in reach, with how far up or down it is: the prompt
  // says which way to move the deck instead of offering nothing
  nextSlotNear(feet) {
    let best = null, dist = Infinity;
    for (const run of this.runs) {
      const slot = this.nextForRun(run);
      if (!slot) continue;
      const flat = Math.hypot(slot.center.x - feet.x, slot.center.z - feet.z);
      if (flat < 3.2 && flat < dist) { best = slot; dist = flat; }
    }
    return best ? { slot: best, dy: best.center.y - (feet.y + Install.HANDS), flat: dist } : null;
  }

  fit(slot, player) {
    this.fitted.add(slot.id);
    this.fx.show(slot.i, true);
    this.guides.show(slot.i, false);
    this.lastFit = slot;
    player.carry = null;
    if (!this.powered.has(slot.column) && this.columnComplete(slot.column)) { this.powerColumn(slot.column); this.justPowered = slot.column; }
    return true;
  }

  columnComplete(column) { return this.slots.every((s) => s.column !== column || this.fitted.has(s.id)); }
  powerColumn(column) {
    this.powered.add(column);
    for (const s of this.slots) if (s.column === column) this.fx.power(s.i, true);
  }

  // fx.js hides a fitted light for a few seconds in the small hours; it used to reach into a
  // per-slot mesh that no longer exists, so it asks the set instead
  showSlot(slot, visible) { this.fx.show(slot.i, visible); }

  setGuide(on) {
    this.guide = !!on;
    try { localStorage.setItem(GUIDE_KEY, this.guide ? '1' : '0'); } catch (e) { /* private mode */ }
    this.guides.mesh.visible = this.guide;
    if (!this.guide) this.fx.setColourAll(WHITE);   // steady white the moment the guide goes off
  }

  // the pulse. Guide off is one comparison a frame: the colour buffers are left alone.
  update(t) {
    this.t = t;
    if (!this.guide) return;
    const p = 0.5 + 0.5 * Math.sin(t * Math.PI * 2 * PULSE_HZ);
    this.guides.pulse(0.18 + 0.57 * p);
    this.fx.setColourAll(WHITE.clone().lerp(GREEN, p * 0.85));
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
