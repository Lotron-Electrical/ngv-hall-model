export function updateHud(el, prompt, clock, install, action, carry, body) {
  const c = install.counts();
  const bits = [
    `<span>${clock.timeText()}</span>`,
    `<span>Night ${clock.night}</span>`,
    `<span>${c.fitted} / ${c.total} lights</span>`,
    `<span>${c.columnsDone} columns done</span>`
  ];
  el.innerHTML = bits.join('');
  // the body: two bars, stamina (green, its ceiling shrinking as fatigue rises) and fatigue (orange)
  if (body) {
    const bars = document.getElementById('bars');
    if (bars) bars.innerHTML = `<div class="bar"><i style="width:${body.stamina.toFixed(0)}%"></i><b style="left:${body.max.toFixed(0)}%"></b><span>Stamina</span></div>`
      + `<div class="bar fat"><i style="width:${body.fatigue.toFixed(0)}%"></i><span>Fatigue: ${body.text()}</span></div>`;
  }
  const held = carry ? `<small>Holding ${carry.type}</small>` : '';
  prompt.innerHTML = `${action.label}${held}`;
  prompt.classList.toggle('can', !!action.run);
}

export function showSummary(root, textEl, clock, fittedTonight, clean) {
  const cleanText = clean.ok ? 'done' : `failed: ${clean.left.join(', ')} left in the hall`;
  textEl.innerHTML = `Fitted tonight: ${fittedTonight}<br>Clean-up: ${cleanText}<br>Nights so far: ${clock.night}`;
  root.classList.add('up');
}
