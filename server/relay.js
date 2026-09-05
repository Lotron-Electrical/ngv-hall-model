// THE CREW ROOM RELAY (Lloyd, 2026-09-05: "I want this to be able to be multiplayer").
//
// A room is a code. Everyone who joins it sees everyone else: where they stand, what they carry,
// where their lift is, and every light anyone fits. The relay keeps the room's shared state
// (fitted slots, pallet box counts, the night) so a late joiner gets the hall as it stands, and
// forwards everything else as it arrives. It decides nothing: each player owns their own body
// and their own lift, and a fit is a fit.
//
//   node server/relay.js            (PORT from the environment, 9940 by default)
//
// Wire (JSON text frames):
//   c->s  {t:'join', room, name}                 -> s->c {t:'welcome', id, room, state, peers:[{id,name}]}
//   s->all {t:'peer', id, name} / {t:'leave', id}
//   c->s  {t:'s', ...}     a state frame, forwarded with the sender's id stamped in
//   c->s  {t:'fit', slot} {t:'box', pallet} {t:'night', n} {t:'toast', msg}   shared, stored, forwarded
//   both  {t:'ping'} / {t:'pong'}
'use strict';
const http = require('http');
const { WebSocketServer } = require('ws');

const PORT = +(process.env.PORT || 9940);
const rooms = new Map();   // code -> { clients: Map<id, ws>, state: { fitted: Set, boxes: {}, night } , touched }
let nextId = 1;

function room(code) {
  let r = rooms.get(code);
  if (!r) { r = { clients: new Map(), state: { fitted: new Set(), boxes: {}, night: 1 }, touched: Date.now() }; rooms.set(code, r); }
  r.touched = Date.now();
  return r;
}
function send(ws, msg) { if (ws.readyState === 1) ws.send(JSON.stringify(msg)); }
function broadcast(r, msg, except) { const s = JSON.stringify(msg); for (const [id, ws] of r.clients) if (id !== except && ws.readyState === 1) ws.send(s); }
function shape(r) { return { fitted: [...r.state.fitted], boxes: r.state.boxes, night: r.state.night }; }

const server = http.createServer((req, res) => {
  // a health line, and a count for the curious
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ ok: true, rooms: rooms.size, players: [...rooms.values()].reduce((n, r) => n + r.clients.size, 0) }));
});
const wss = new WebSocketServer({ server, maxPayload: 64 * 1024 });

wss.on('connection', (ws) => {
  let me = null;   // { id, name, code }
  ws.isAlive = true;
  ws.on('pong', () => { ws.isAlive = true; });
  ws.on('message', (data) => {
    let m; try { m = JSON.parse(data); } catch (e) { return; }
    if (!m || typeof m.t !== 'string') return;
    if (m.t === 'ping') { send(ws, { t: 'pong' }); return; }
    if (m.t === 'join') {
      if (me) return;
      const code = String(m.room || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8);
      if (!code) { send(ws, { t: 'error', msg: 'no room' }); return; }
      const name = String(m.name || 'Crew').slice(0, 18);
      const r = room(code);
      me = { id: String(nextId++), name, code };
      send(ws, { t: 'welcome', id: me.id, room: code, state: shape(r), peers: [...r.clients.keys()].map((id) => ({ id, name: r.clients.get(id).crewName })) });
      ws.crewName = name;
      r.clients.set(me.id, ws);
      broadcast(r, { t: 'peer', id: me.id, name }, me.id);
      return;
    }
    if (!me) return;
    const r = rooms.get(me.code); if (!r) return;
    r.touched = Date.now();
    switch (m.t) {
      case 's': m.id = me.id; broadcast(r, m, me.id); break;
      case 'fit': if (typeof m.slot === 'string' && !r.state.fitted.has(m.slot)) { r.state.fitted.add(m.slot); broadcast(r, { t: 'fit', slot: m.slot, id: me.id, name: me.name }, me.id); } break;
      case 'box': if (Number.isInteger(m.pallet)) { r.state.boxes[m.pallet] = (r.state.boxes[m.pallet] || 0) + 1; broadcast(r, { t: 'box', pallet: m.pallet, id: me.id }, me.id); } break;
      case 'night': if (Number.isInteger(m.n) && m.n > r.state.night) { r.state.night = m.n; broadcast(r, { t: 'night', n: m.n, id: me.id, name: me.name }, me.id); } break;
      case 'toast': if (typeof m.msg === 'string') broadcast(r, { t: 'toast', msg: m.msg.slice(0, 120), id: me.id, name: me.name }, me.id); break;
      default: break;
    }
  });
  ws.on('close', () => {
    if (!me) return;
    const r = rooms.get(me.code); if (!r) return;
    r.clients.delete(me.id);
    broadcast(r, { t: 'leave', id: me.id, name: me.name });
  });
});

// dead sockets go every 30 s; an empty room is forgotten after an hour so a crew can come back from a break
setInterval(() => {
  for (const ws of wss.clients) { if (!ws.isAlive) { ws.terminate(); continue; } ws.isAlive = false; ws.ping(); }
  const cut = Date.now() - 60 * 60 * 1000;
  for (const [code, r] of rooms) if (!r.clients.size && r.touched < cut) rooms.delete(code);
}, 30000);

server.listen(PORT, () => console.log(`ngv relay on :${PORT}`));
