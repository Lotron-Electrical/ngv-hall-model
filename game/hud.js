// (Claude, 2026-09-07) THE LEFT-HAND STACK. The four clock chips wrap to THREE rows on a phone,
// and everything under them was pinned at a fixed top written for one row: the stamina bars were
// drawn straight through "0 / 768 lights", and the inventory strip sat inside the UP button. So
// nothing below the chips has a fixed place any more. The block is measured each frame and the
// bars, the slots and the deck read are stacked under it, one row or three. Only a `top` that has
// actually moved is written, so the usual frame does no style work at all
function stackHud(stats) {
  if (!stats.offsetParent) return;             // the HUD is not on screen: nothing to measure
  const ghud = stats.parentElement;
  const put = (id, y) => { const e = document.getElementById(id); if (e && e.style.top !== y + 'px') e.style.top = y + 'px'; return e; };
  const y0 = ghud.offsetTop + stats.offsetHeight + 4;
  const bars = put('bars', y0);
  put('inv', y0 + (bars ? bars.offsetHeight : 0) + 4);
  // the deck read is right-aligned, so it shares the bars' row -- but it must clear the Crew and
  // Guide buttons, which are the tall half of the header on a desk
  put('deckh', Math.max(y0, ghud.offsetTop + ghud.offsetHeight + 4));
}

export function updateHud(el, prompt, clock, install, action, carry, body) {
  const c = install.counts();
  const bits = [
    `<span>${clock.timeText()}</span>`,
    `<span>Night ${clock.night}</span>`,
    `<span>${c.fitted} / ${c.total} lights</span>`,
    `<span>${c.columnsDone} columns done</span>`
  ];
  const line = bits.join('');
  if (el.__sig !== line) { el.__sig = line; el.innerHTML = line; }
  // the body: two bars, stamina (green, its ceiling shrinking as fatigue rises) and fatigue (orange)
  if (body) {
    const bars = document.getElementById('bars');
    if (bars) bars.innerHTML = `<div class="bar"><i style="width:${body.stamina.toFixed(0)}%"></i><b style="left:${body.max.toFixed(0)}%"></b><span>Stamina</span></div>`
      + `<div class="bar fat"><i style="width:${body.fatigue.toFixed(0)}%"></i><span>Fatigue: ${body.text()}</span></div>`;
  }
  stackHud(el);   // after the bars are written: their height is what the slots sit under
  const held = carry ? `<small>Holding ${carry.type}</small>` : '';
  prompt.innerHTML = `${action.label}${held}`;
  prompt.classList.toggle('can', !!action.run);
  prompt.hidden = !action.run && !action.hint;   // (Lloyd, 2026-09-05: "remove the no action nearby") the pill is up only when there is something to do, or something to say (a hint)
}

export function showSummary(root, textEl, clock, fittedTonight, clean) {
  const cleanText = clean.ok ? 'done' : `failed: ${clean.left.join(', ')} left in the hall`;
  textEl.innerHTML = `Fitted tonight: ${fittedTonight}<br>Clean-up: ${cleanText}<br>Nights so far: ${clock.night}`;
  root.classList.add('up');
}
