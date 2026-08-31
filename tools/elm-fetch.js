#!/usr/bin/env node
// Pull the page's pixel map out of a headless browser, for an agent that has no screen.
//
// The map is not a file: index.html computes it in JavaScript from the current design (system,
// density, gap count, strip order, pixels per universe), so the only honest source of the CSV is
// the page itself. This drives an already-running Chrome over the DevTools protocol, opens the
// page in a throwaway tab, waits for window.elmCsv to exist, and prints what it asks for.
//
//     node tools/elm-fetch.js --url <page> [--port 9222] [--what csv|patch|facts] [--out file]
//                             [--set density=60,count=8,system=strip] [--ppu 128] [--u0 1]
//                             [--proto ArtNet|sACN] [--up y|z]
//
// Start the browser first, e.g.
//     chrome --headless=new --remote-debugging-port=9222 --remote-allow-origins=*
// and serve the repo (a file:// URL works too, but the model is 6 MB so a local server is kinder):
//     node tools/serve.js  ->  http://127.0.0.1:8877/index.html
//
// No npm packages: the WebSocket client below is the handshake plus masked text frames and a
// re-assembling reader, which is all the DevTools protocol needs from us.
'use strict';
const http = require('http');
const crypto = require('crypto');
const fs = require('fs');

const args = {};
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  if (a.startsWith('--')) args[a.slice(2)] = (process.argv[i + 1] || '').startsWith('--') || i + 1 >= process.argv.length ? true : process.argv[++i];
}
const PORT = +(args.port || 9222);
const PAGE = args.url || 'http://127.0.0.1:8877/index.html';
const WHAT = args.what || 'csv';
const TIMEOUT = +(args.timeout || 60) * 1000;

function httpJson(method, path) {
  return new Promise((res, rej) => {
    const req = http.request({ host: '127.0.0.1', port: PORT, path, method }, r => {
      let b = ''; r.on('data', d => b += d); r.on('end', () => { try { res(JSON.parse(b)); } catch (e) { rej(new Error(`${path}: ${b.slice(0, 200)}`)); } });
    });
    req.on('error', rej); req.end();
  });
}

// ---- minimal WebSocket client (client frames must be masked; server frames are not)
function wsConnect(url) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const key = crypto.randomBytes(16).toString('base64');
    const req = http.request({ host: u.hostname, port: u.port || 80, path: u.pathname + u.search, method: 'GET',
      // no Origin header: Chrome rejects an origin-bearing DevTools upgrade with 403 unless it was
      // started with --remote-allow-origins, and the rejection is silent (no 'upgrade' event)
      headers: { Connection: 'Upgrade', Upgrade: 'websocket', 'Sec-WebSocket-Key': key, 'Sec-WebSocket-Version': 13 } });
    req.on('response', r => reject(new Error(`DevTools refused the WebSocket upgrade: HTTP ${r.statusCode}`)));
    req.on('upgrade', (res, socket) => {
      socket.setNoDelay(true);
      let buf = Buffer.alloc(0), frag = [], fragOp = 0;
      const handlers = { message: () => {} };
      socket.on('data', d => {
        buf = Buffer.concat([buf, d]);
        for (;;) {
          if (buf.length < 2) return;
          const fin = (buf[0] & 0x80) !== 0, op = buf[0] & 0x0f;
          let len = buf[1] & 0x7f, p = 2;
          if (len === 126) { if (buf.length < 4) return; len = buf.readUInt16BE(2); p = 4; }
          else if (len === 127) { if (buf.length < 10) return; len = Number(buf.readBigUInt64BE(2)); p = 10; }
          if (buf.length < p + len) return;
          const payload = buf.subarray(p, p + len);
          buf = buf.subarray(p + len);
          if (op === 0x8) { socket.end(); return; }
          if (op === 0x9) { socket.write(Buffer.concat([Buffer.from([0x8a, 0x80]), Buffer.alloc(4)])); continue; }
          if (op === 0xa) continue;
          if (op === 0x0) frag.push(payload); else { frag = [payload]; fragOp = op; }
          if (fin) { const m = Buffer.concat(frag); frag = []; if (fragOp === 0x1) handlers.message(m.toString('utf8')); }
        }
      });
      const send = text => {
        const body = Buffer.from(text, 'utf8'), mask = crypto.randomBytes(4);
        const len = body.length;
        const head = len < 126 ? Buffer.from([0x81, 0x80 | len])
          : len < 65536 ? Buffer.from([0x81, 0xfe, len >> 8 & 255, len & 255])
            : Buffer.concat([Buffer.from([0x81, 0xff]), (() => { const b = Buffer.alloc(8); b.writeBigUInt64BE(BigInt(len)); return b; })()]);
        const masked = Buffer.allocUnsafe(len);
        for (let i = 0; i < len; i++) masked[i] = body[i] ^ mask[i & 3];
        socket.write(Buffer.concat([head, mask, masked]));
      };
      resolve({ send, socket, on: (k, f) => { handlers[k] = f; } });
    });
    req.on('error', reject);
    req.end();
  });
}

async function main() {
  const version = await httpJson('GET', '/json/version');
  // Chrome 111+ wants PUT for /json/new
  let target;
  try { target = await httpJson('PUT', '/json/new?' + encodeURIComponent(PAGE)); }
  catch (e) { target = await httpJson('GET', '/json/new?' + encodeURIComponent(PAGE)); }
  const ws = await wsConnect(target.webSocketDebuggerUrl);
  let id = 0; const pending = new Map();
  ws.on('message', txt => { const m = JSON.parse(txt); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
  const cmd = (method, params) => new Promise((res, rej) => {
    const i = ++id; pending.set(i, m => m.error ? rej(new Error(m.error.message)) : res(m.result));
    ws.send(JSON.stringify({ id: i, method, params: params || {} }));
  });
  const evaluate = async expr => {
    const r = await cmd('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception ? r.exceptionDetails.exception.description : 'evaluate failed');
    return r.result.value;
  };

  // the page builds its geometry after model.glb loads, so wait for the keyhole AND for runs
  const t0 = Date.now();
  for (;;) {
    const ready = await evaluate('!!(window.elmCsv && window.ngv && window.ngv.P && window.ngv.P.runs && window.ngv.P.runs.length)').catch(() => false);
    if (ready) break;
    if (Date.now() - t0 > TIMEOUT) throw new Error(`page did not become ready within ${TIMEOUT / 1000}s: ${PAGE}`);
    await new Promise(r => setTimeout(r, 500));
  }

  // optional design changes, applied through the page's own controls so it recomputes properly
  const sets = [];
  if (typeof args.set === 'string') for (const kv of args.set.split(',')) { const [k, v] = kv.split('='); sets.push([k, v]); }
  for (const [k, v] of sets) {
    if (k === 'system') sets.system = await evaluate(`(()=>{const b=document.querySelector('#sysseg button[data-s="${v}"]'); if(!b)return 'no such system'; b.click(); return 'ok';})()`);
    else if (k === 'density') await evaluate(`(()=>{const b=document.querySelector('#dens button[data-d="${+v}"]'); if(b)b.click(); return 'ok';})()`);
    else if (k === 'count') await evaluate(`(()=>{const n=document.getElementById('cn'); n.value=${+v}; n.dispatchEvent(new Event('change',{bubbles:true})); return 'ok';})()`);
  }
  const fields = { ppu: 'pm_ppu', u0: 'pm_u0', maxout: 'pm_maxout', opc: 'pm_opc', order: 'pm_order', dir: 'pm_dir', proto: 'pm_proto', up: 'pm_up' };
  for (const [flag, elId] of Object.entries(fields)) {
    if (args[flag] === undefined || args[flag] === true) continue;
    await evaluate(`(()=>{const e=document.getElementById('${elId}'); e.value=${JSON.stringify(String(args[flag]))}; e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true})); return 'ok';})()`);
  }
  if (sets.length || Object.keys(fields).some(f => args[f] !== undefined && args[f] !== true)) await new Promise(r => setTimeout(r, 1200));

  const facts = await evaluate(`(()=>{const P=window.ngv.P, s=window.ngv.state;
    const g=id=>document.getElementById(id).value;
    let uMin=Infinity,uMax=-Infinity; for(let i=0;i<P.n;i++){const u=P.univ[i]; if(u<uMin)uMin=u; if(u>uMax)uMax=u;}
    const px=new Set(); for(let i=0;i<P.n;i++)px.add(P.run[i]*4096+P.pi[i]);
    return {system:s.system, density:s.density, gapsPerColumn:s.count, strips:P.runs.length, leds:P.n, pixels:px.size,
      pixelsPerUniverse:+g('pm_ppu'), firstUniverse:+g('pm_u0'), maxPixelsPerOutput:+g('pm_maxout'), outputsPerController:+g('pm_opc'),
      stripOrder:g('pm_order'), dataDirection:g('pm_dir'), elmProtocol:g('pm_proto'), elmUpAxis:g('pm_up'),
      pageUniverseMin:uMin, pageUniverseMax:uMax, summary:document.getElementById('pm_tot').textContent};})()`);

  let out;
  if (WHAT === 'facts') out = JSON.stringify(facts, null, 2);
  else if (WHAT === 'patch') out = await evaluate(
    `(()=>{const t=document.getElementById('pm_table'); return Array.from(t.rows).map(r=>Array.from(r.cells).map(c=>c.textContent).join(',')).join('\\n');})()`);
  else out = await evaluate('window.elmCsv()');

  if (WHAT === 'csv') {
    const n = out ? out.split('\n').length - 1 : 0;
    process.stderr.write(JSON.stringify({ stage: 'csv', rows: n, ...facts }) + '\n');
  }
  if (args.out && typeof args.out === 'string') { fs.writeFileSync(args.out, out); process.stderr.write(`wrote ${args.out}\n`); }
  else process.stdout.write(out + '\n');

  await cmd('Page.close').catch(() => {});
  await httpJson('GET', '/json/close/' + target.id).catch(() => {});
  ws.socket.destroy();
  process.exit(0);
}
main().catch(e => { process.stderr.write(JSON.stringify({ stage: 'error', error: e.message }) + '\n'); process.exit(1); });
