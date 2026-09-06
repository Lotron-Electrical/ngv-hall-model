const KEY = 'ngv-install-phase1';

export class GameClock {
  constructor(saved) {
    this.night = saved?.night || 1;
    this.minute = 17 * 60;
    this.ended = false;
    this.running = false;
    this.fittedAtStart = 0;
  }

  update(dt) {
    if (!this.running || this.ended) return;
    this.minute += dt;
    if (this.minute >= 29 * 60) this.ended = true;
  }

  timeText() {
    const m = Math.floor(this.minute) % (24 * 60);
    const h = Math.floor(m / 60);
    const mm = String(m % 60).padStart(2, '0');
    return `${String(h).padStart(2, '0')}:${mm}`;
  }

  fatigue() {
    const h = this.minute / 60;
    if (h >= 28) return 0.55;
    if (h >= 27) return 0.7;
    if (h >= 25) return 0.85;
    return 1;
  }

  fatigueText() {
    const f = this.fatigue();
    if (f > 0.98) return 'fresh';
    if (f > 0.8) return 'tired';
    if (f > 0.6) return 'worn';
    return 'wrecked';
  }

  nextNight(fittedNow) {
    this.night++;
    this.minute = 17 * 60;
    this.ended = false;
    this.running = false;
    this.fittedAtStart = fittedNow;
  }
}

export function loadSave() {
  try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch { return {}; }
}

// (Lloyd, 2026-09-06: floor protection) the path of ply sheets is part of the job, so it is part
// of the save: `sheets` is [[u, d, along], ...] in hall coordinates and `stackSheets` is what is
// left on each pallet of ply. `world` is optional so an older caller still saves the lights
export function saveGame(clock, install, world, items) {
  const extra = {};
  if (world && world.sheets) extra.sheets = world.sheets.map((s) => [+s.u.toFixed(3), +s.d.toFixed(3), s.along]);
  if (items && items.stacks) extra.stackSheets = items.stacks.map((s) => s.sheets);
  localStorage.setItem(KEY, JSON.stringify({ night: clock.night, ...install.saveShape(), ...extra }));
}
