// Load a page on the :8877 server (install mode, cache off) and print every console error and
// uncaught exception after N seconds.   node tools/page-errors.mjs [page] [seconds]   (CDP_PORT 9334)
import { attach } from './cdp.mjs';
const [page = 'index.html', secs = '10'] = process.argv.slice(2);
const P = await attach({ port: +(process.env.CDP_PORT || 9334) });
await P.send('Network.setCacheDisabled', { cacheDisabled: true });
await P.send('Page.navigate', { url: 'http://127.0.0.1:8877/' + page + '?install=gandel-2026' });
await P.sleep(+secs * 1000);
const has = await P.ev('typeof window.ngv').catch(e => 'eval-failed ' + e.message);
console.log('typeof ngv:', has);
console.log(P.errors.length ? P.errors.join('\n') : 'no errors captured');
P.close(); process.exit(0);
