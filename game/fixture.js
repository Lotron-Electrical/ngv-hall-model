import * as THREE from 'three';

// THE FIXTURE, PORTED FROM THE PROPOSAL SIM (Lloyd, 2026-09-04: the light the game fits must be
// the same product the simulator sells, not a white box). This is index.html rebuild()'s default
// system lifted out whole: a 20 x 20 mm aluminium extrusion whose back plate sits on the shaft
// valley, a 16 mm black acrylic cover on its face, one emitter tile per LED at 60/m behind the
// cover, and one halo disc per LED anchored 1 mm proud of the aperture. Every constant and every
// line of the placement maths is the sim's, unchanged, so index.html's rebuild() can import this
// module next and the two can never drift apart.
//
// The run polyline is the strip line 12 mm proud of the shaft valley, which is why EXT_BACK is
// negative: the extrusion runs from the valley (-12 mm) out to its face (+8 mm).
// (Lloyd, 2026-09-05: "the lights should also look like our pixel bars") the fitted light is the
// NGV-PX-20x45 seamless magnetic bar: 20 mm wide, 45 mm deep, black anodised, a full-face black
// diffuser (32 % T, so it reads black with the strip off). The run polyline is still the strip line
// 12 mm proud of the valley; the bar's face is now 33 mm proud of it
export const EXT_W = 0.020, EXT_D = 0.045, EXT_BACK = -0.012, FACE_W = 0.018, WALL = 0.002;
export const TILE_T = 0.001, LEDS_PER_M = 60;
// black acrylic passes only part of the light; 0.25 sits on the ACRYLITE LED black/white figure,
// near the middle of the measured range for day/night cover grades
export const DIFFUSER_T = 0.25;
// what reaches the room is DIFFUSER_T; what the EYE sees looking straight at a lit face is a
// hundred times the hall, so the face is drawn at the LED colour, not at 25% grey
export const EMIT_EXPOSURE = 1 / DIFFUSER_T;
// the halo is one soft disc per LED summed along the line: HALO_PEAK is what that sum reaches on
// the strip line at full output, HALO_MEAN the disc's mean alpha along a diameter
export const HALO_PEAK = 0.7, HALO_MEAN = 0.4;
export const HALO_SIZE = 0.08;                        // the sim's gsize for the black cover
export const PITCH = 1 / LEDS_PER_M;
export const BASE_OFF = EXT_BACK + EXT_D + 0.0006;    // the cover tile's plane
export const EMIT_OFF = BASE_OFF + TILE_T / 2 + 0.0004;
export const HALO_OFF = EMIT_OFF + 0.00025 + 0.001;   // glare leaves the aperture, not the die
export const RIBBON_PARTS = 3;                        // back plate and two walls
export const HALO_GAIN = HALO_PEAK / ((HALO_SIZE / PITCH) * HALO_MEAN * DIFFUSER_T);

// the sim's glow sprite: a radial disc, no colour space, additive
const GLOWTEX = (() => {
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d');
  const r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(0.25, 'rgba(255,255,255,.55)'); r.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = r; g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.NoColorSpace; return t;
})();

// the sim's basis, exactly: the tangent is up the run, b is across the face, nn is out of it
export function slotBasis(slot, t = new THREE.Vector3(), b = new THREE.Vector3(), nn = new THREE.Vector3()) {
  t.copy(slot.tangent).normalize();
  b.crossVectors(t, slot.normal).normalize();
  nn.crossVectors(b, t).normalize();
  return { t, b, nn };
}

// ONE draw call per part for the whole install: 768 slots is 2,304 ribbon boxes, 768 covers and
// 69,120 emitter tiles, which is the sim's own scale. Phong/Lambert/Basic only for the per-LED
// meshes: the sim measured 73k instances of MeshStandardMaterial halving the frame rate on its own.
export class FixtureSet {
  constructor(scene, slots) {
    this.scene = scene;
    this.slots = slots;
    const n = slots.length;
    this.leds = Math.max(1, Math.round((slots[0]?.len || 1.5) / PITCH));
    const L = this.leds;
    this.vis = new Array(n).fill(false);
    // (Lloyd, 2026-09-05: "they are black until turned on") a fitted bar is a black bar until its
    // column is powered; lit[i] is the power, vis[i] the bar
    this.lit = new Array(n).fill(false);
    this.colour = slots.map(() => new THREE.Color(1, 1, 1));

    this.ribbon = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1),
      new THREE.MeshStandardMaterial({ color: 0x0c0c0e, metalness: 0.55, roughness: 0.5 }), n * RIBBON_PARTS);   // black anodised
    this.cover = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1),
      new THREE.MeshPhongMaterial({ color: 0x08080a, specular: 0x222222, shininess: 30 }), n);   // the black diffuser, off
    this.emit = new THREE.InstancedMesh(new THREE.BoxGeometry(FACE_W, PITCH, 0.0005),
      new THREE.MeshBasicMaterial({ color: new THREE.Color().setScalar(EMIT_EXPOSURE), toneMapped: false, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }), n * L);
    this.emit.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(n * L * 3), 3);
    this.emit.instanceColor.setUsage(THREE.DynamicDrawUsage);

    // the halo shares the emitter's colour buffer, as it does in the sim: one write lights both
    const hpos = new Float32Array(n * L * 3);
    const gg = new THREE.BufferGeometry();
    gg.setAttribute('position', new THREE.BufferAttribute(hpos, 3));
    gg.setAttribute('color', new THREE.BufferAttribute(this.emit.instanceColor.array, 3));
    gg.attributes.color.setUsage(THREE.DynamicDrawUsage);
    this.halo = new THREE.Points(gg, new THREE.PointsMaterial({ map: GLOWTEX, color: new THREE.Color().setScalar(HALO_GAIN), size: HALO_SIZE, vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false, sizeAttenuation: true }));
    this.hpos = hpos;

    // an InstancedMesh caches a bounding sphere built from the matrices it had when it was first
    // culled; ours change as lights go in, so culling them would hide fitted sections
    for (const m of [this.ribbon, this.cover, this.emit, this.halo]) { m.frustumCulled = false; scene.add(m); }

    this._M = new THREE.Matrix4(); this._p = new THREE.Vector3();
    this._t = new THREE.Vector3(); this._b = new THREE.Vector3(); this._nn = new THREE.Vector3();
    for (let i = 0; i < n; i++) { this.writeHalo(i); this.writeMatrices(i); }
    this.ribbon.instanceMatrix.needsUpdate = this.cover.instanceMatrix.needsUpdate = this.emit.instanceMatrix.needsUpdate = true;
    this.emit.instanceColor.needsUpdate = true;
  }

  // the halo positions never move, fitted or not: an unfitted slot is dark because its colour is
  // zero, which costs nothing per frame
  writeHalo(i) {
    const s = this.slots[i], L = this.leds, len = s.len || 1.5;
    const { t, nn } = slotBasis(s, this._t, this._b, this._nn);
    for (let j = 0; j < L; j++) {
      const d = (j + 0.5) * PITCH - len / 2;
      const k = (i * L + j) * 3;
      this.hpos[k] = s.center.x + t.x * d + nn.x * HALO_OFF;
      this.hpos[k + 1] = s.center.y + t.y * d + nn.y * HALO_OFF;
      this.hpos[k + 2] = s.center.z + t.z * d + nn.z * HALO_OFF;
    }
    this.halo.geometry.attributes.position.needsUpdate = true;
  }

  // a hidden slot gets a zero-scale matrix: it stays in the buffer and costs a degenerate triangle
  writeMatrices(i) {
    const s = this.slots[i], L = this.leds, len = s.len || 1.5, on = this.vis[i];
    const M = this._M, p = this._p;
    const { t, b, nn } = slotBasis(s, this._t, this._b, this._nn);
    const sc = new THREE.Vector3();
    const zero = () => { M.makeScale(0, 0, 0); };
    const part = (rk, off, side, w, d) => {
      if (!on) { zero(); this.ribbon.setMatrixAt(rk, M); return; }
      M.makeBasis(b, t, nn);
      p.copy(s.center).addScaledVector(nn, off).addScaledVector(b, side);
      sc.set(w, len, d); M.setPosition(p); M.scale(sc);
      this.ribbon.setMatrixAt(rk, M);
    };
    const r0 = i * RIBBON_PARTS;
    part(r0, EXT_BACK + WALL / 2, 0, EXT_W, WALL);                    // back plate on the valley
    part(r0 + 1, EXT_BACK + EXT_D / 2, (EXT_W - WALL) / 2, WALL, EXT_D);   // walls
    part(r0 + 2, EXT_BACK + EXT_D / 2, -(EXT_W - WALL) / 2, WALL, EXT_D);
    if (!on) { zero(); this.cover.setMatrixAt(i, M); }
    else {
      M.makeBasis(b, t, nn); p.copy(s.center).addScaledVector(nn, BASE_OFF);
      sc.set(FACE_W, len, TILE_T); M.setPosition(p); M.scale(sc); this.cover.setMatrixAt(i, M);
    }
    for (let j = 0; j < L; j++) {
      if (!on) { zero(); this.emit.setMatrixAt(i * L + j, M); continue; }
      const d = (j + 0.5) * PITCH - len / 2;
      M.makeBasis(b, t, nn);
      p.copy(s.center).addScaledVector(t, d).addScaledVector(nn, EMIT_OFF);
      M.setPosition(p);
      this.emit.setMatrixAt(i * L + j, M);
    }
  }

  writeColour(i) {
    const L = this.leds, a = this.emit.instanceColor.array, c = this.colour[i], on = this.vis[i] && this.lit[i];
    const r = on ? c.r : 0, g = on ? c.g : 0, bl = on ? c.b : 0;
    for (let j = 0; j < L; j++) { const k = (i * L + j) * 3; a[k] = r; a[k + 1] = g; a[k + 2] = bl; }
  }

  show(i, visible) {
    if (this.vis[i] === !!visible) return;
    this.vis[i] = !!visible;
    this.writeMatrices(i); this.writeColour(i);
    this.ribbon.instanceMatrix.needsUpdate = this.cover.instanceMatrix.needsUpdate = this.emit.instanceMatrix.needsUpdate = true;
    this.emit.instanceColor.needsUpdate = true;
    this.halo.geometry.attributes.color.needsUpdate = true;
  }

  setColour(i, colour) {
    this.colour[i].copy(colour);
    if (!this.vis[i]) return;
    this.writeColour(i);
    this.emit.instanceColor.needsUpdate = true;
    this.halo.geometry.attributes.color.needsUpdate = true;
  }

  // one pass over the whole buffer for the guide's pulse, instead of 768 calls that each set the
  // same two dirty flags
  // power for one slot's bar: lit, its LEDs show the colour; unpowered, the bar stays black
  power(i, on) {
    if (this.lit[i] === !!on) return;
    this.lit[i] = !!on;
    this.writeColour(i);
    this.emit.instanceColor.needsUpdate = true;
    this.halo.geometry.attributes.color.needsUpdate = true;
  }

  setColourAll(colour) {
    const L = this.leds, a = this.emit.instanceColor.array;
    for (let i = 0; i < this.slots.length; i++) {
      this.colour[i].copy(colour);
      if (!this.vis[i] || !this.lit[i]) continue;
      for (let j = 0; j < L; j++) { const k = (i * L + j) * 3; a[k] = colour.r; a[k + 1] = colour.g; a[k + 2] = colour.b; }
    }
    this.emit.instanceColor.needsUpdate = true;
    this.halo.geometry.attributes.color.needsUpdate = true;
  }

  dispose() {
    for (const m of [this.ribbon, this.cover, this.emit, this.halo]) {
      this.scene.remove(m); m.geometry.dispose();
      for (const mm of [].concat(m.material)) mm.dispose();
    }
  }
}
