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

export function saveGame(clock, install) {
  localStorage.setItem(KEY, JSON.stringify({ night: clock.night, ...install.saveShape() }));
}
