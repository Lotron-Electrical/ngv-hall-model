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
    this.airborne = false; this.vy = 0; this.jumpQueued = false;   // the jump: 3.4 m/s up is a 0.6 m hop under 9.8 m/s2
    this.carry = null;
    this.speedScale = 1;
    // (2026-09-04) install mode inside the sim can be switched off again, so every listener bind()
    // adds is remembered here and undone by unbind(): a second toggle otherwise runs the keys and
    // the sticks through two players at once
    this.off = [];
  }

  // add a listener and remember how to take it away again
  on(target, type, fn, opts) { target.addEventListener(type, fn, opts); this.off.push(() => target.removeEventListener(type, fn, opts)); }
  unbind() { for (const f of this.off) f(); this.off = []; document.body.classList.remove('paused'); }

  // lock the pointer to the canvas. Raw (unadjusted) movement where the browser has it, so the OS
  // mouse acceleration does not bend the look; the plain lock where it does not. Chrome refuses a
  // lock for about a second after an Esc exit: that refusal lands in pointerlockerror, the pause
  // screen stays up, and the next click gets it
  lock() {
    if (this.coarse || !this.canvas.requestPointerLock) return;
    let req;
    try { req = this.canvas.requestPointerLock({ unadjustedMovement: true }); } catch (e) { req = null; }
    const plain = () => { try { const r = this.canvas.requestPointerLock(); if (r?.catch) r.catch(() => {}); } catch (e) {} };
    if (req?.catch) req.catch((err) => { if (err?.name === 'NotSupportedError') plain(); }); else if (!req) plain();
  }

  // the pause: while the pointer is free on a mouse-and-keyboard machine the game holds, the keys
  // are dropped, and #paused ("click to resume") stands over the hall
  setPaused(on) {
    on = !!on && !this.coarse && this.hadLock && document.body.classList.contains('playing');
    if (on === this.paused) return;
    this.paused = on;
    if (on && this.dropKeys) this.dropKeys();
    document.body.classList.toggle('paused', on);
  }

  bind(ui) {
    this.on(window, 'keydown', (e) => {
      if (e.code === 'KeyE') this.actionQueued = true;
      if (e.code === 'KeyF') this.dropQueued = true;
      // (Lloyd, 2026-09-05: "add spacebar jump") on the floor Space is a jump; aboard the lift it
      // stays the deck's UP. One jump at a time, from the ground only
      if (e.code === 'Space') { if (this.onLift) this.liftUp = true; else if (!e.repeat && !this.airborne) this.jumpQueued = true; }
      if (e.code === 'ShiftLeft' || e.code === 'ShiftRight') this.liftDown = true;
      this.keys.add(e.code);
    });
    this.on(window, 'keyup', (e) => {
      this.keys.delete(e.code);
      if (e.code === 'Space') this.liftUp = false;
      if (e.code === 'ShiftLeft' || e.code === 'ShiftRight') this.liftDown = false;
    });
    // THE MOUSE (Lloyd, 2026-09-04: "I had to press Esc to unlock the mouse, then I can't start
    // looking again"). The browser-FPS workflow every pointer-lock game uses: a click on the play
    // area locks the pointer, Esc (the browser's own key, it cannot be rebound) unlocks it and the
    // game PAUSES behind a "click to resume" screen, and the next click locks again. The click is
    // heard on the document, not the canvas: the install overlay covers the canvas, so a canvas
    // listener never fired after Esc. Buttons and the prompt keep their own clicks. The keys are
    // dropped on every unlock, blur and tab switch, so nothing runs on while the eye is free.
    this.coarse = matchMedia?.('(pointer: coarse)').matches;
    this.paused = false;
    this.on(document, 'click', (e) => {
      if (this.coarse || !document.body.classList.contains('playing')) return;
      if (e.target.closest?.('button, a, input, select, #prompt, #overlay, #summary')) return;
      if (document.pointerLockElement !== this.canvas) this.lock();
    });
    // the pause is for a lock LOST (Esc, alt-tab): before the first lock has been held the shift
    // runs on with the keys, and the first click on the hall captures the mouse. A browser that
    // refuses the lock outright (headless, a blocked permission) therefore never holds the game
    this.hadLock = false;
    this.on(document, 'pointerlockchange', () => { const locked = document.pointerLockElement === this.canvas; if (locked) this.hadLock = true; this.setPaused(!locked); });
    this.on(document, 'pointerlockerror', () => this.setPaused(true));
    const drop = () => { this.keys.clear(); this.liftUp = this.liftDown = false; this.move.set(0, 0); this.look.set(0, 0); };
    this.dropKeys = drop;
    this.on(window, 'blur', drop);
    this.on(document, 'visibilitychange', () => { if (document.hidden) drop(); });
    this.on(document, 'mousemove', (e) => {
      if (document.pointerLockElement !== this.canvas) return;
      this.lookBy(e.movementX * 0.0022, e.movementY * 0.0022);
    });
    if (ui.action) this.on(ui.action, 'click', () => this.actionQueued = true);
    // (Lloyd, 2026-09-04: "the messages that appear are better, can tap on them") the prompt is the button
    if (ui.prompt) this.on(ui.prompt, 'click', () => this.actionQueued = true);
    if (ui.drop) this.on(ui.drop, 'click', () => this.dropQueued = true);
    if (ui.liftUp) { this.on(ui.liftUp, 'pointerdown', (e) => { e.preventDefault(); this.liftUp = true; });
      this.on(ui.liftUp, 'pointerup', () => this.liftUp = false);
      this.on(ui.liftUp, 'pointercancel', () => this.liftUp = false); }
    if (ui.liftDown) { this.on(ui.liftDown, 'pointerdown', (e) => { e.preventDefault(); this.liftDown = true; });
      this.on(ui.liftDown, 'pointerup', () => this.liftDown = false);
      this.on(ui.liftDown, 'pointercancel', () => this.liftDown = false); }
    this.bindStick(ui.moveStick, this.move);
    this.bindStick(ui.lookStick, this.look);
  }

  bindStick(el, out) {
    const knob = el.querySelector('i');
    const active = { id: null };
    const S = { touched: false, held: false, t: 0 }; this.stk = this.stk || {}; this.stk[el.id] = S;
    // (Lloyd, 2026-09-04, twice) BOTH sticks work the same way: how far the knob sits from the
    // stick's centre is the rate. Hold the look stick over and the view keeps turning, let it
    // spring back and it stops. A drag-only look stick ("only moves exactly how far you move
    // it") was tried in between and Lloyd asked for this back. The 9 px dead zone is what stops
    // a resting thumb from drifting the view
    const set = (e) => {
      const r = el.getBoundingClientRect();
      const x = e.clientX - r.left - r.width * 0.5;
      const y = e.clientY - r.top - r.height * 0.5;
      // the knob's reach is the ring's: the free-roam ring is 80 px, so full rate at 34 px out
      const reach = Math.max(20, r.width * 0.5 - 6);
      const v = new THREE.Vector2(x, y).clampLength(0, reach);
      // (Lloyd, 2026-09-04: the view drifted left at the start) a thumb resting a few pixels off
      // the centre is not an input: nothing inside 7 px, and the rest scaled from that edge
      const len = v.length(), dead = 7;
      if (len < dead) out.set(0, 0); else { const k = (len - dead) / (reach - dead) / len; out.set(v.x * k, v.y * k); }
      knob.style.transform = `translate(${v.x}px,${v.y}px)`;
    };
    this.on(el, 'pointerdown', (e) => {
      S.touched = true; S.held = true; S.t = performance.now() / 1000;
      active.id = e.pointerId;
      el.setPointerCapture(e.pointerId);
      set(e);
    });
    this.on(el, 'pointermove', (e) => {
      if (active.id !== e.pointerId) return;
      set(e);
    });
    const end = (e) => {
      if (active.id !== e.pointerId) return;
      active.id = null;
      out.set(0, 0);
      knob.style.transform = '';
      S.held = false; S.t = performance.now() / 1000;
    };
    this.on(el, 'pointerup', end);
    this.on(el, 'pointercancel', end);
    this.on(el, 'lostpointercapture', end);
    // a release the element never hears (a gesture the browser took over, the tab hidden) must
    // still let go, or the view drifts on a phantom hold
    const letGo = () => { if (active.id === null) return; active.id = null; out.set(0, 0); knob.style.transform = ''; S.held = false; S.t = performance.now() / 1000; };
    this.on(window, 'pointerup', (e) => { if (e.target !== el && !el.contains(e.target)) return; letGo(); });
    this.on(window, 'touchend', (e) => { if (e.touches.length === 0) letGo(); }, { passive: true });
    this.on(window, 'touchcancel', letGo, { passive: true });
    this.on(window, 'blur', letGo);
    this.on(document, 'visibilitychange', () => { if (document.hidden) letGo(); });
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
    // the look stick held over: a full deflection turns 2.8 rad/s across and 1.8 rad/s up and down
    if (this.look.lengthSq() > 0) this.lookBy(this.look.x * dt * 2.8, this.look.y * dt * 1.8);
    // (2026-09-04) on the lift the deck is the floor: lift.js walks you, not this
    if (!this.onLift) {
      const forward = (this.keys.has('KeyW') ? 1 : 0) - (this.keys.has('KeyS') ? 1 : 0) - this.move.y;
      const strafe = (this.keys.has('KeyD') ? 1 : 0) - (this.keys.has('KeyA') ? 1 : 0) + this.move.x;
      const v = new THREE.Vector3(strafe, 0, -forward).clampLength(0, 1);
      v.applyAxisAngle(new THREE.Vector3(0, 1, 0), this.yaw);
      this.pos.addScaledVector(v, dt * 3.3 * this.speedScale);
      // standing still is standing still: no push, so nothing can slide you (2026-09-04)
      if (v.lengthSq() > 0) collide(this.pos, 0.32, world, this.ignore || []);
      // the jump rides on top of the walk: the floor is where the feet were when they left it
      if (this.jumpQueued) { this.jumpQueued = false; if (!this.airborne) { this.airborne = true; this.ground = this.pos.y; this.vy = 3.4; } }
      if (this.airborne) { this.vy -= 9.8 * dt; this.pos.y += this.vy * dt; if (this.pos.y <= this.ground) { this.pos.y = this.ground; this.vy = 0; this.airborne = false; } }
    } else { this.airborne = false; this.vy = 0; this.jumpQueued = false; }
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
