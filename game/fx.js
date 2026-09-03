import * as THREE from 'three';

// FATIGUE AND THE SMALL HOURS (Lloyd, 2026-09-04). From 01:00 the body slows (clock.fatigue()
// scales walking, driving and the lift). From 03:00 the mind goes too: a light you have just
// fitted is not there when you look back (it returns in a few seconds), the columns lean, the
// colours drift, the view breathes, and a second lift stands across the hall for a moment.
// All of it harmless: nothing here changes what is actually fitted or where anything is.
export class Fx {
  constructor(scene, camera, hallScene, lift, install) {
    this.scene = scene; this.camera = camera; this.hall = hallScene; this.lift = lift; this.install = install;
    this.t = 0; this.level = 0;
    this.vanish = null;            // {slot, yaw0, hidden, until}
    this.ghost = null; this.ghostUntil = 0; this.nextGhost = 40 + Math.random() * 60;
    this.baseFov = camera.fov;
    this.vignette = document.getElementById('vignette');
    this.bg = scene.background ? scene.background.clone() : new THREE.Color(0x08090b);
  }

  // the level is 0 before 03:00, 1 at 04:00, 1.8 at 05:00: the last hour is the worst (Lloyd)
  levelFor(clock) { const h = clock.minute / 60; return h < 27 ? 0 : h < 28 ? (h - 27) : 1 + (h - 28) * 0.8; }

  onFit(slot, player) {
    if (this.level <= 0 || !slot.mesh) return;
    // a quarter of the fits from 03:00, over half by 04:00: it vanishes once you look away
    if (Math.random() < 0.25 + 0.3 * Math.min(1, this.level)) this.vanish = { slot, yaw0: player.yaw, hidden: false, until: 0 };
  }

  update(dt, clock, player) {
    this.t += dt;
    this.level = this.levelFor(clock);
    const L = this.level, k = Math.min(1, L);
    // the tired eye: a vignette that closes in from 01:00 and pulses in the small hours
    const tired = Math.max(0, Math.min(1, (clock.minute / 60 - 25) / 3));
    if (this.vignette) this.vignette.style.opacity = (tired * 0.55 + k * 0.25 * (0.5 + 0.5 * Math.sin(this.t * 0.7))).toFixed(3);
    if (L <= 0) { this.reset(); return; }
    // the view breathes and rolls a little; the columns lean
    this.camera.fov = this.baseFov + Math.sin(this.t * 0.45) * 4 * k; this.camera.updateProjectionMatrix();
    this.camera.rotation.z = Math.sin(this.t * 0.6) * 0.02 * k;
    if (this.hall) this.hall.rotation.z = Math.sin(this.t * 0.23) * 0.012 * k;
    // colours drift: the background warms and cools with a slow tide
    const hue = 0.6 + 0.12 * Math.sin(this.t * 0.17);
    this.scene.background = new THREE.Color().setHSL(hue, 0.35 * k, 0.03 + 0.04 * k * (0.5 + 0.5 * Math.sin(this.t * 0.31)));
    // the fitted light that is not there
    const V = this.vanish;
    if (V) {
      const away = Math.abs(Math.atan2(Math.sin(player.yaw - V.yaw0), Math.cos(player.yaw - V.yaw0))) > 1.1;
      if (!V.hidden && away) { V.hidden = true; V.slot.mesh.visible = false; V.until = this.t + 3 + Math.random() * 5; }
      if (V.hidden && this.t > V.until) { V.slot.mesh.visible = true; this.vanish = null; }
    }
    // the second lift: a see-through copy across the hall for a few seconds
    if (!this.ghost && this.t > this.nextGhost && this.lift) {
      const g = this.lift.group.clone(true);
      g.traverse((o) => { if (o.isMesh) { o.material = o.material.clone(); o.material.transparent = true; o.material.opacity = 0.35; o.material.depthWrite = false; } });
      const a = Math.random() * Math.PI * 2, r = 9 + Math.random() * 6;
      g.position.add(new THREE.Vector3(Math.cos(a) * r, 0, Math.sin(a) * r));
      this.scene.add(g); this.ghost = g; this.ghostUntil = this.t + 4 + Math.random() * 4;
    }
    if (this.ghost && this.t > this.ghostUntil) { this.scene.remove(this.ghost); this.ghost = null; this.nextGhost = this.t + 25 + Math.random() * 50 / Math.max(0.3, L); }
  }

  reset() {
    if (this.camera.fov !== this.baseFov) { this.camera.fov = this.baseFov; this.camera.updateProjectionMatrix(); }
    this.camera.rotation.z = 0;
    if (this.hall) this.hall.rotation.z = 0;
    this.scene.background = this.bg;
    if (this.vanish) { this.vanish.slot.mesh.visible = true; this.vanish = null; }
    if (this.ghost) { this.scene.remove(this.ghost); this.ghost = null; }
  }
}
