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
    ui.action.addEventListener('click', () => this.actionQueued = true);
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
    const set = (e) => {
      const r = el.getBoundingClientRect();
      const x = e.clientX - r.left - r.width * 0.5;
      const y = e.clientY - r.top - r.height * 0.5;
      const v = new THREE.Vector2(x, y).clampLength(0, 42);
      out.set(v.x / 42, v.y / 42);
      knob.style.transform = `translate(${v.x}px,${v.y}px)`;
    };
    el.addEventListener('pointerdown', (e) => {
      active.id = e.pointerId;
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
      out.set(0, 0);
      knob.style.transform = '';
    };
    el.addEventListener('pointerup', end);
    el.addEventListener('pointercancel', end);
  }

  lookBy(dx, dy) {
    this.yaw -= dx;
    this.pitch = THREE.MathUtils.clamp(this.pitch - dy, -1.35, 1.35);
  }

  update(dt, world, collide) {
    // the look stick turns the view for as long as it is held, not only while the thumb moves
    if (this.look.lengthSq() > 0) this.lookBy(this.look.x * dt * 2.4, this.look.y * dt * 1.6);
    const forward = (this.keys.has('KeyW') ? 1 : 0) - (this.keys.has('KeyS') ? 1 : 0) - this.move.y;
    const strafe = (this.keys.has('KeyD') ? 1 : 0) - (this.keys.has('KeyA') ? 1 : 0) + this.move.x;
    const v = new THREE.Vector3(strafe, 0, -forward).clampLength(0, 1);
    v.applyAxisAngle(new THREE.Vector3(0, 1, 0), this.yaw);
    this.pos.addScaledVector(v, dt * 3.3 * this.speedScale);
    collide(this.pos, 0.32, world);
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
