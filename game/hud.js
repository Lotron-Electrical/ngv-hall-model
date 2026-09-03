export function updateHud(el, prompt, clock, install, action, carry) {
  const c = install.counts();
  const bits = [
    `<span>${clock.timeText()}</span>`,
    `<span>Night ${clock.night}</span>`,
    `<span>${c.fitted} / ${c.total} lights</span>`,
    `<span>${c.columnsDone} columns done</span>`
  ];
  if (clock.minute >= 25 * 60) bits.push(`<span>Fatigue ${clock.fatigueText()}</span>`);
  el.innerHTML = bits.join('');
  const held = carry ? `<small>Holding ${carry.type}</small>` : '';
  prompt.innerHTML = `${action.label}${held}`;
}

export function showSummary(root, textEl, clock, fittedTonight, clean) {
  const cleanText = clean.ok ? 'done' : `failed: ${clean.left.join(', ')} left in the hall`;
  textEl.innerHTML = `Fitted tonight: ${fittedTonight}<br>Clean-up: ${cleanText}<br>Nights so far: ${clock.night}`;
  root.classList.add('up');
}
