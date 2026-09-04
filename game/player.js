import * as THREE from 'three';

export class Player {
  constructor(camera, canvas) {
    this.camera = camera;
    this.canvas = canvas;
    this.pos = new THREE.Vector3();
    this.yaw = 0;
    this.pitch = 0;
    this.eye = 1.68;
    this.keys = new Set();
    this.move = new THREE.Vector2();
    this.look = new THREE.Vector2();
    this.lookRate = new THREE.Vector2();   // held-over look stick: turn per second
    this.actionQueued = false;
    this.dropQueued = false;
    this.liftUp = false;
    this.liftDown = false;
    this.onLift = false;
    this.carry = null;
    this.speedScale = 1;
  }

  bind(ui) {
    addEventListener('keydown', (e) => {
      if (e.code === 'KeyE') this.actionQueued = true;
      if (e.code === 'KeyF') this.dropQueued = true;
      if (e.code === 'Space') this.liftUp = true;
      if (e.code === 'ShiftLeft' || e.code === 'ShiftRight') this.liftDown = true;
      this.keys.add(e.code);
    });
    addEventListener('keyup', (e) => {
      this.keys.delete(e.code);
      if (e.code === 'Space') this.liftUp = false;
      if (e.code === 'ShiftLeft' || e.code === 'ShiftRight') this.liftDown = false;
    });
    const coarse = matchMedia?.('(pointer: coarse)').matches;
    this.canvas.addEventListener('click', () => {
      if (coarse || !document.body.classList.contains('playing')) return;
      const req = this.canvas.requestPointerLock?.();
      if (req?.catch) req.catch(() => {});
    });
    document.addEventListener('mousemove', (e) => {
      if (document.pointerLockElement !== this.canvas) return;
      this.lookBy(e.movementX * 0.0022, e.movementY * 0.0022);
    });
    ui.action?.addEventListener('click', () => this.actionQueued = true);
    // (Lloyd, 2026-09-04: "the messages that appear are better, can tap on them") the prompt is the button
    ui.prompt?.addEventListener('click', () => this.actionQueued = true);
    ui.drop?.addEventListener('click', () => this.dropQueued = true);
    ui.liftUp?.addEventListener('pointerdown', (e) => { e.preventDefault(); this.liftUp = true; });
    ui.liftUp?.addEventListener('pointerup', () => this.liftUp = false);
    ui.liftUp?.addEventListener('pointercancel', () => this.liftUp = false);
    ui.liftDown?.addEventListener('pointerdown', (e) => { e.preventDefault(); this.liftDown = true; });
    ui.liftDown?.addEventListener('pointerup', () => this.liftDown = false);
    ui.liftDown?.addEventListener('pointercancel', () => this.liftDown = false);
    this.bindStick(ui.moveStick, this.move);
    this.bindStick(ui.lookStick, this.look, true);
  }

  bindStick(el, out, isLook = false) {
    const knob = el.querySelector('i');
    const active = { id: null };
    const S = { touched: false, held: false, t: 0 }; this.stk = this.stk || {}; this.stk[el.id] = S;
    // (Lloyd, 2026-09-04: the view kept drifting) the LOOK stick is a DRAG like free roam's: the
    // view turns by how far the thumb has moved since the last event, never by where it rests.
    // A thumb parked on the stick does nothing; the knob leans with the drag and springs back
    const set = (e) => {
      if (isLook) {
        if (active.last) this.lookBy((e.clientX - active.last.x) * 0.0062, (e.clientY - active.last.y) * 0.0048);
        active.last = { x: e.clientX, y: e.clientY };
        // (Lloyd, 2026-09-04: "hold a direction and keep turning, not having to flick") held
        // further than 26 px from where the thumb LANDED it also turns at a rate; measured from
        // the landing point, not the stick's centre, so a thumb resting anywhere never turns
        if (!active.down) active.down = { x: e.clientX, y: e.clientY };
        const ox = e.clientX - active.down.x, oy = e.clientY - active.down.y, len = Math.hypot(ox, oy), past = Math.max(0, len - 26);
        if (past > 0) { const k = Math.min(1, past / 40) / len; this.lookRate.set(ox * k, oy * k); } else this.lookRate.set(0, 0);
        const r = el.getBoundingClientRect();
        const v = new THREE.Vector2(e.clientX - r.left - r.width * 0.5, e.clientY - r.top - r.height * 0.5).clampLength(0, 42);
        knob.style.transform = `translate(${v.x}px,${v.y}px)`;
        return;
      }
      const r = el.getBoundingClientRect();
      const x = e.clientX - r.left - r.width * 0.5;
      const y = e.clientY - r.top - r.height * 0.5;
      const v = new THREE.Vector2(x, y).clampLength(0, 42);
      // (Lloyd, 2026-09-04: the view drifted left at the start) a thumb resting a few pixels off
      // the centre is not an input: nothing inside 9 px, and the rest scaled from that edge
      const len = v.length(), dead = 9;
      if (len < dead) out.set(0, 0); else { const k = (len - dead) / (42 - dead) / len; out.set(v.x * k, v.y * k); }
      knob.style.transform = `translate(${v.x}px,${v.y}px)`;
    };
    el.addEventListener('pointerdown', (e) => {
      S.touched = true; S.held = true; S.t = performance.now() / 1000;
      active.id = e.pointerId; active.last = null; active.down = null; this.lookRate.set(0, 0);
      el.setPointerCapture(e.pointerId);
      set(e);
    });
    el.addEventListener('pointermove', (e) => {
      if (active.id !== e.pointerId) return;
      set(e);
    });
    const end = (e) => {
      if (active.id !== e.pointerId) return;
      active.id = null;
      out.set(0, 0); if (isLook) this.lookRate.set(0, 0);
      knob.style.transform = '';
      S.held = false; S.t = performance.now() / 1000;
    };
    el.addEventListener('pointerup', end);
    el.addEventListener('pointercancel', end);
    el.addEventListener('lostpointercapture', end);
    // a release the element never hears (a gesture the browser took over, the tab hidden) must
    // still let go, or the view drifts on a phantom hold
    const letGo = () => { if (active.id === null) return; active.id = null; out.set(0, 0); if (isLook) this.lookRate.set(0, 0); knob.style.transform = ''; S.held = false; S.t = performance.now() / 1000; };
    addEventListener('pointerup', (e) => { if (e.target !== el && !el.contains(e.target)) return; letGo(); });
    addEventListener('touchend', (e) => { if (e.touches.length === 0) letGo(); }, { passive: true });
    addEventListener('touchcancel', letGo, { passive: true });
    addEventListener('blur', letGo);
    document.addEventListener('visibilitychange', () => { if (document.hidden) letGo(); });
  }

  lookBy(dx, dy) {
    this.yaw -= dx;
    this.pitch = THREE.MathUtils.clamp(this.pitch - dy, -1.35, 1.35);
  }

  // the viewer's rule (sticksSync in index.html): a stick shows until its first touch, then while
  // held and for a second after
  sticksSync() {
    const now = performance.now() / 1000;
    for (const id in this.stk || {}) { const S = this.stk[id]; document.getElementById(id).classList.toggle('show', !S.touched || S.held || now - S.t < 1.0); }
  }

  update(dt, world, collide) {
    this.sticksSync();
    if (this.lookRate.lengthSq() > 0) this.lookBy(this.lookRate.x * dt * 2.4, this.lookRate.y * dt * 1.6);
    // (2026-09-04) on the lift the deck is the floor: lift.js walks you, not this
    if (!this.onLift) {
      const forward = (this.keys.has('KeyW') ? 1 : 0) - (this.keys.has('KeyS') ? 1 : 0) - this.move.y;
      const strafe = (this.keys.has('KeyD') ? 1 : 0) - (this.keys.has('KeyA') ? 1 : 0) + this.move.x;
      const v = new THREE.Vector3(strafe, 0, -forward).clampLength(0, 1);
      v.applyAxisAngle(new THREE.Vector3(0, 1, 0), this.yaw);
      this.pos.addScaledVector(v, dt * 3.3 * this.speedScale);
      // standing still is standing still: no push, so nothing can slide you (2026-09-04)
      if (v.lengthSq() > 0) collide(this.pos, 0.32, world, this.ignore || []);
    }
    this.camera.position.set(this.pos.x, this.pos.y + this.eye, this.pos.z);
    this.camera.rotation.set(this.pitch, this.yaw, 0, 'YXZ');
  }

  takeAction() {
    const v = this.actionQueued;
    this.actionQueued = false;
    return v;
  }

  takeDrop() {
    const v = this.dropQueued;
    this.dropQueued = false;
    return v;
  }
}
