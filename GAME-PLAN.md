# The Install (game mode) — plan

Lloyd, 2026-09-04. A separate page, `game.html`, in this repo. It shares `model.glb` and `runs.json`
and NOTHING else with the viewer: `index.html` (the proposal page's iframe) is not touched. Until
Lloyd says otherwise this is a private link, never linked from the proposal page.

## The job being simulated

- 12 columns, N1..N6 along the wall row, S1..S6 the glass row. Column feet in the hall frame
  (u along the wall in metres, d into the room), from `index.html` EVENT.cols:
  `[7.71,3.82],[7.53,11.41],[14.94,3.86],[14.88,11.29],[22.3,3.86],[22.17,11.33],[29.67,3.77],
  [29.96,11.15],[37.18,3.84],[36.82,11.52],[44.54,3.80],[44.23,11.27]` (pairs: N,S per bay).
  Hall frame: origin (-54.907447, -1.43545, 3.040286), u = (0.975681, 0, 0.219196),
  inRoom = (0.219186, 0, -0.975639). Floor y = -1.435. Hall 48.9 m long (u 0..48.9), about 15 m
  deep (d 0..15; d=0 is the solid wall, d=15 the glazing). Ceiling ~12.2 m.
- Each column carries 8 vertical runs (`runs.json`, `column` N1..S6, 8 per column, each run a
  polyline from the floor to 11.43 m with a face `normal`). Each run takes 8 lights of 1.5 m,
  fitted bottom to top. So a column is 64 lights.
- Packaging: every light is bubble-wrapped; 8 lights to a box; 8 boxes to a pallet; one pallet
  per column (12 pallets). Pallets move by pallet jack. Boxes are carried one at a time. A light
  is unwrapped (wrap goes in a rubbish bag) then carried to the lift.
- Storage: a corridor OUTSIDE the hall at the far end (u = 48.9 end), with the 12 pallets, the
  scissor lift(s), the pallet jack and the rubbish bags. A skip sits outside past the corridor.
  The doorway into the hall is in the end wall, centred at d ≈ 7.5, 2.5 m wide, 3 m tall.
- Access window: 17:00 to 05:00. At 05:00 the hall must be EMPTY (lift, jack, pallets, boxes, wrap,
  bags all back in the corridor or the skip) or the night is failed. The job spans nights; the
  score is the number of nights. One in-game hour = one real minute.
- Fatigue: from 01:00 everything slows (walk, drive, fit); 03:00 more; 04:00 much more. From 03:00
  hallucinations: a light you just fitted is not there when you look back (it reappears a few
  seconds later), colours drift, the columns lean, a second lift appears across the hall, sound
  detunes. Harmless but unnerving.
- Crew: solo at first. After the prototype column (first column done) a helper joins: AI that
  does any task you did: pallet moves, unpacking, carrying to the lift, fitting. After a full
  column with the helper, a team of 2 joins with their own lift; teams copy the process. One
  scissor lift per 2-person team.

## Phase 1 (this build)

`game.html` + `game/` folder of ES modules, three r160 via the same import map as index.html.

- Load `model.glb`, find the floor from the mesh named floor / flat-floor (same rule as
  index.html: bounding box min y of that mesh), place everything on it. Collide the player and
  the lift against the columns and the hall bounds (simple: column feet as 0.55 m radius
  cylinders, room as a box, the doorway a gap in the end wall).
- First person. Desktop: WASD + mouse look (pointer lock), E to interact, F to drop, Space raises
  the lift when aboard, Shift lowers. Phone: two touch sticks (move left, look right) and one
  big ACTION button; the action button does what E does. Always a prompt on screen naming the
  action available ("Pick up box", "Unwrap light", "Get on lift", "Fit light", ...).
- Scissor lift: a drivable platform (3 m x 1.2 m deck, 1.1 m rails), driven with the move stick
  when aboard, deck raises to 12 m. Fitting a light: aboard, raised within 1.5 m of the next
  empty slot on a run of the nearest column, carrying an unwrapped light, press ACTION: the light
  snaps in, glows faintly. Lights are fitted bottom-up per run; the lift must be at the height.
- Pallet jack: walk to it, ACTION to take it, walk it under a pallet, ACTION to lift, drive the
  pallet, ACTION to set down. Box: ACTION on a pallet takes a box (8 lights); carried in front
  of the player; ACTION on the floor sets it down; ACTION on a box you stand at takes one wrapped
  light; ACTION with a wrapped light unwraps it (the wrap drops as a rubbish item); ACTION near a
  rubbish bag puts wrap in the bag; full bags and empty boxes go to the skip.
- The lift can carry ONE box (8 lights) on its deck: ACTION at the lift with a box puts it
  aboard; then aboard, ACTION takes a light from it, unwraps on the next ACTION, fits on the
  next. This is the fast loop and the game should let it be discovered.
- Clock HUD (top): the time, night number, lights fitted / 768, columns done, a fatigue meter
  after 01:00. End of night at 05:00: a summary card (fitted tonight, clean-up done or failed,
  nights so far), then "Next night" resets everything to the corridor with progress kept.
- The installed lights glow white (emissive), unlit slots draw nothing.
- Save progress in localStorage (night count, fitted slots) so a reload continues.
- No sound in phase 1 beyond a click on fit and a beep on the lift.
- Keep it fast on a phone: no shadows, one directional + hemisphere light, the GLB as is.

## Phase 2: fatigue + hallucinations. Phase 3: helper and team AI. Phase 4: sound.
