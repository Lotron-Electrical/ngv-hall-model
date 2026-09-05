import * as THREE from 'three';
import { Avatar } from './avatar.js';
import { Lift } from './lift.js';

// THE CREW ROOM (Lloyd, 2026-09-05: "I want this to be able to be multiplayer"). A room is a
// six-letter code. Everyone in it works the same hall: you see the others as characters
// (avatar.js) with their name over the hat, what they carry in their hands, their own scissor
// lift where they left it, and every light anyone fits goes in for everyone, columns powering up
// as they finish. The relay (server/relay.js) keeps the room's fitted set and pallet counts so a
// late joiner gets the hall as it stands.
//
// What is shared: bodies (position, look, carry), lifts (position, heading, deck height), fits,
// column power, boxes taken off pallets, the night. What is not shared yet: loose things on the
// floor (a box or bag someone else set down), the wraps, the bags' fill, the pallet jack. Each
// player's own physics run locally. The NPC crew stand down in a room: the crew is the people.
//
// The relay's address: RELAY below, or ?relay=ws://host:port for a local check.

export const RELAY = 'wss://ngv-relay.onrender.com';
const SEND_HZ = 12;
const VESTS = [0xff7a1a, 0xffd21a, 0x33d17a, 0x3aa0ff, 0xff4fa3, 0x9b6bff, 0x00d5d5, 0xff5b3a];

export function makeRoomCode() {
  const A = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; let s = '';
  for (let i = 0; i < 6; i++) s += A[Math.floor(Math.random() * A.length)];
  return s;
}

class Peer {
  constructor(id, name, scene, floorY, colour) {
    this.id = id; this.name = name;
    this.av = new Avatar(colour, name); scene.add(this.av.group);
    this.lift = new Lift(scene, floorY); this.lift.remote = true;
    this.target = null;              // the last frame received
    this.prev = null;                // the one before, for the pace
    this.speed = 0;
    this.pos = new THREE.Vector3(); this.yaw = 0; this.have = false;
    this.lastSeen = performance.now();
  }
  // a state frame from the wire
  take(m) {
    const now = performance.now();
    if (this.target) { this.prev = this.target; const dt = Math.max(0.03, (now - this.prev.at) / 1000); this.speed = Math.hypot(m.p[0] - this.prev.p[0], m.p[2] - this.prev.p[2]) / dt; }
    this.target = { ...m, at: now };
    this.lastSeen = now;
    if (!this.have) { this.pos.set(m.p[0], m.p[1], m.p[2]); this.yaw = m.y; this.have = true; this.lift.pos.set(m.L[0], this.lift.floorY, m.L[1]); this.lift.yaw = m.L[2]; this.lift.height = m.L[3]; }
  }
  // ease toward the last frame; the body walks at the pace the frames imply
  update(dt) {
    const t = this.target; if (!t) return;
    const k = Math.min(1, dt * 12);
    this.pos.x += (t.p[0] - this.pos.x) * k; this.pos.y += (t.p[1] - this.pos.y) * k; this.pos.z += (t.p[2] - this.pos.z) * k;
    let dy = t.y - this.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy)); this.yaw += dy * k;
    // no frame for a while = standing still, whatever the last pace was
    const stale = performance.now() - t.at > 400;
    const g = this.av.group;
    g.position.x = this.pos.x; g.position.z = this.pos.z;
    this.av.floorY = this.pos.y;
    // the camera yaw is the way the eyes look (three's -z forward); the avatar faces +z at rotation 0, so it turns half a circle
    g.rotation.y = this.yaw + Math.PI;
    this.av.walk(dt, stale ? 0 : this.speed);
    this.av.setLook(t.x || 0);
    this.av.setCarry(t.c || null);
    // the lift eases too
    const L = this.lift;
    L.pos.x += (t.L[0] - L.pos.x) * k; L.pos.z += (t.L[1] - L.pos.z) * k;
    let dl = t.L[2] - L.yaw; dl = Math.atan2(Math.sin(dl), Math.cos(dl)); L.yaw += dl * k;
    L.height += (t.L[3] - L.height) * k;
    L.refresh();
  }
  dispose(scene) {
    this.av.dispose();
    scene.remove(this.lift.group);
    this.lift.group.traverse((o) => { if (o.isMesh) { if (o.geometry) o.geometry.dispose(); for (const m of [].concat(o.material || [])) if (m && m.dispose) m.dispose(); } });
  }
}

export class Net {
  // G is the game (index.html's IG); hooks: { toast(msg), onFit(slot, name), onBox(pallet), onNight(n), onPeers() }
  constructor(G, { room, name, relay, hooks }) {
    this.G = G; this.room = room; this.name = name || 'Crew'; this.relay = relay || RELAY; this.hooks = hooks || {};
    this.peers = new Map(); this.id = null; this.on = false; this.closed = false;
    this.ws = null; this.acc = 0; this.retry = 0; this.status = 'connecting';
    this.slotById = new Map(G.install.slots.map((s) => [s.id, s]));
    this.connect();
  }

  connect() {
    if (this.closed) return;
    this.status = this.retry ? `reconnecting (${this.retry})` : 'connecting';
    let ws; try { ws = new WebSocket(this.relay); } catch (e) { this.status = 'bad relay address'; return; }
    this.ws = ws;
    ws.onopen = () => { ws.send(JSON.stringify({ t: 'join', room: this.room, name: this.name })); };
    ws.onmessage = (e) => { let m; try { m = JSON.parse(e.data); } catch (err) { return; } this.handle(m); };
    ws.onclose = () => { this.on = false; this.ws = null; if (this.closed) return; this.status = 'lost the relay'; this.retry++; setTimeout(() => this.connect(), Math.min(8000, 800 * this.retry)); this.hooks.onPeers?.(); };
    ws.onerror = () => { /* onclose follows */ };
  }

  handle(m) {
    const G = this.G;
    switch (m.t) {
      case 'welcome': {
        this.id = m.id; this.on = true; this.retry = 0; this.status = 'in the room';
        for (const p of m.peers || []) this.addPeer(p.id, p.name);
        // the hall as it stands: every fit anyone made, the boxes gone off the pallets, the night
        for (const id of m.state?.fitted || []) this.applyFit(id, null, true);
        for (const [i, n] of Object.entries(m.state?.boxes || {})) { const pal = G.items.pallets[+i]; if (pal) { pal.boxes = Math.max(0, Math.min(pal.boxes, 8 - n)); G.items.updatePalletStack(pal); } }
        if (m.state?.night > G.clock.night) this.hooks.onNight?.(m.state.night);
        // our own fits from before joining go up too, so the room and the save agree
        for (const id of G.install.fitted) if (!(m.state?.fitted || []).includes(id)) this.send({ t: 'fit', slot: id });
        this.hooks.toast?.(`In room ${this.room}${m.peers?.length ? ' with ' + m.peers.map((p) => p.name).join(', ') : ': share the link to bring the crew in'}`);
        this.hooks.onPeers?.();
        break;
      }
      case 'peer': this.addPeer(m.id, m.name); this.hooks.toast?.(`${m.name} joined the crew`); this.hooks.onPeers?.(); break;
      case 'leave': { const p = this.peers.get(m.id); if (p) { p.dispose(G.group); this.peers.delete(m.id); this.hooks.toast?.(`${p.name} left`); this.hooks.onPeers?.(); } break; }
      case 's': { const p = this.peers.get(m.id); if (p) p.take(m); break; }
      case 'fit': this.applyFit(m.slot, m.name, false); break;
      case 'box': { const pal = G.items.pallets[m.pallet]; if (pal && pal.boxes > 0) { pal.boxes--; G.items.updatePalletStack(pal); } break; }
      case 'night': this.hooks.onNight?.(m.n, m.name); break;
      case 'toast': this.hooks.toast?.(m.msg); break;
      case 'error': this.status = m.msg; break;
      default: break;
    }
  }

  addPeer(id, name) {
    if (this.peers.has(id) || id === this.id) return;
    const colour = VESTS[this.peers.size % VESTS.length];
    this.peers.set(id, new Peer(id, name, this.G.group, this.G.world.floorY, colour));
  }

  applyFit(slotId, byName, silent) {
    const G = this.G, slot = this.slotById.get(slotId);
    if (!slot || G.install.fitted.has(slotId)) return;
    G.install.fit(slot, { carry: null });
    this.hooks.onFit?.(slot, byName, silent);
  }

  send(msg) { if (this.ws && this.ws.readyState === 1) this.ws.send(JSON.stringify(msg)); }
  sendFit(slotId) { this.send({ t: 'fit', slot: slotId }); }
  sendBox(palletIndex) { this.send({ t: 'box', pallet: palletIndex }); }
  sendNight(n) { this.send({ t: 'night', n }); }

  // every frame: our state out at SEND_HZ, the others eased in
  update(dt) {
    const G = this.G, { player, lift } = G;
    this.acc += dt;
    if (this.on && this.acc >= 1 / SEND_HZ) {
      this.acc = 0;
      const c = player.carry ? player.carry.type : 0;
      this.send({ t: 's', p: [+player.pos.x.toFixed(3), +player.pos.y.toFixed(3), +player.pos.z.toFixed(3)], y: +player.yaw.toFixed(3), x: +player.pitch.toFixed(2), c,
        L: [+lift.pos.x.toFixed(3), +lift.pos.z.toFixed(3), +lift.yaw.toFixed(3), +lift.height.toFixed(2)], a: lift.aboard ? 1 : 0 });
    }
    for (const p of this.peers.values()) p.update(dt);
  }

  // the others' lifts are solid to you, and so are the others (a small circle each)
  lifts() { const out = []; for (const p of this.peers.values()) if (p.have) out.push(p.lift); return out; }
  addObstacles(world) { for (const p of this.peers.values()) if (p.have) world.obstacles.push({ x: p.pos.x, z: p.pos.z, r: 0.35, ref: p }); }
  points() { const out = []; for (const p of this.peers.values()) if (p.have) out.push(p.pos, p.lift.pos); return out; }
  names() { return [...this.peers.values()].map((p) => p.name); }

  close() {
    this.closed = true;
    if (this.ws) { try { this.ws.close(); } catch (e) {} this.ws = null; }
    for (const p of this.peers.values()) p.dispose(this.G.group);
    this.peers.clear(); this.on = false;
  }
}
