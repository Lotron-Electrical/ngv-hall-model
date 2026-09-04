import * as THREE from 'three';
import { loadWorld, collideWorld, updateDoors, hallToWorld } from './world.js';
import { Fx } from './fx.js';
import { Body } from './body.js';
import { Crew } from './crew.js';
import { setupRenderer, updateRunLights } from './hallmat.js';
import { Sound } from './sound.js';
import { Player } from './player.js';
import { Lift } from './lift.js';
import { createItems, nearestAction, updateItems, dropCarry, cleanupClear, resetForNight, refreshObstacles } from './items.js';
import { Install } from './install.js';
import { GameClock, loadSave, saveGame } from './clock.js';
import { updateHud, showSummary } from './hud.js';

const canvas = document.querySelector('#cv');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.7));
const scene = new THREE.Scene();
setupRenderer(renderer, scene);
const camera = new THREE.PerspectiveCamera(68, 1, 0.05, 220);
const player = new Player(camera, canvas);
player.bind({
  action: document.querySelector('#action'),
  prompt: document.querySelector('#prompt'),
  moveStick: document.querySelector('#move'),
  lookStick: document.querySelector('#look'),
  drop: document.querySelector('#drop'),
  liftUp: document.querySelector('#liftUp'),
  liftDown: document.querySelector('#liftDown')
});
scene.add(camera);

let world, lift, items, install, clock, currentAction, fx, body, crew;
let last = performance.now();
let runLightTick = 0;
let doorsWereOpen = false;

function resize() {
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

const snd = new Sound();

async function init() {
  world = await loadWorld(scene);
  const saved = loadSave();
  const runsData = await fetch(new URL('../runs.json', import.meta.url).href).then((r) => r.json());
  install = new Install(scene, runsData, saved);
  items = createItems(scene, world, camera);
  lift = new Lift(scene, world.floorY);
  items.lift = lift;   // dropCarry needs it to know a light went down on the deck
  clock = new GameClock(saved);
  body = new Body();
  player.body = body;
  fx = new Fx(scene, camera, world.hallScene, lift, install);
  crew = new Crew(scene, world, items, install, collideWorld, lift);
  clock.fittedAtStart = install.counts().fitted;
  player.pos.copy(hallToWorld(52.0, 7.5, world.floorY));
  player.yaw = 1.35;
  document.querySelector('#prompt').textContent = 'Press Start Shift';
  window.game = { player, lift, items, install, clock, world, fx, body, crew, hallToWorld, dbg: { dt: 0, frames: 0 } };
  updateRunLights(install);   // for headless checks
  requestAnimationFrame(loop);
}

// a line at the top of the picture for a few seconds: who joined, who finished what
let toastTimer = null;
function showToast(msg) { const el = document.querySelector('#toast'); el.textContent = msg; el.classList.add('up'); clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove('up'), 6000); }

function startGame() {
  document.querySelector('#overlay').classList.add('gone');
  document.body.classList.add('playing');
  clock.running = true;
  if (!matchMedia('(pointer: coarse)').matches) {
    const req = canvas.requestPointerLock?.();
    if (req?.catch) req.catch(() => {});
  }
  snd.wake(); snd.tone(220, 0.08, 'sine', 0.05);
}

function interact() {
  if (!currentAction?.run) return;
  const before = install.counts().fitted, label = currentAction.label, carried = player.carry && player.carry.type;
  currentAction.run();
  const after = install.counts().fitted;
  // the sound of what just happened, read off the prompt that was pressed
  if (after > before) { snd.fit(); if (install.lastFit) fx.onFit(install.lastFit, player); }
  else if (/^Unwrap/.test(label)) snd.crinkle();
  else if (/pallet jack|pallet$|Set pallet/.test(label)) snd.jack();
  else if (/box|Put light|Pick up|Take|Dispose|Bag/.test(label)) snd.thud();
  snd.clock(clock.minute);
  updateRunLights(install);
  saveGame(clock, install);
}

function loop(now) {
  const dt = Math.min(0.05, (now - last) / 1000);
  if (window.game) { window.game.dbg.dt = dt; window.game.dbg.frames++; }
  last = now;
  resize();
  // the body: what it carries and whether it moves this frame set the drain
  const load = items.jack.held && items.jack.carrying ? 3 : (player.carry && player.carry.type !== 'wrap') || (items.jack.held) ? 2 : player.carry ? 1 : (lift.aboard ? 1 : 0);
  const moving = player.move.lengthSq() > 0.01 || ['KeyW', 'KeyA', 'KeyS', 'KeyD'].some((k) => player.keys.has(k)) || (lift.driving && (player.liftUp || player.liftDown));
  if (!clock.ended && document.body.classList.contains('playing')) body.update(dt, clock, load, moving);
  player.speedScale = body.speedScale();
  refreshObstacles(items, [lift].concat(crew.teams.map((t) => t.lift)));
  player.ignore = lift.aboard ? [lift, lift.box] : [player.carry];
  player.update(dt, world, collideWorld);
  const oldLift = lift.height;
  lift.update(dt, player, world, collideWorld);
  if (!lift.aboard) player.pos.y = world.floorY;   // no gravity to speak of: off the deck you are on the floor
  document.body.classList.toggle('aboard', lift.aboard);
  document.body.classList.toggle('driving', lift.driving);   // UP/DOWN only show at the controls
  document.body.classList.toggle('carrying', !!player.carry);
  snd.motor(Math.abs(lift.height - oldLift) > 0.002 || Math.abs(lift.speed) > 0.02, fx.level);
  snd.clock(clock.minute);
  if (!doorsWereOpen && !world.doorsShut) snd.door(); doorsWereOpen = !world.doorsShut;
  camera.position.set(player.pos.x, player.pos.y + player.eye, player.pos.z);
  camera.rotation.set(player.pitch, player.yaw, 0, 'YXZ');
  updateDoors(dt, world, (lift.aboard ? [lift.pos] : [player.pos]).concat(crew.points()));   // the parked lift does not hold the doors open
  if (document.body.classList.contains('playing') && !clock.ended) crew.update(dt, clock, player, install.counts().columnsDone);
  if (crew.toasts.length) showToast(crew.toasts.shift());
  if ((runLightTick += dt) > 1) { runLightTick = 0; updateRunLights(install); }   // the crew's fits light the room too
  fx.update(dt, clock, player, body);
  updateItems(player, lift, items);
  if (player.takeDrop() && !lift.anim) { dropCarry(player, items); snd.thud(); }
  currentAction = nearestAction(player, lift, install, items);
  if (player.takeAction()) interact();
  clock.update(dt);
  updateHud(document.querySelector('#stats'), document.querySelector('#prompt'), clock, install, currentAction, player.carry, body);
  if (clock.ended && !document.querySelector('#summary').classList.contains('up')) {
    const fittedTonight = install.counts().fitted - clock.fittedAtStart;
    clock.running = false;
    const clean = cleanupClear(items, lift); clean.left.push(...crew.leftInHall()); clean.ok = clean.left.length === 0;
    showSummary(document.querySelector('#summary'), document.querySelector('#summaryText'), clock, fittedTonight, clean);
    saveGame(clock, install);
  }
  renderer.render(scene, camera);
  requestAnimationFrame(loop);
}

document.querySelector('#start').addEventListener('click', startGame);
document.querySelector('#nextNight').addEventListener('click', () => {
  document.querySelector('#summary').classList.remove('up');
  resetForNight(player, lift, items);
  crew.resetForNight();
  clock.nextNight(install.counts().fitted);
  body.nextNight();
  snd.nextNight();
  document.querySelector('#overlay').classList.remove('gone');
  document.body.classList.remove('playing');
  saveGame(clock, install);
});

init().catch((err) => {
  console.error(err);
  document.querySelector('#prompt').textContent = 'Game failed to load. See console.';
});
