// (2026-09-08) The finale card as the tour leaves it: opens the page, presses Enter and Tour, seeks
// the tour to its last second and shoots the card on a desk (1280x800) and a phone (412x915).
//   node tools/finale-shot.mjs <outdir> [page] [tag]     (CDP_PORT, default 9334)
import { attach } from './cdp.mjs';
const [out, page = 'index.html', tag = 'finale'] = process.argv.slice(2);
const P = await attach({ port: +(process.env.CDP_PORT || 9334) });
for (const [w, h, name] of [[1280, 800, 'desk'], [412, 915, 'phone']]) {
  await P.send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: name === 'phone' });
  await P.open(page);
  await P.ev(`document.getElementById('tourbtn').click()`); await P.sleep(2500);
  await P.ev(`tourCtl.seek(tourCtl.state().total-0.8)`); await P.sleep(3500);
  console.log(name, await P.ev(`JSON.stringify(tourCtl.state())`));
  await P.shot(`${out}/${tag}-${name}.jpg`);
}
console.log(P.errors.join('\n') || 'no errors'); P.close(); process.exit(0);
