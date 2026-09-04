// SOUND (phase 4, 2026-09-04): everything synthesised on a WebAudio context, nothing to load.
// The lift hums while it moves, boxes thud, wrap crinkles, a fit clicks, 04:30 chimes the
// pack-up and 05:00 rings the night out. In the small hours the hum detunes with the fatigue
// level (fx.js), which is the one place the sound is allowed to lie to you.
export class Sound {
  constructor() { this.ctx = null; this.hum = null; this.humGain = null; this.warned = false; this.rang = false; }
  wake() {
    if (this.ctx) { if (this.ctx.state !== 'running') this.ctx.resume().catch(() => {}); return; }
    const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
    this.ctx = new AC();
    this.master = this.ctx.createGain(); this.master.gain.value = 0.5; this.master.connect(this.ctx.destination);
  }
  // a short enveloped tone
  tone(freq, dur, type = 'sine', peak = 0.08, slide = 0) {
    if (!this.ctx) return; const c = this.ctx, t = c.currentTime;
    const o = c.createOscillator(), g = c.createGain(); o.type = type; o.frequency.setValueAtTime(freq, t);
    if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(20, freq + slide), t + dur);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(peak, t + 0.01); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g).connect(this.master); o.start(t); o.stop(t + dur + 0.05);
  }
  // a burst of filtered noise: crinkle, thud, scrape
  noise(dur, freq, q = 1, peak = 0.12) {
    if (!this.ctx) return; const c = this.ctx, t = c.currentTime, n = Math.floor(c.sampleRate * dur);
    const buf = c.createBuffer(1, n, c.sampleRate), d = buf.getChannelData(0); for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n);
    const s = c.createBufferSource(); s.buffer = buf; const f = c.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = freq; f.Q.value = q;
    const g = c.createGain(); g.gain.value = peak; s.connect(f).connect(g).connect(this.master); s.start(t);
  }
  fit() { this.tone(1760, 0.06, 'square', 0.05); this.tone(880, 0.09, 'sine', 0.05); }
  thud() { this.noise(0.12, 140, 0.8, 0.25); this.tone(70, 0.12, 'sine', 0.12, -30); }
  crinkle() { for (let i = 0; i < 4; i++) setTimeout(() => this.noise(0.05, 3500 + Math.random() * 2500, 2, 0.08), i * 45); }
  jack() { this.noise(0.25, 400, 1.5, 0.08); }
  door() { this.tone(90, 0.5, 'triangle', 0.03, 25); }
  chime() { this.tone(880, 0.4, 'sine', 0.1); setTimeout(() => this.tone(1174, 0.5, 'sine', 0.1), 250); }
  bell() { for (let i = 0; i < 3; i++) setTimeout(() => { this.tone(660, 0.9, 'sine', 0.12); this.tone(1320, 0.6, 'sine', 0.04); }, i * 600); }
  // the lift's motor: a low saw that rises and falls with movement
  motor(on, fxLevel = 0) {
    if (!this.ctx) return; const c = this.ctx;
    if (!this.hum) { this.hum = c.createOscillator(); this.hum.type = 'sawtooth'; this.hum.frequency.value = 55;
      const f = c.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 320; this.humGain = c.createGain(); this.humGain.gain.value = 0;
      this.hum.connect(f).connect(this.humGain).connect(this.master); this.hum.start(); }
    this.humGain.gain.setTargetAtTime(on ? 0.09 : 0, c.currentTime, 0.08);
    this.hum.frequency.setTargetAtTime(55 + (on ? 8 : 0) + Math.sin(performance.now() / 700) * 6 * fxLevel, c.currentTime, 0.1);
  }
  // the clock's cues, once each per night
  clock(clockMinute) {
    if (!this.warned && clockMinute >= 28.5 * 60) { this.warned = true; this.chime(); }
    if (!this.rang && clockMinute >= 29 * 60) { this.rang = true; this.bell(); }
  }
  nextNight() { this.warned = false; this.rang = false; }
  // (2026-09-04) install mode can be switched off inside the sim, so the game's own context has
  // to go with it: a left-open AudioContext keeps the motor hum's oscillator running for the
  // life of the page and a second toggle would start another one on top of it
  close() {
    if (this.hum) { try { this.hum.stop(); } catch (e) {} this.hum = null; this.humGain = null; }
    if (this.ctx) { try { this.ctx.close(); } catch (e) {} this.ctx = null; this.master = null; }
  }
}
