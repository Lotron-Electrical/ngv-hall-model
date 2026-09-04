#!/usr/bin/env node
// Static file server for the repo, so the page can be opened by a headless browser without
// file:// quirks (the ES module imports and the 6 MB model.glb both prefer a real origin).
//
//     node tools/serve.js [--port 8877] [--root <repo dir>]
//
// Binds 127.0.0.1 only: this is a local check harness, not a web host.
'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');

const args = Object.fromEntries(process.argv.slice(2).map((a, i, all) => a.startsWith('--') ? [a.slice(2), all[i + 1]] : []).filter(x => x.length));
const PORT = +(args.port || 8877);
const ROOT = path.resolve(args.root || path.join(__dirname, '..'));
const TYPES = { '.html': 'text/html', '.mp3': 'audio/mpeg', '.js': 'text/javascript', '.json': 'application/json', '.css': 'text/css',
  '.glb': 'model/gltf-binary', '.png': 'image/png', '.jpg': 'image/jpeg', '.csv': 'text/csv', '.cmd': 'text/plain', '.md': 'text/markdown' };

http.createServer((req, res) => {
  const rel = decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, '') || 'index.html';
  const file = path.resolve(ROOT, rel);
  if (!file.startsWith(ROOT)) { res.writeHead(403).end('no'); return; }
  // THE STUDIO'S SAVE (Lloyd, 2026-09-04): studio.html exports a show straight into the repo
  // rather than through the browser's download folder. POST /save with the body as the bytes and
  // ?path=show/<name>.cues.json (or .wav, .json under show/ or sound/). Local server, local files.
  if (req.method === 'POST' && rel === 'save') {
    const q = new URL(req.url, 'http://x').searchParams, p = String(q.get('path') || '');
    const target = path.resolve(ROOT, p);
    if (!/^(show|sound)\/[\w.-]+\.(json|wav|mp3)$/.test(p) || !target.startsWith(ROOT)) { res.writeHead(400).end('bad path'); return; }
    const chunks = []; req.on('data', d => chunks.push(d)); req.on('end', () => {
      fs.mkdirSync(path.dirname(target), { recursive: true }); fs.writeFileSync(target, Buffer.concat(chunks));
      res.writeHead(200, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }).end(JSON.stringify({ ok: true, path: p, bytes: Buffer.concat(chunks).length }));
    }); return;
  }
  fs.stat(file, (err, st) => {
    if (err || !st.isFile()) { res.writeHead(404, { 'Content-Type': 'text/plain' }).end('not found: ' + rel); return; }
    const base = { 'Content-Type': TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream',
      'Access-Control-Allow-Origin': '*', 'Cache-Control': 'no-store', 'Accept-Ranges': 'bytes' };
    // byte ranges: a browser seeks in an audio file by asking for its bytes from the new spot, and
    // a server that answers 200 with the whole file leaves the soundtrack unable to move
    const m = /^bytes=([0-9]*)-([0-9]*)$/.exec(req.headers.range || '');
    if (m && (m[1] || m[2])) {
      const a = m[1] ? +m[1] : Math.max(0, st.size - +m[2]), b = (m[1] && m[2]) ? Math.min(+m[2], st.size - 1) : st.size - 1;
      if (a >= st.size || a > b) { res.writeHead(416, { 'Content-Range': 'bytes */' + st.size }).end(); return; }
      res.writeHead(206, Object.assign(base, { 'Content-Range': `bytes ${a}-${b}/${st.size}`, 'Content-Length': b - a + 1 }));
      const rs = fs.createReadStream(file, { start: a, end: b }); rs.pipe(res); res.on('close', () => rs.destroy()); return;   // a browser drops its range request on every seek: the stream goes with it
    }
    res.writeHead(200, Object.assign(base, { 'Content-Length': st.size }));
    const rs = fs.createReadStream(file); rs.pipe(res); res.on('close', () => rs.destroy());
  });
}).listen(PORT, '127.0.0.1', () => console.log(`serving ${ROOT} at http://127.0.0.1:${PORT}/`));
