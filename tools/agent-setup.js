#!/usr/bin/env node
// One command that stands the live loop up: ELM (or any Art-Net / sACN sender) -> bridge -> the
// hall page. Written for an AI agent driving the tool for a client, so every step is a JSON line
// on stdout with a `stage` field; humans get the same lines and a plain-English summary at the end.
//
//     node tools/agent-setup.js                  start the bridge if needed, then wait for both ends
//     node tools/agent-setup.js --status         one JSON line describing the bridge, no changes
//     node tools/agent-setup.js --stop           stop a bridge this machine is running
//     node tools/agent-setup.js --no-wait        set up and exit without waiting for traffic
//     node tools/agent-setup.js --open           also open the page with ?ws= pointing at the bridge
//
// Flags: --ws 9930  --artnet 6454  --sacn 5568  --universes 1-1024  --fps 40  --timeout 300
//        --page <url, default the GitHub Pages copy>
//
// Stages, in order: node, bridge, port, start, up, network, elm, page, wait_artnet, artnet,
// wait_client, client, ready. Terminal stages: ready, timeout, error. An agent should read lines
// until one of those three appears.
//
// No npm packages, same as dmx_bridge.js.
'use strict';
const http = require('http');
const dgram = require('dgram');
const os = require('os');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const argv = process.argv.slice(2);
const args = {};
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (!a.startsWith('--')) continue;
  const next = argv[i + 1];
  args[a.slice(2)] = next === undefined || next.startsWith('--') ? true : (i++, next);
}
const WS = +(args.ws || 9930), ARTNET = +(args.artnet || 6454), SACN = +(args.sacn || 5568);
const UNIVERSES = String(args.universes || '1-1024'), FPS = +(args.fps || 40);
const TIMEOUT = +(args.timeout || 300) * 1000;
const BRIDGE = path.join(__dirname, 'dmx_bridge.js');
const PAGE = String(args.page || 'https://lotron-electrical.github.io/ngv-hall-model/');
const LOG = path.join(os.tmpdir(), `ngv-dmx-bridge-${WS}.log`);

let lastStage = '';
function say(stage, obj) { lastStage = stage; process.stdout.write(JSON.stringify({ stage, ...obj }) + '\n'); }
const sleep = ms => new Promise(r => setTimeout(r, ms));

function status() {
  return new Promise(resolve => {
    const req = http.get({ host: '127.0.0.1', port: WS, path: '/', timeout: 1500 }, res => {
      let b = ''; res.on('data', d => b += d);
      res.on('end', () => { try { resolve(JSON.parse(b)); } catch (e) { resolve(null); } });
    });
    req.on('error', () => resolve(null));
    req.on('timeout', () => { req.destroy(); resolve(null); });
  });
}

// Is something else already holding the Art-Net port? On this machine that is usually ELM itself,
// which binds udp/6454 to LISTEN for Art-Net polls; two processes cannot both receive the unicast
// stream, so ELM must be told to send somewhere else (see the `elm` stage below).
function portHolder(port) {
  return new Promise(resolve => {
    const s = dgram.createSocket({ type: 'udp4', reuseAddr: false });
    s.once('error', e => { s.close(() => {}); resolve(e.code || 'EADDRINUSE'); });
    s.bind(port, () => s.close(() => resolve(null)));
  });
}

const ips = Object.values(os.networkInterfaces()).flat()
  .filter(i => i && i.family === 'IPv4' && !i.internal).map(i => ({ address: i.address, netmask: i.netmask }));
const broadcasts = ips.map(i => i.address.split('.').map((o, k) => (+o | ~+i.netmask.split('.')[k]) & 255).join('.'));

async function main() {
  const nodeOk = +process.versions.node.split('.')[0] >= 14;
  say('node', { version: process.version, ok: nodeOk, exec: process.execPath, bridge: BRIDGE, bridgeExists: fs.existsSync(BRIDGE) });
  if (!nodeOk) { say('error', { error: 'Node 14 or newer is required; install from https://nodejs.org' }); process.exit(1); }
  if (!fs.existsSync(BRIDGE)) { say('error', { error: `dmx_bridge.js not found beside this script (${BRIDGE})` }); process.exit(1); }

  if (args.stop) {
    const st = await status();
    if (!st) { say('ready', { running: false, note: 'no bridge was listening on this port' }); return; }
    // the bridge has no shutdown endpoint; find it by the port it holds and end it
    const pid = await pidOnPort(WS);
    if (pid) { try { process.kill(pid); } catch (e) { /* already gone */ } }
    await sleep(500);
    say('ready', { running: !!(await status()), killed: pid || null });
    return;
  }

  let st = await status();
  // the bridge's own `ws` field is a port number, so spread it first and let the URLs win
  say('bridge', { running: !!st, ...(st || {}), statusUrl: `http://127.0.0.1:${WS}/`, wsUrl: `ws://localhost:${WS}` });

  if (args.status) { if (!st) say('error', { error: 'bridge is not running' }); else say('ready', st); return; }

  const holder = st ? null : await portHolder(ARTNET);
  say('port', { artnet: ARTNET, free: !holder, code: holder,
    note: holder ? `udp/${ARTNET} is already held by another process on this machine (usually ELM itself). The bridge will still start, but Art-Net unicast to this machine's own IP will not reach it. Workarounds, best first: (1) run the bridge on a SECOND machine on the same LAN and point ELM at that IP; (2) give this machine a second IPv4 address and unicast to that; (3) send Art-Net as BROADCAST to ${broadcasts[0] || 'x.x.x.255'} (both processes receive a broadcast); (4) use sACN instead - ELM sends sACN multicast on udp/${SACN}, which both processes can join.` : undefined });

  if (!st && !args['no-start']) {
    const fd = fs.openSync(LOG, 'a');
    const child = spawn(process.execPath, [BRIDGE, '--ws', String(WS), '--artnet', String(ARTNET), '--sacn', String(SACN), '--universes', UNIVERSES, '--fps', String(FPS)],
      { detached: true, windowsHide: true, stdio: ['ignore', fd, fd], cwd: path.dirname(BRIDGE) });
    child.unref();
    say('start', { pid: child.pid, log: LOG, args: { ws: WS, artnet: ARTNET, sacn: SACN, universes: UNIVERSES, fps: FPS } });
    for (let i = 0; i < 20 && !st; i++) { await sleep(250); st = await status(); }
  }
  if (!st) { say('error', { error: `the bridge did not answer on http://127.0.0.1:${WS}/ - see ${LOG}` }); process.exit(1); }
  say('up', { ...st, statusUrl: `http://127.0.0.1:${WS}/` });

  say('network', { ips: ips.map(i => i.address), broadcasts, artnetPort: ARTNET, sacnPort: SACN,
    firewall: 'Windows Defender must allow inbound UDP for node.exe on the private profile. If the first run showed a firewall dialog and it was dismissed, allow it with: netsh advfirewall firewall add rule name="NGV DMX bridge" dir=in action=allow protocol=UDP localport=' + ARTNET });

  say('elm', {
    protocol: 'Art-Net',
    sendTo: holder ? (broadcasts[0] || null) : (ips[0] ? ips[0].address : '127.0.0.1'),
    mode: holder ? 'broadcast' : 'unicast',
    universes: 'ELM 0 to 607 (the page calls the same universes 1 to 608)',
    steps: [
      'Devices / Art-Net output: every universe row carries a node IP. Select all 608 rows and bulk-fill the IP with `sendTo` above; leave the port at ' + ARTNET + '.',
      'Universe numbering: the CSV exported from the page already carries ELM-style numbers (Art-Net 0-based). Do not re-address the rig after import; ELM keeps the patch from the file.',
      'Output rate: 40 fps or lower. The bridge batches to --fps ' + FPS + ' regardless, so a faster ELM only adds UDP.',
      'If sending sACN instead, point it at multicast (default) on udp/' + SACN + ' and set the page\'s universe offset to -1 only if the numbering looks one out.'
    ],
    verify: `curl http://127.0.0.1:${WS}/  ->  artnet or sacn counters must climb`
  });

  const pageUrl = PAGE + (PAGE.includes('#') ? '' : '') + (PAGE.includes('?') ? '&' : '?') + 'ws=' + encodeURIComponent(`ws://localhost:${WS}`);
  say('page', { url: pageUrl, fallback: PAGE,
    note: `The ?ws= parameter is a PROPOSED auto-connect (see PLAN-agentic.md); until it ships, open ${PAGE}, expand "Live input", set Bridge to ws://localhost:${WS} and press Connect.`,
    mixedContent: 'A page served over https connecting to ws://localhost is allowed by Chrome (localhost is a trusted origin), but Chrome\'s Local Network Access prompt may still appear on first connect - accept it. If the browser blocks it, serve the page locally instead: node tools/serve.js, then http://127.0.0.1:8877/index.html' });

  if (args.open) {
    spawn('cmd', ['/c', 'start', '', pageUrl], { detached: true, windowsHide: true, stdio: 'ignore' }).unref();
  }
  if (args['no-wait']) { say('ready', { waited: false, ...(await status()) }); return; }

  const t0 = Date.now();
  say('wait_artnet', { timeoutSeconds: TIMEOUT / 1000, waitingFor: 'the first Art-Net or sACN packet from the sender' });
  let s;
  for (;;) {
    s = await status();
    if (s && (s.artnet || s.sacn)) break;
    if (Date.now() - t0 > TIMEOUT) { say('timeout', { at: 'artnet', ...(s || {}), hint: holder ? 'udp/' + ARTNET + ' is shared with another process on this machine - use broadcast or a second machine' : 'check the sender\'s target IP, the firewall, and that the sender is actually outputting' }); process.exit(2); }
    await sleep(1000);
  }
  say('artnet', { artnet: s.artnet, sacn: s.sacn, universes: s.universes, lastSource: s.lastSource,
    expect: 'universes should reach 608 for the full 8-gaps-per-column design at 128 RGBW px per universe' });

  say('wait_client', { waitingFor: 'the hall page to connect to ws://localhost:' + WS });
  for (;;) {
    s = await status();
    if (s && s.clients > 0) break;
    if (Date.now() - t0 > TIMEOUT) { say('timeout', { at: 'client', ...(s || {}), hint: 'open ' + PAGE + ', expand "Live input", press Connect' }); process.exit(2); }
    await sleep(1000);
  }
  say('ready', { ...s, page: PAGE, statusUrl: `http://127.0.0.1:${WS}/`,
    summary: `${s.universes} universes arriving from ${s.lastSource}, ${s.clients} page(s) connected. What ELM drives is now what the hall shows.` });
}

// Which process holds a TCP port, without npm: netstat is on every Windows and Linux box we target.
function pidOnPort(port) {
  return new Promise(resolve => {
    const cmd = process.platform === 'win32' ? ['netstat', ['-ano', '-p', 'tcp']] : ['lsof', ['-ti', `tcp:${port}`]];
    const p = spawn(cmd[0], cmd[1], { windowsHide: true });
    let out = ''; p.stdout.on('data', d => out += d);
    p.on('error', () => resolve(null));
    p.on('close', () => {
      if (process.platform !== 'win32') return resolve(+out.trim().split('\n')[0] || null);
      const line = out.split('\n').find(l => /LISTENING/.test(l) && new RegExp(`[:.]${port}\\s`).test(l));
      resolve(line ? +line.trim().split(/\s+/).pop() : null);
    });
  });
}

main().catch(e => { say('error', { error: e.message, after: lastStage }); process.exit(1); });
