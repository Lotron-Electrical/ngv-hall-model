#!/usr/bin/env node
// The one button. Double-click tools/live-preview.cmd (or run this file with node) and the live
// loop stands itself up: bridge started silently, page served over http (https cannot open
// ws://localhost), browser opened already connected. The human's whole job is the three steps
// this prints - install ELM 2026, open the show file, turn on a pattern.
//
// Same-machine rule, measured 2026-08-31: ELM's Art-Net cannot reach a local bridge at all (it
// sends FROM its own :6454 bind and Windows drops cross-address self-unicast at ARP), so the show
// file's live-preview stage is sACN on multicast, which loops back to local group members.
//
//     node tools/live-preview.js [--ws 9930] [--http 8877] [--fps 20] [--universes 1-608] [--no-open]
'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn } = require('child_process');

const args = Object.fromEntries(process.argv.slice(2).map((a, i, all) => a.startsWith('--') ? [a.slice(2), (all[i + 1] === undefined || all[i + 1].startsWith('--')) ? true : all[i + 1]] : []).filter(x => x.length));
const WS = +(args.ws || 9930), HTTP = +(args.http || 8877);
const FPS = +(args.fps || 40), UNIVERSES = String(args.universes || '1-608');
const ROOT = path.join(__dirname, '..');
const PAGE = `http://127.0.0.1:${HTTP}/index.html?connect=1&ws=localhost:${WS}`;
const ELM_DOWNLOAD = 'https://cdn.enttec.com/elm/releases/ELM-Preview-win-x64-preview-Setup.exe';

const get = (port, p) => new Promise(res => {
  const r = http.get({ host: '127.0.0.1', port, path: p || '/', timeout: 1200 }, x => {
    let b = ''; x.on('data', d => b += d); x.on('end', () => res(b));
  });
  r.on('error', () => res(null)); r.on('timeout', () => { r.destroy(); res(null); });
});
const sleep = ms => new Promise(r => setTimeout(r, ms));
const quiet = (file, argv) => { // detached, no console window, logged to temp
  const fd = fs.openSync(path.join(os.tmpdir(), 'ngv-' + path.basename(file, '.js') + '.log'), 'a');
  spawn(process.execPath, [file, ...argv], { detached: true, windowsHide: true, stdio: ['ignore', fd, fd], cwd: ROOT }).unref();
};

// ELM 2026 Preview is a silent Velopack installer that launches itself when done, so the button
// can install it too. The show file rides beside this script (or in the repo root / Downloads).
const ELM_EXE = path.join(process.env.LOCALAPPDATA || '', 'ELM-Preview', 'current', 'ELM.exe');
const showFile = [path.join(__dirname, 'ngv-gandel-hall.elm'), path.join(ROOT, 'ngv-gandel-hall.elm'),
  path.join(os.homedir(), 'Downloads', 'ngv-gandel-hall.elm')].find(f => fs.existsSync(f));

function download(url, to) { // follow one redirect, print progress dots
  return new Promise((resolve, reject) => {
    require('https').get(url, r => {
      if (r.statusCode >= 300 && r.statusCode < 400 && r.headers.location) { r.resume(); return resolve(download(r.headers.location, to)); }
      if (r.statusCode !== 200) { r.resume(); return reject(new Error('HTTP ' + r.statusCode)); }
      const total = +r.headers['content-length'] || 0; let got = 0, dots = 0;
      const f = fs.createWriteStream(to);
      r.on('data', d => { got += d.length; const want = total ? Math.floor(got / total * 30) : Math.floor(got / 8e6); while (dots < want) { process.stdout.write('.'); dots++; } });
      r.pipe(f); f.on('finish', () => f.close(() => { process.stdout.write('\n'); resolve(); })); f.on('error', reject);
    }).on('error', reject);
  });
}

async function ensureElm() {
  if (fs.existsSync(ELM_EXE)) return true;
  console.log('  ELM 2026 is not installed - downloading it from ENTTEC (about 190 MB)');
  const setup = path.join(os.tmpdir(), 'ELM-Preview-Setup.exe');
  try { await download(ELM_DOWNLOAD, setup); } catch (e) { console.log('  download failed (' + e.message + ') - get it yourself: ' + ELM_DOWNLOAD); return false; }
  console.log('  installing (silent - ELM opens itself when done)');
  spawn(setup, [], { detached: true, windowsHide: true, stdio: 'ignore' }).unref();
  for (let i = 0; i < 120 && !fs.existsSync(ELM_EXE); i++) await sleep(2000);
  return fs.existsSync(ELM_EXE);
}

(async () => {
  console.log('');
  console.log('  NGV Gandel Hall - live preview');
  console.log('  ------------------------------');

  // ELM: install if missing, open the show file if ELM is not already running
  const haveElm = await ensureElm();
  if (haveElm && showFile) {
    const running = await new Promise(r => {
      const p = spawn('tasklist', ['/FI', 'IMAGENAME eq ELM.exe'], { windowsHide: true });
      let o = ''; p.stdout.on('data', d => o += d); p.on('close', () => r(/ELM\.exe/i.test(o))); p.on('error', () => r(false));
    });
    if (!running) { spawn(ELM_EXE, [showFile], { detached: true, windowsHide: true, stdio: 'ignore' }).unref(); console.log('  ELM      opening ' + path.basename(showFile) + ' (the big rig takes a minute to load)'); }
    else console.log('  ELM      already running - load ' + path.basename(showFile) + ' if it is not open');
  } else if (haveElm) {
    console.log('  ELM      installed. Show file not found - put ngv-gandel-hall.elm next to this script.');
  }
  console.log('  in ELM   3D stages > the "-sacn" stage > Testing > Testing mode ON');
  console.log('           (or run any effect on that stage - whatever ELM outputs, the hall shows)');
  console.log('');

  // bridge
  let st = await get(WS);
  if (!st) {
    quiet(path.join(__dirname, 'dmx_bridge.js'), ['--ws', String(WS), '--universes', UNIVERSES, '--fps', String(FPS)]);
    for (let i = 0; i < 20 && !st; i++) { await sleep(250); st = await get(WS); }
  }
  console.log(st ? `  bridge   listening (Art-Net udp/6454, sACN udp/5568 -> ws://localhost:${WS})` : '  bridge   FAILED to start - is another program on port ' + WS + '?');
  if (!st) process.exit(1);

  // page server
  let pg = await get(HTTP, '/index.html');
  if (!pg) {
    quiet(path.join(__dirname, 'serve.js'), ['--port', String(HTTP), '--root', ROOT]);
    for (let i = 0; i < 20 && !pg; i++) { await sleep(250); pg = await get(HTTP, '/index.html'); }
  }
  console.log(pg ? `  page     http://127.0.0.1:${HTTP}/` : '  page     FAILED to serve - is port ' + HTTP + ' taken?');
  if (!pg) process.exit(1);

  if (!args['no-open']) spawn('cmd', ['/c', 'start', '', PAGE], { detached: true, windowsHide: true, stdio: 'ignore' }).unref();
  console.log('  browser  ' + PAGE);
  console.log('');
  console.log('  Waiting for ELM... (this window can be closed; everything keeps running)');

  let hadDmx = false, hadClient = false;
  for (;;) {
    await sleep(2000);
    const s = JSON.parse(await get(WS) || '{}');
    if (!hadClient && s.clients > 0) { hadClient = true; console.log('  page connected.'); }
    if (!hadDmx && (s.sacn > 0 || s.artnet > 0)) { hadDmx = true; console.log(`  DMX arriving: ${s.universes} universes from ${s.lastSource}.`); }
    if (hadDmx && hadClient) { console.log('');
      console.log(`  LIVE - ${s.universes} universes on the hall. What ELM drives is what you see.`);
      break; }
  }
})();
