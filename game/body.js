// STAMINA AND FATIGUE (Lloyd, 2026-09-04: "it should also be a stamina and fatigue system").
// Two numbers, 0 to 100.
//  STAMINA is the short term: it drains while you carry, jack a pallet or drive the lift, and
//   comes back when you ease off (fastest standing still). Out of puff you crawl and cannot pick
//   up a box or lift a pallet until you have rested a moment.
//  FATIGUE is the night: it climbs with the clock (slowly to 01:00, then faster, worst in the
//   last two hours) and with every bit of stamina spent. Fatigue lowers the stamina ceiling and
//   slows recovery, slows everything, and past 70 the small hours start (fx.js reads it).
export class Body {
  constructor(saved) {
    this.stamina = 100;
    this.fatigue = 0;
    this.max = 100;
    this.rested = 0;        // seconds without effort, for the recovery ramp
  }

  // what the body is doing this frame: load = 0 idle, 1 walking light, 2 carrying, 3 jacking a pallet
  update(dt, clock, load, moving) {
    const h = clock.minute / 60;
    // the clock's own toll: 2/h to 01:00, 6/h to 03:00, 12/h to 04:00, 20/h to 05:00
    const perHour = h < 25 ? 2 : h < 27 ? 6 : h < 28 ? 12 : 20;
    this.fatigue += perHour * dt / 60;              // one game hour is one real minute
    // effort drains stamina, and a tenth of that lands on fatigue for good
    const drain = !moving ? 0 : load >= 3 ? 7 : load >= 2 ? 4 : load >= 1 ? 1.2 : 0;   // a box the length of the hall (12 s) costs about half the tank
    if (drain > 0) { this.stamina -= drain * dt; this.fatigue += drain * dt * 0.1; this.rested = 0; }
    else { this.rested += dt; const rate = (moving ? 4 : 9) * (1 - this.fatigue / 100 * 0.6) * Math.min(1, 0.3 + this.rested / 3); this.stamina += rate * dt; }
    this.fatigue = Math.min(100, this.fatigue);
    this.max = 100 - this.fatigue * 0.6;              // dead tired, the tank is 40
    this.stamina = Math.max(0, Math.min(this.max, this.stamina));
  }

  // how fast the body goes: fatigue takes up to 45 percent, being out of puff takes half again
  speedScale() {
    const f = 1 - this.fatigue / 100 * 0.45;
    const s = this.stamina < 15 ? 0.5 + 0.5 * (this.stamina / 15) : 1;
    return f * s;
  }

  canLift(cost) { return this.stamina >= cost; }

  text() {
    const f = this.fatigue;
    return f < 20 ? 'fresh' : f < 45 ? 'tiring' : f < 70 ? 'worn' : f < 90 ? 'wrecked' : 'gone';
  }

  nextNight() { this.stamina = 100; this.fatigue = 0; this.max = 100; this.rested = 0; }
}
