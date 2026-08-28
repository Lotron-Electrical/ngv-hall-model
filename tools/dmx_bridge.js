#!/usr/bin/env node
// Art-Net / sACN -> WebSocket bridge, so a browser page can show what a pixel mapper (ELM, Resolume,
// MadMapper, a console) is sending. A browser cannot open a UDP socket; this listens on the two
// standard ports and re-sends every universe it hears over ws://localhost:9930 as binary frames.
//
//     node tools/dmx_bridge.js [--ws 9930] [--artnet 6454] [--sacn 5568] [--universes 1-512] [--fps 40]
//
// Point the mapper's Art-Net or sACN output at this machine (unicast to its IP, or broadcast /
// multicast on the same LAN), open the hall page, expand "Live input" and press Connect. The page
// applies the DMX to its LEDs through its own pixel map, so the map on the page IS the patch the
// mapper must use.
//
// No npm packages: the WebSocket server is the twenty lines the protocol needs for server -> client
// binary frames (RFC 6455 handshake, unmasked frames, ping/pong), which is all this does.
//
// Frame format (binary, little-endian): repeated records of
//     uint16 universe, uint16 length, then `length` bytes of DMX (slot 1 first, no start code)
// batched at --fps so 480 universes at 40 Hz is one WebSocket frame every 25 ms, not 19,200 a second.
'use strict';
const dgram = require('dgram');
const http = require('http');
const crypto = require('crypto');
const os = require('os');

const args = Object.fromEntries(process.argv.slice(2).map((a, i, all) => a.startsWith('--') ? [a.slice(2), all[i + 1]] : []).filter(x => x.length));
const WS_PORT = +(args.ws || 9930), ARTNET_PORT = +(args.artnet || 6454), SACN_PORT = +(args.sacn || 5568), FPS = +(args.fps || 40);
const [U_LO, U_HI] = (args.universes || '1-512').split('-').map(Number);

const universes = new Map();   // universe -> Uint8Array(512)
const dirty = new Set();
const stats = { artnet: 0, sacn: 0, frames: 0, clients: 0, lastSource: '' };

function store(u, data, source) {
  if (u < U_LO || u > U_HI) return;
  let buf = universes.get(u);
  if (!buf) { buf = new Uint8Array(512); universes.set(u, buf); }
  buf.set(data.subarray(0, 512));
  dirty.add(u);
  stats.lastSource = source;
}

// ---- Art-Net: "Art-Net\0", OpCode 0x5000 little-endian, ProtVer, Sequence, Physical, SubUni, Net,
// Length big-endian, data. Universe = Net<<8 | SubUni; ELM and most senders show this as 0-based
// "universe 0 = first", so the page's 1-based universe N is Art-Net N-1 unless the sender says otherwise.
const ART = dgram.createSocket({ type: 'udp4', reuseAddr: true });
ART.on('message', (m, rinfo) => {
  if (m.length < 18 || m.toString('latin1', 0, 8) !== 'Art-Net\0') return;
  const op = m.readUInt16LE(8);
  if (op !== 0x5000) return;
  const u = (m[15] << 8 | m[14]) + 1;   // 1-based on the page
  const len = Math.min(m.readUInt16BE(16), m.length - 18, 512);
  store(u, m.subarray(18, 18 + len), `Art-Net ${rinfo.address}`);
  stats.artnet++;
});
ART.bind(ARTNET_PORT, () => { try { ART.setBroadcast(true); } catch (e) { /* not fatal */ } });

// ---- sACN / E1.31: root layer (ACN packet identifier at 4..15), framing layer universe at 113..114
// big-endian, DMP layer property values from 125 (start code) then slots from 126.
const SACN = dgram.createSocket({ type: 'udp4', reuseAddr: true });
SACN.on('message', (m, rinfo) => {
  if (m.length < 126 || m.toString('latin1', 4, 16) !== 'ASC-E1.17\0\0\0') return;
  const vector = m.readUInt32BE(18);
  if (vector !== 0x00000004) return;         // VECTOR_ROOT_E131_DATA
  const u = m.readUInt16BE(113);
  if (m[125] !== 0) return;                  // only start code 0 is levels
  const count = Math.min(m.readUInt16BE(123) - 1, m.length - 126, 512);
  store(u, m.subarray(126, 126 + count), `sACN ${rinfo.address}`);
  stats.sacn++;
});
SACN.bind(SACN_PORT, () => {
  // join the multicast group of every universe in range; unicast to this host arrives regardless
  for (let u = U_LO; u <= Math.min(U_HI, 63999); u++) {
    try { SACN.addMembership(`239.255.${(u >> 8) & 0xff}.${u & 0xff}`); } catch (e) { break; }
  }
});

// ---- WebSocket server, server -> client only
const clients = new Set();
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
  res.end(JSON.stringify({ ok: true, ...stats, universes: universes.size, ws: WS_PORT }));
});
server.on('upgrade', (req, socket) => {
  const key = req.headers['sec-websocket-key'];
  if (!key) { socket.destroy(); return; }
  const accept = crypto.createHash('sha1').update(key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
  socket.write('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ' + accept + '\r\n\r\n');
  clients.add(socket); stats.clients = clients.size;
  socket.on('data', d => { if ((d[0] & 0x0f) === 0x8) { clients.delete(socket); stats.clients = clients.size; socket.end(); } else if ((d[0] & 0x0f) === 0x9) { socket.write(Buffer.from([0x8a, 0])); } });
  socket.on('close', () => { clients.delete(socket); stats.clients = clients.size; });
  socket.on('error', () => { clients.delete(socket); stats.clients = clients.size; });
  // a new client gets everything known so far
  for (const u of universes.keys()) dirty.add(u);
});
server.listen(WS_PORT, '127.0.0.1');

function frame(payload) {
  const len = payload.length;
  const head = len < 126 ? Buffer.from([0x82, len]) : len < 65536 ? Buffer.from([0x82, 126, len >> 8, len & 255]) : Buffer.concat([Buffer.from([0x82, 127]), (() => { const b = Buffer.alloc(8); b.writeBigUInt64BE(BigInt(len)); return b; })()]);
  return Buffer.concat([head, payload]);
}
setInterval(() => {
  if (!dirty.size || !clients.size) { dirty.clear(); return; }
  const parts = [];
  for (const u of dirty) { const h = Buffer.alloc(4); h.writeUInt16LE(u, 0); h.writeUInt16LE(512, 2); parts.push(h, Buffer.from(universes.get(u))); }
  dirty.clear();
  const f = frame(Buffer.concat(parts));
  for (const c of clients) { if (!c.write(f)) { /* back-pressure: drop this frame for a slow client */ } }
  stats.frames++;
}, 1000 / FPS);

const ips = Object.values(os.networkInterfaces()).flat().filter(i => i && i.family === 'IPv4' && !i.internal).map(i => i.address);
console.log(`dmx_bridge: Art-Net on udp/${ARTNET_PORT}, sACN on udp/${SACN_PORT} (universes ${U_LO}-${U_HI}), WebSocket ws://localhost:${WS_PORT} at ${FPS} fps`);
console.log(`send to this machine at ${ips.join(', ') || 'localhost'}; status: http://localhost:${WS_PORT}/`);
setInterval(() => { if (stats.artnet + stats.sacn) console.log(`packets art-net ${stats.artnet} sacn ${stats.sacn}, universes ${universes.size}, clients ${clients.size}, last ${stats.lastSource}`); }, 5000);
