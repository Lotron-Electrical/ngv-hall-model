// The three lines every proof script in here repeats: attach to the headless Chrome on NGV_PORT,
// evaluate expressions in the page, and collect anything the page threw. Kept as one module so a
// new proof is the checks and nothing else.
// (Lloyd, 2026-09-07) the static server is http://127.0.0.1:8877; "ngv is not defined" everywhere
// means it is down, not that the page is broken.
import fs from 'node:fs';

export async function attach({ port = +(process.env.NGV_PORT || 9333), width = 1280, height = 800, dsf = 1, mobile = false } = {}) {
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
  let t = tabs.find(x => x.type === 'page');
  if (!t) t = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  let id = 0; const pend = {}; const errors = [];
  ws.onmessage = e => {
    const m = JSON.parse(e.data);
    if (m.id && pend[m.id]) { pend[m.id](m.result); delete pend[m.id]; }
    if (m.method === 'Runtime.exceptionThrown') errors.push('EXCEPTION ' + String(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text).slice(0, 300));
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') errors.push('CONSOLE ' + m.params.args.map(a => String(a.value ?? a.description ?? '')).join(' ').slice(0, 300));
  };
  await new Promise(r => ws.onopen = r);
  const send = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async expression => {
    const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (r && r.exceptionDetails) throw new Error('EVAL ' + String(r.exceptionDetails.exception?.description || r.exceptionDetails.text).slice(0, 400));
    return r ? r.result.value : undefined;
  };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable');
  await send('Network.setCacheDisabled', { cacheDisabled: true });
  await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: dsf, mobile });
  const shot = async path => { const s = await send('Page.captureScreenshot', { format: 'jpeg', quality: 90 }); fs.writeFileSync(path, Buffer.from(s.data, 'base64')); };
  // the page is ready when the hall, the strips and the light samples all exist
  const open = async (page = 'index.html', q = '') => {
    await send('Page.navigate', { url: `http://127.0.0.1:8877/${page}?cb=${Date.now()}${q}` });
    for (let i = 0; i < 90; i++) { await sleep(500); if (await ev('!!(window.ngv&&window.ngv.P&&window.ngv.P.n&&window.ngv.hall)').catch(() => false)) break; }
    await ev(`document.getElementById('enter').click()`).catch(() => {});
    await sleep(1500);
  };
  // Enter leaves the eye on the object's orbit, and idleStep drives it every frame: setCam is
  // overwritten until free roam takes the camera. Free roam sinks the object over about 15 s.
  const roam = async () => {
    await ev(`const r=document.getElementById('roamfab'); if(r)r.click();`).catch(() => {});
    // roamStep goes on writing the house dimmer and the layer stack for about fifteen seconds
    // after the orbit ends, so a scene set before it finishes is thrown away: wait for it to land
    for (let i = 0; i < 45; i++) { await sleep(700); if (await ev('!!(window.dbg&&!window.dbg.idle&&window.dbg.roam()===null)').catch(() => false)) break; }
    await sleep(1200);
  };
  return { ws, send, ev, sleep, shot, open, roam, errors, close: () => ws.close() };
}

// the ok/FAIL pattern the other proofs use: every line prints, and the process exits 1 if any failed
export function reporter() {
  let bad = 0;
  const say = (ok, msg) => { console.log((ok ? 'ok   ' : 'FAIL ') + msg); if (!ok) bad++; };
  return { say, note: m => console.log('     ' + m), done: () => bad };
}
