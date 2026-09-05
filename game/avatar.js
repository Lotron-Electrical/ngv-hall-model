import * as THREE from 'three';

// THE CHARACTER MODEL (Lloyd, 2026-09-05: "we will also need character models"). One articulated
// worker, built from parts so it needs no download: hard hat, head, a hi-vis vest with two
// reflective bands over a dark shirt, arms and legs that swing in a walk cycle, and a name tag
// over the head. Everyone who is not you wears it: the other players in a crew room (net.js) and
// the NPC crew (crew.js). The group's origin is between the feet on the floor; +z is the way it
// faces (the same convention as crew.js's old figure: rotation.y = yaw with yaw = atan2(dx, dz)).
//
//   av = new Avatar(vestColour, name)   av.group goes in the scene
//   av.walk(dt, speed)                  speed in m/s drives the legs; 0 lets them settle
//   av.setCarry(kind)                   null | 'box' | 'bag' | 'light' | 'wrap': arms come forward, a prop rides in the hands
//   av.setLook(pitch)                   the head tilts with the eyes
//   av.dispose()

const SKIN = 0xc9a07a, HAT = 0xf2f2f2, SHIRT = 0x2a2f36, TROUSER = 0x23262b, BOOT = 0x151515, BAND = 0xd8d8d0;
const SHOULDER = 1.42, HIP = 0.92;

function box(w, h, d, color, extra = {}) {
  return new THREE.Mesh(new THREE.BoxGeometry(w, h, d), new THREE.MeshStandardMaterial({ color, roughness: 0.85, ...extra }));
}

// a limb hangs from its pivot: the pivot group sits at the joint, the mesh is offset down half its length
function limb(w, len, d, color, lower = null) {
  const pivot = new THREE.Group();
  const upper = box(w, len, d, color); upper.position.y = -len / 2; pivot.add(upper);
  if (lower) { const l = box(lower.w, lower.h, lower.d, lower.color); l.position.y = -len - lower.h / 2 + 0.01; pivot.add(l); }
  return pivot;
}

function nameTag(text) {
  const c = document.createElement('canvas'); c.width = 256; c.height = 64;
  const g = c.getContext('2d');
  g.fillStyle = 'rgba(0,0,0,0.55)'; g.beginPath(); g.roundRect(8, 8, 240, 48, 10); g.fill();
  g.fillStyle = '#fff'; g.font = '600 30px "Barlow Condensed", "Arial Narrow", sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillText(String(text || '').slice(0, 16), 128, 33);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true, depthTest: false, depthWrite: false }));
  s.scale.set(0.9, 0.225, 1); s.renderOrder = 999;
  return s;
}

export class Avatar {
  constructor(vestColour = 0xff7a1a, name = '') {
    const g = this.group = new THREE.Group();
    this.vest = new THREE.MeshStandardMaterial({ color: vestColour, roughness: 0.75, emissive: vestColour, emissiveIntensity: 0.12 });
    // torso: shirt under a vest, two reflective bands round the chest and waist
    const torso = box(0.36, 0.52, 0.2, SHIRT); torso.position.y = HIP + 0.26; g.add(torso);
    const vest = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.46, 0.24), this.vest); vest.position.y = HIP + 0.27; g.add(vest);
    for (const y of [HIP + 0.4, HIP + 0.14]) { const b = box(0.41, 0.045, 0.25, BAND, { roughness: 0.3, metalness: 0.4 }); b.position.y = y; g.add(b); }
    // hips and legs
    const hips = box(0.34, 0.16, 0.2, TROUSER); hips.position.y = HIP - 0.02; g.add(hips);
    this.legL = limb(0.14, 0.5, 0.16, TROUSER, { w: 0.15, h: 0.36, d: 0.17, color: TROUSER }); this.legL.position.set(-0.1, HIP - 0.06, 0); g.add(this.legL);
    this.legR = limb(0.14, 0.5, 0.16, TROUSER, { w: 0.15, h: 0.36, d: 0.17, color: TROUSER }); this.legR.position.set(0.1, HIP - 0.06, 0); g.add(this.legR);
    for (const L of [this.legL, this.legR]) { const boot = box(0.15, 0.09, 0.26, BOOT); boot.position.set(0, -0.86, 0.05); L.add(boot); }
    // arms: shirt sleeves, skin hands
    this.armL = limb(0.11, 0.3, 0.12, SHIRT, { w: 0.1, h: 0.3, d: 0.11, color: SKIN }); this.armL.position.set(-0.25, SHOULDER, 0); g.add(this.armL);
    this.armR = limb(0.11, 0.3, 0.12, SHIRT, { w: 0.1, h: 0.3, d: 0.11, color: SKIN }); this.armR.position.set(0.25, SHOULDER, 0); g.add(this.armR);
    // head and hard hat, on a neck pivot so it can tilt with the look
    this.head = new THREE.Group(); this.head.position.y = SHOULDER + 0.1; g.add(this.head);
    const skull = new THREE.Mesh(new THREE.SphereGeometry(0.12, 12, 10), new THREE.MeshStandardMaterial({ color: SKIN, roughness: 0.9 })); skull.position.y = 0.13; this.head.add(skull);
    const hatMat = new THREE.MeshStandardMaterial({ color: HAT, roughness: 0.45 });
    const brim = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.025, 14), hatMat); brim.position.y = 0.2; this.head.add(brim);
    const dome = new THREE.Mesh(new THREE.SphereGeometry(0.135, 14, 10, 0, Math.PI * 2, 0, Math.PI / 2), hatMat); dome.position.y = 0.2; this.head.add(dome);
    const peak = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.02, 0.09), hatMat); peak.position.set(0, 0.2, 0.17); this.head.add(peak);
    // the name over the hat
    this.tag = nameTag(name); this.tag.position.y = 2.05; g.add(this.tag);
    // what the hands hold
    this.prop = null; this.carry = null;
    this.phase = 0; this.swing = 0; this._floorY = 0;
  }

  setName(name) {
    if (this.tag) { this.group.remove(this.tag); this.tag.material.map.dispose(); this.tag.material.dispose(); }
    this.tag = nameTag(name); this.tag.position.y = 2.05; this.group.add(this.tag);
  }

  // the legs and free arms swing with the pace; the body bobs a little at the step
  walk(dt, speed) {
    const moving = speed > 0.05;
    const target = moving ? Math.min(1, speed / 1.6) : 0;
    this.swing += (target - this.swing) * Math.min(1, dt * 8);
    if (moving) this.phase += dt * Math.max(3.2, speed * 4.2);
    const s = Math.sin(this.phase) * 0.65 * this.swing;
    this.legL.rotation.x = s; this.legR.rotation.x = -s;
    if (!this.carry) { this.armL.rotation.x = -s * 0.8; this.armR.rotation.x = s * 0.8; }
    this.group.position.y = this._floorY + Math.abs(Math.sin(this.phase)) * 0.035 * this.swing;
  }
  // whoever moves it sets the floor under the feet; walk() adds its bob on top
  get floorY() { return this._floorY; }
  set floorY(v) { this._floorY = v; }

  setLook(pitch) { this.head.rotation.x = THREE.MathUtils.clamp(-(pitch || 0) * 0.7, -0.6, 0.6); }

  // arms forward with a prop in the hands: a box, a bag, a bar, or a sheet of wrap
  setCarry(kind, withProp = true) {
    if (kind === this.carry) return;
    this.carry = kind || null;
    if (this.prop) { this.group.remove(this.prop); this.prop.traverse((o) => { if (o.isMesh) { o.geometry.dispose(); o.material.dispose(); } }); this.prop = null; }
    if (!this.carry) { this.armL.rotation.set(0, 0, 0); this.armR.rotation.set(0, 0, 0); return; }
    this.armL.rotation.set(-1.25, 0, 0.15); this.armR.rotation.set(-1.25, 0, -0.15);
    if (!withProp) return;   // the crew carry the real item mesh (crew.js settle); only the pose is wanted
    let p;
    switch (this.carry) {
      case 'box': case 'emptyBox': p = box(0.5, 0.34, 0.38, this.carry === 'box' ? 0x9a7b55 : 0x6f6250); p.position.set(0, SHOULDER - 0.3, 0.42); break;
      case 'bag': p = new THREE.Mesh(new THREE.SphereGeometry(0.3, 10, 8), new THREE.MeshStandardMaterial({ color: 0x41523d, roughness: 0.95 })); p.scale.set(1, 1.25, 0.8); p.position.set(0, SHOULDER - 0.35, 0.4); break;
      case 'light': case 'wrapped': p = box(1.5, 0.02, 0.045, this.carry === 'wrapped' ? 0xe8e8e0 : 0x0c0c0e, { roughness: 0.4, metalness: 0.5 }); p.position.set(0, SHOULDER - 0.28, 0.42); break;
      case 'wrap': p = box(0.42, 0.06, 0.34, 0xf4f4ee, { transparent: true, opacity: 0.5 }); p.position.set(0, SHOULDER - 0.3, 0.42); break;
      default: p = box(0.3, 0.3, 0.3, 0x888888); p.position.set(0, SHOULDER - 0.3, 0.42);
    }
    this.prop = p; this.group.add(p);
  }

  dispose() {
    this.group.removeFromParent();
    this.group.traverse((o) => { if (o.isMesh || o.isSprite) { if (o.geometry) o.geometry.dispose(); const m = o.material; if (m) { if (m.map) m.map.dispose(); m.dispose(); } } });
  }
}
