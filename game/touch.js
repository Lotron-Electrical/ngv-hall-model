// (Lloyd, 2026-09-07: "we need to improve the controls on phone", "No big buttons that will take up
// screen space. Do some research online on phone UI best practices") THE PHONE SCHEME. Built on the
// research (PUBG / CoD Mobile / Genshin / Roblox / Fortnite mobile, Material and Apple touch
// targets, the thumb-zone field study): a FLOATING move stick under the left thumb, FREE LOOK by
// dragging the rest of the screen, and a TAP ON THE THING ITSELF instead of an action button.
// Nothing on screen is permanent except what the moment needs.
//
// The layout the sim used before this: two fixed 80 px rings, an UP / DOWN / FAST column and a
// DROP button, all up all the time, on a 412 px screen. That is the thing being deleted.
import * as THREE from 'three';

const KEY = 'ngv.ctl.';
// the settings a player can change, and what they are when nobody has
export const DEFAULTS = { look: 'drag', sensH: 1, sensV: 1, invY: 0, stick: 'M', autorun: 1, lefty: 0, opacity: 0.7 };
// (research 1) the ring the thumb pulls against: 55-70 px is the band, so S / M / L sit around it
export const RADIUS = { S: 50, M: 60, L: 72 };
// (research 3) SCALED RADIAL dead zone: an axial one snaps to eight directions, a plain radial one
// jumps at its edge. Touch does not drift, so 0.10 of the ring is enough
const DEAD = 0.10;
// (research 2) 1 px of drag is a fixed angle, not a rate: rate on a drag surface reads as drift
const DEG_H = 0.22, DEG_V = 0.18;
// the look curve. `sign(d) * |d/REF|^0.15 * d` is mild: at REF px in a frame the gain is exactly 1,
// so the numbers above are the honest degrees-per-pixel for an ordinary drag, and a fast flick
// gets a little more. Without the reference the same exponent would make the answer depend on how
// many events the browser split the drag into
const CURVE = 0.15, REF = 10;
const TOPSTRIP = 96;      // the clock chips and the two header buttons: no stick lands under them
const MOVE_FRAC = 0.40;   // (research 1) the move stick owns the left 40 % of the width
// (skeptic 10, 2026-09-07) a tap is a tap, not the start of a look. 250 ms was too short for a
// deliberate press on a small target and a slow press did nothing at all; the 10 px gate is what
// actually separates a tap from a look, so the clock may be generous
const TAP_PX = 10, TAP_MS = 500;
// the four inventory slots run along the bottom centre now, so the resting ghost parks above them
const INVBAR = 62;
const IDLE = 3.0;         // (research 9) controls fade to a third after three seconds of nothing

export function loadCtl() {
  const o = { ...DEFAULTS };
  try { for (const k in DEFAULTS) { const v = localStorage.getItem(KEY + k); if (v !== null) o[k] = typeof DEFAULTS[k] === 'number' ? +v : v; } } catch (e) {}
  return o;
}
export function saveCtl(k, v) { try { localStorage.setItem(KEY + k, String(v)); } catch (e) {} }

export class TouchControls {
  // els: { zone, move, look, deck, root, onTap, onLetGo }
  constructor(player, els) {
    this.p = player; this.els = els;
    this.ctl = loadCtl();
    this.off = [];
    this.move = null;        // the finger on the move stick { id, cx, cy }
    this.look = null;        // the finger looking { id, x, y, t, moved }
    this.deckId = null;
    this.run = false; this.rimT = 0;
    // (skeptic 13) the clock starts NOW, not at zero: with zero the idle fade was already true on
    // the first frame and the one hint about where the stick lives was drawn at a third strength
    // before the player had touched anything
    this.lastTouch = performance.now() / 1000;
    this.bind();
    this.apply();
  }

  on(t, type, fn, opts) { t.addEventListener(type, fn, opts); this.off.push(() => t.removeEventListener(type, fn, opts)); }
  destroy() { for (const f of this.off) f(); this.off = []; this.p.move.set(0, 0); this.p.look.set(0, 0); this.p.touchRun = false; this.p.liftRate = 0; }

  radius() { return RADIUS[this.ctl.stick] || RADIUS.M; }
  // the play layer's own box, not the window's: the shift runs inside a stage that is 44 px short
  // of the page's bottom, and in a crew room or an embed it is somewhere else again
  box() {
    const r = this.els.zone.getBoundingClientRect();
    // the top strip is whatever the header actually measures (the clock chips wrap to three rows on
    // a narrow phone), never a number written for one row
    const h = this.els.head ? this.els.head.getBoundingClientRect() : null;
    const top = h && h.height ? Math.max(r.top, h.bottom + 8) : r.top + TOPSTRIP;
    return { l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height, top };
  }
  // the move stick's side of the screen. Left-handed mirrors it, and the corner cluster with it
  inMoveZone(x, y) {
    const B = this.box();
    if (y < B.top) return false;
    return this.ctl.lefty ? x > B.r - B.w * MOVE_FRAC : x < B.l + B.w * MOVE_FRAC;
  }

  // settings changed (or the screen turned): the classes, the opacity and the resting ghost
  apply() {
    const r = this.els.root, c = this.ctl;
    r.style.setProperty('--ctlop', String(c.opacity));
    r.style.setProperty('--ctlr', this.radius() + 'px');
    document.body.classList.toggle('lefty', !!+c.lefty);
    document.body.classList.toggle('lookstick', c.look === 'stick');
    // the resting ghost sits where a right thumb naturally falls, until the first touch moves it
    if (!this.touched) this.park();
  }

  park() {
    const B = this.box(), R = this.radius();
    const x = this.ctl.lefty ? B.r - (R + 34) : B.l + R + 34;
    // (skeptic 3b) the inventory strip sits along the bottom centre now: the ghost parks a slot's
    // height higher so the hint and the slots never draw through each other
    this.place(this.els.move, x, B.b - (R + 34 + INVBAR));
    this.els.move.classList.add('show', 'ghost');
  }

  place(el, x, y) {
    const R = this.radius(), r = this.els.zone.getBoundingClientRect();
    el.style.left = (x - R - r.left) + 'px'; el.style.top = (y - R - r.top) + 'px';
    el.style.width = el.style.height = (R * 2) + 'px';
  }

  knob(el, dx, dy) { const i = el.querySelector('i'); if (i) i.style.transform = `translate(${dx.toFixed(1)}px,${dy.toFixed(1)}px)`; }

  bind() {
    const Z = this.els.zone;
    this.on(Z, 'contextmenu', (e) => e.preventDefault());
    this.on(Z, 'pointerdown', (e) => this.down(e));
    this.on(Z, 'pointermove', (e) => this.moveEv(e));
    const end = (e) => this.up(e);
    this.on(Z, 'pointerup', end);
    this.on(Z, 'pointercancel', end);
    this.on(Z, 'lostpointercapture', end);
    // the deck's mini-stick: one axis, and its magnitude is the speed, which is what killed the
    // FAST button (research 10)
    const D = this.els.deck;
    if (D) {
      this.on(D, 'pointerdown', (e) => { e.preventDefault(); this.deckId = e.pointerId; D.setPointerCapture(e.pointerId); this.deckAt = e.clientY; this.deckSet(e); });
      this.on(D, 'pointermove', (e) => { if (this.deckId === e.pointerId) this.deckSet(e); });
      const dend = (e) => { if (this.deckId !== e.pointerId) return; this.deckId = null; this.p.liftRate = 0; this.knob(D, 0, 0); };
      this.on(D, 'pointerup', dend); this.on(D, 'pointercancel', dend); this.on(D, 'lostpointercapture', dend);
    }
    this.on(window, 'blur', () => this.letGo());
    this.on(document, 'visibilitychange', () => { if (document.hidden) this.letGo(); });
    this.on(window, 'resize', () => { if (!this.move) this.park(); });
  }

  deckSet(e) {
    const R = 56, dy = THREE.MathUtils.clamp(e.clientY - this.deckAt, -R, R);
    const mag = Math.abs(dy) / R, out = mag < DEAD ? 0 : ((mag - DEAD) / (1 - DEAD)) * -Math.sign(dy);
    this.p.liftRate = out;
    this.knob(this.els.deck, 0, dy * 0.55);
    this.lastTouch = performance.now() / 1000;
  }

  letGo() {
    if (this.move) { this.move = null; this.p.move.set(0, 0); this.knob(this.els.move, 0, 0); this.els.move.classList.remove('held'); }
    this.look = null; this.p.look.set(0, 0); this.p.touchRun = this.run = false;
    if (this.els.look) { this.els.look.classList.remove('show', 'held'); this.knob(this.els.look, 0, 0); }
    if (this.deckId !== null) { this.deckId = null; this.p.liftRate = 0; this.knob(this.els.deck, 0, 0); }
  }

  down(e) {
    if (document.body.classList.contains('sheetOpen') || document.body.classList.contains('panelOpen')
      || document.body.classList.contains('halted')) return;
    this.lastTouch = performance.now() / 1000; this.touched = true;
    const Z = this.els.zone;
    if (this.inMoveZone(e.clientX, e.clientY)) {
      // (skeptic 11) the stick already has a thumb: a SECOND finger on the move side is a palm or a
      // grip, not a look. It used to fall through to the look branch and drift the view
      if (this.move) { e.preventDefault(); return; }
      // (research 1) the base appears WHERE THE THUMB LANDS -- no hunting for a fixed ring.
      // (skeptic 5) the CENTRE IS THE THUMB, always: the ring is only DRAWN pulled inside the glass.
      // Storing the pulled-in centre meant a thumb landing near an edge started 60 px deflected and
      // sprinted off on the first pixel of jitter. The vector at touch-down is now always zero
      const R = this.radius(), B = this.box();
      const dx = THREE.MathUtils.clamp(e.clientX, B.l + R + 6, B.r - R - 6);
      const dy = THREE.MathUtils.clamp(e.clientY, B.top + R + 6, B.b - R - 6);
      this.move = { id: e.pointerId, cx: e.clientX, cy: e.clientY };
      this.place(this.els.move, dx, dy);
      this.els.move.classList.add('show', 'held'); this.els.move.classList.remove('ghost');
      this.knob(this.els.move, 0, 0);
      this.p.move.set(0, 0); this.mag = 0; this.rimT = 0;
      try { Z.setPointerCapture(e.pointerId); } catch (err) {}
      e.preventDefault();
      return;
    }
    if (this.look) return;                       // one looking thumb; a third finger is ignored
    this.look = { id: e.pointerId, x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY, t: performance.now(), moved: 0 };
    if (this.ctl.look === 'stick') {
      // (Lloyd, 2026-09-04, twice: "hold a direction and keep turning") the option: today's rate
      // stick, floating where the thumb lands. The research says a drag surface must be positional,
      // so this is not the default any more
      const R = this.radius(), B = this.box();
      this.look.cx = THREE.MathUtils.clamp(e.clientX, B.l + R + 6, B.r - R - 6);
      this.look.cy = THREE.MathUtils.clamp(e.clientY, B.top + R + 6, B.b - R - 6);
      this.place(this.els.look, this.look.cx, this.look.cy);
      this.els.look.classList.add('show', 'held');
      this.knob(this.els.look, 0, 0);
    }
    try { Z.setPointerCapture(e.pointerId); } catch (err) {}
    e.preventDefault();
  }

  moveEv(e) {
    this.lastTouch = performance.now() / 1000;
    if (this.move && e.pointerId === this.move.id) {
      const R = this.radius();
      const v = new THREE.Vector2(e.clientX - this.move.cx, e.clientY - this.move.cy);
      // the thumb may drag PAST the ring: the output clamps and the stick keeps the finger, so a
      // long push never needs a re-grab (research 1)
      const knob = v.clone().clampLength(0, R);
      const mag = Math.min(1, v.length() / R);
      const out = mag < DEAD ? 0 : (mag - DEAD) / (1 - DEAD);
      const dir = v.lengthSq() > 0 ? v.clone().normalize() : v;
      this.p.move.set(dir.x * out, dir.y * out);
      this.knob(this.els.move, knob.x, knob.y);
      this.mag = mag;
      return;
    }
    if (this.look && e.pointerId === this.look.id) {
      const dx = e.clientX - this.look.x, dy = e.clientY - this.look.y;
      this.look.x = e.clientX; this.look.y = e.clientY;
      this.look.moved = Math.max(this.look.moved, Math.hypot(e.clientX - this.look.x0, e.clientY - this.look.y0));
      if (this.ctl.look === 'stick') {
        const R = this.radius();
        const v = new THREE.Vector2(e.clientX - this.look.cx, e.clientY - this.look.cy);
        const knob = v.clone().clampLength(0, R);
        const mag = Math.min(1, v.length() / R);
        const out = mag < DEAD ? 0 : (mag - DEAD) / (1 - DEAD);
        const dir = v.lengthSq() > 0 ? v.clone().normalize() : v;
        this.p.look.set(dir.x * out, dir.y * out);
        this.knob(this.els.look, knob.x, knob.y);
        return;
      }
      this.turn(dx, dy);
    }
  }

  // POSITIONAL look: this many pixels is this many degrees, every time
  turn(dx, dy) {
    const c = this.ctl;
    // the gain is capped: a flick, or one huge synthetic event, must not multiply itself away
    const bend = (d) => Math.sign(d) * Math.abs(d) * Math.min(2, Math.pow(Math.max(Math.abs(d), 0.001) / REF, CURVE));
    const h = bend(dx) * DEG_H * c.sensH * Math.PI / 180;
    const v = bend(dy) * DEG_V * c.sensV * Math.PI / 180 * (+c.invY ? -1 : 1);
    this.p.lookBy(h, v);
  }

  up(e) {
    if (this.move && e.pointerId === this.move.id) {
      this.move = null; this.mag = 0; this.rimT = 0;
      this.p.move.set(0, 0); this.p.touchRun = this.run = false;
      this.knob(this.els.move, 0, 0);
      this.els.move.classList.remove('held', 'show');   // the base hides on release (research 1)
      return;
    }
    if (this.look && e.pointerId === this.look.id) {
      const L = this.look; this.look = null;
      this.p.look.set(0, 0);
      if (this.els.look) { this.els.look.classList.remove('show', 'held'); this.knob(this.els.look, 0, 0); }
      // (research 6, Fortnite mobile's "In World") a tap is an ACT on whatever is under the finger;
      // anything longer or further was a look, and looking does not press things
      if (L.moved < TAP_PX && performance.now() - L.t < TAP_MS && this.els.onTap) {
        if (this.els.onTap(L.x0, L.y0)) this.buzz();
      }
    }
  }

  // (research 13) Android only, and only after the page has been touched once, which by here it has
  buzz() { try { if (navigator.vibrate) navigator.vibrate(15); } catch (e) {} }

  update(dt) {
    // the resting ghost follows the layer: the controls are built while #installUi is still
    // display:none (every rect reads zero), and the phone turns under them afterwards
    if (!this.touched && !this.move) {
      const B = this.box();
      if (B.w !== this.pw || B.h !== this.ph || B.b !== this.pb) { this.pw = B.w; this.ph = B.h; this.pb = B.b; if (B.w) this.park(); }
    }
    // (research 5) RUN WITHOUT A BUTTON: hold the stick at the rim and it latches, and it stays
    // latched until the thumb comes back inside a third of the ring
    if (this.move && +this.ctl.autorun) {
      if (this.mag > 0.85) { this.rimT += dt; if (this.rimT > 0.4) this.run = true; } else this.rimT = 0;
      if (this.run && this.mag < 0.3) this.run = false;
    } else if (!this.move) this.run = false;
    this.p.touchRun = this.run;
    this.els.move.classList.toggle('run', this.run);
    // (research 9) idle controls fade back to about a third and come up again on contact
    const idle = performance.now() / 1000 - this.lastTouch > IDLE;
    document.body.classList.toggle('ctlIdle', idle);
  }
}
