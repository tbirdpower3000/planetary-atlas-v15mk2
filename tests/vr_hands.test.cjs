// VR hands: do they keep working when the view changes, and do they recover by themselves?
//   node tests/vr_hands.test.cjs            (needs Playwright; THREE_DIR=<a three@0.128 package folder> to run offline)
// Opens the atlas in a phone-sized browser with a made-up camera and a stand-in hand finder (tests/fake-hands.mjs),
// goes into VR on Mars, and checks:
//   1. a held-up hand is seen on the globe;
//   2. after looking at "Solar System", the hand is still seen on the map, the finder was never handed a repeated
//      time and never threw (the fault fixed in v15mk2.61);
//   3. back on a globe and out to the map again, the same;
//   4. a finder that breaks is made afresh with the camera left open (v15mk2.62);
//   5. a camera that ends is opened again.
// Exit code 1 on any failed check.
const path = require('path'), fs = require('fs'), http = require('http');
const { chromium } = require('playwright');
const ROOT = path.join(__dirname, '..'), PORT = 8791, THREE_DIR = process.env.THREE_DIR || '';
const TYPES = { '.html': 'text/html', '.json': 'application/json', '.js': 'text/javascript', '.mjs': 'text/javascript', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp' };
const server = http.createServer((q, r) => {
  const f = path.join(ROOT, decodeURIComponent(q.url.split(/[?#]/)[0]).replace(/^\/$/, '/index.html'));
  if (!f.startsWith(ROOT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(r);
});
let failed = 0;
const ok = (name, pass, detail) => { if (!pass) failed++; console.log((pass ? '  ok   ' : '  FAIL ') + name + (detail !== undefined ? '  [' + detail + ']' : '')); };
(async () => {
  await new Promise((go) => server.listen(PORT, '127.0.0.1', go));
  const b = await chromium.launch({ args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const ctx = await b.newContext({ viewport: { width: 852, height: 393 }, permissions: ['camera'] }), p = await ctx.newPage();
  const errs = []; p.on('pageerror', (e) => errs.push(e.message));
  if (THREE_DIR) {
    await p.route('**/three.min.js', (r) => r.fulfill({ path: path.join(THREE_DIR, 'build/three.min.js'), contentType: 'text/javascript' }));
    await p.route('**/OrbitControls.js', (r) => r.fulfill({ path: path.join(THREE_DIR, 'examples/js/controls/OrbitControls.js'), contentType: 'text/javascript' }));
  }
  await p.route('**/vision_bundle.mjs', (r) => r.fulfill({ path: path.join(__dirname, 'fake-hands.mjs'), contentType: 'text/javascript' }));
  // The camera's clock is made to move on between any two readings, as it can on a phone between the two views' turns
  // in one frame. Without this the made-up camera hides the fault: both views would see "no new picture" and one would skip.
  await p.addInitScript(() => {
    window.__fake = { on: true, u: 0.5, v: 0.5 };
    const d = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, 'currentTime');
    Object.defineProperty(HTMLMediaElement.prototype, 'currentTime', { configurable: true, get() { return this.srcObject ? performance.now() / 1000 : d.get.call(this); }, set(v) { d.set.call(this, v); } });
  });
  await p.goto(`http://127.0.0.1:${PORT}/#mars`, { waitUntil: 'load' });
  await p.waitForFunction(() => window.VRM && document.getElementById('vrBtn'), null, { timeout: 60000 });
  const S = () => p.evaluate(() => { const s = VRM.state(); return Object.assign({ mode: s.mode }, s.hand, { mp: Object.assign({}, window.__mp) }); });
  const until = (fn, ms) => p.waitForFunction(fn, null, { timeout: ms || 20000 }).then(() => true, () => false);
  const seen = () => until(() => VRM.state().hand.ok, 8000);
  // looks up and down a little until the sign there is picked and the view changes
  const lookFor = async (mode, pitches) => {
    await p.evaluate(() => (window.__fake.on = false)); // hands down, so the hand does not pick anything by accident
    for (const q of pitches) { await p.evaluate((q) => (Array.isArray(q) ? VRM.look(q[0], q[1]) : VRM.look(0, q)), q); if (await until(`VRM.state().mode === '${mode}'`, 2800)) break; } // a number is a look up or down; a pair is [turn left, look up]
    await p.evaluate(() => { VRM.look(20, 5); window.__fake.on = true; });
    return (await S()).mode === mode;
  };
  await p.evaluate(() => document.getElementById('vrBtn').scrollIntoView({ block: 'center' }));
  await p.waitForTimeout(6000);
  await p.click('#vrBtn');
  ok('VR starts on the globe and the hands come on', await until(() => VRM.state().on && VRM.state().mode === 'globe' && VRM.state().hand.state === 'on', 30000));
  ok('1. a held-up hand is seen on the globe', await seen());

  ok('the Solar System sign takes you to the map', await lookFor('map', [[-32, 10], [-32, 8], [-32, 12], [-29, 10], [-35, 10]]));
  await p.waitForTimeout(2500); // past the fade from one view to the other
  let s = await S();
  ok('2. the hand is still seen on the map', await seen());
  ok('2. the finder was never handed the same time twice, and never threw', s.mp.repeats === 0 && s.mp.throws === 0, `repeats ${s.mp.repeats}, throws ${s.mp.throws}`);
  ok('2. nothing had to be restarted', s.restarts === 0 && s.remakes === 0 && s.mp.made === 1, `restarts ${s.restarts}, remakes ${s.remakes}, finders made ${s.mp.made}`);

  // back onto a world and out again: VRM.enter is the page's own way in, used by its VR buttons
  await p.evaluate(() => VRM.enter('globe')); await until(() => VRM.state().mode === 'globe', 15000); await p.waitForTimeout(2000);
  const again = await lookFor('map', [[-32, 10], [-32, 8], [-32, 12], [-29, 10], [-35, 10]]); await p.waitForTimeout(2500); s = await S();
  ok('3. globe, map, globe, map: the hand is still seen', again && (await seen()) && s.mp.throws === 0, `mode ${s.mode}, throws ${s.mp.throws}`);

  const cam = s.cam;
  await p.evaluate(() => (window.__fake.fail = true));
  const remade = await until(() => window.__mp.made >= 2 && VRM.state().hand.ok, 15000); s = await S();
  ok('4. a broken finder is made afresh and the hand is seen again', remade, `finders made ${s.mp.made}, remakes ${s.remakes}`);
  ok('4. the camera was left open while that happened', s.cam === cam && s.restarts === 0 && s.state === 'on', `restarts ${s.restarts}`);

  await p.evaluate(() => document.querySelectorAll('video').forEach((v) => v.srcObject && v.srcObject.getTracks().forEach((t) => t.stop())));
  const back = await until(() => VRM.state().hand.restarts >= 1 && VRM.state().hand.ok, 15000); s = await S();
  ok('5. a camera that ends is opened again and the hand is seen', back && s.cam !== cam, `restarts ${s.restarts}`);
  // 6. the signs at the sides of a world, and picking one with the hand (v15mk2.69)
  await p.evaluate(() => VRM.enter('globe')); await until(() => VRM.state().mode === 'globe', 15000);
  await p.evaluate(() => { VRM.look(0, 0); VRM.hand(0.5, 0.5, 0.9, 0.12); }); await p.waitForTimeout(600);
  const sides = await p.evaluate(() => VRM.state().signsAt);
  ok('6. with hands on, the action signs stand to the sides of the world (three each side), not stacked over it', (sides.match(/-32,/g) || []).length === 3 && (sides.match(/(^| )32,/g) || []).length === 3, sides);
  // sweep the stand-in hand to the right until it points at "+ Closer", then pinch
  let on = '';
  for (let u = 0.55; u <= 0.98 && !/Closer/.test(on); u += 0.01) for (const v of [0.5, 0.52, 0.48, 0.54, 0.46]) { await p.evaluate(([u, v]) => VRM.hand(u, v, 0.9, 0.12), [u, v]); await p.waitForTimeout(90); on = await p.evaluate(() => VRM.state().handOnSign); if (/Closer/.test(on)) { await p.evaluate(([u, v]) => (window.__uv = [u, v]), [u, v]); break; } }
  const d0 = await p.evaluate(() => VRM.state().dist);
  // (a pinch, and its release, must each be seen twice running before they count)
  for (const r of [0.2, 0.2, 0.2, 0.9, 0.9, 0.9]) { await p.evaluate((r) => VRM.hand(window.__uv[0], window.__uv[1], r, 0.12), r); await p.waitForTimeout(70); }
  await p.waitForTimeout(700);
  const d1 = await p.evaluate(() => VRM.state().dist);
  ok('6. pointing the hand at a sign lights it, and a pinch picks it (Closer brings the world nearer)', /Closer/.test(on) && d1 < d0 * 0.9, on + ' ' + d0 + ' -> ' + d1);
  await p.evaluate(() => VRM.hand(null));
  ok('no errors on the page', errs.length === 0, errs.slice(0, 3).join(' | ') || undefined);
  await b.close(); server.close();
  console.log(failed ? `${failed} check(s) failed.` : 'All VR hand checks passed.');
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
