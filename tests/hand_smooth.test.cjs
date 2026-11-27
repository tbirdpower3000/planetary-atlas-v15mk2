// The hand-control smoothing in index.html (steady and glide), tried on a made-up hand with the tracker's tremble.
//   node tests/hand_smooth.test.cjs
// The two functions are cut out of the page and run here, so the test is of the page's own code. Exit code 1 on failure.
const s = require('fs').readFileSync(require('path').join(__dirname, '..', 'index.html'), 'utf8');
const cut = (name) => { const i = s.indexOf('      function ' + name + '('); if (i < 0) throw new Error('no ' + name); let d = 0; for (let k = s.indexOf('{', i); ; k++) { if (s[k] === '{') d++; else if (s[k] === '}' && --d === 0) return s.slice(i, k + 1); } };
const { steady, glide } = new Function(cut('steady') + '\n' + cut('glide') + '\nreturn { steady, glide };')();
const num = (re) => +s.match(re)[1];
const SLOW = num(/const H_SLOW = ([\d.]+)/), FAST = num(/H_FAST = ([\d.]+)/), TAU = num(/glide\(hand\.fu, tu, ([\d.]+), dt\)/);
let failed = 0; const ok = (name, pass, got) => { if (!pass) failed++; console.log((pass ? '  ok   ' : '  FAIL ') + name + (got !== undefined ? '  [' + got + ']' : '')); };
let seed = 7; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647 - 0.5) * 2;
// the true hand: still for 1.5 s, a smooth sweep of 0.3 of the picture in 1 s, still again. Seen 30 times a second, 70 ms
// late, with +-0.4% tremble and two one-sighting spikes of 5%; drawn 60 times a second.
const truth = (t) => (t < 1500 ? 0.3 : t < 2500 ? 0.3 + 0.3 * (0.5 - 0.5 * Math.cos((Math.PI * (t - 1500)) / 1000)) : 0.6);
const run = (smooth) => { const f = steady(SLOW, FAST), g = { x: 0.3, v: 0 }; let u = 0.3, vu = 0, tS = 0; const out = [];
  for (let fr = 0; fr < 240; fr++) { const t = (fr * 1000) / 60;
    if (fr % 2 === 0) { let m = truth(t - 70) + rnd() * 0.004; if (fr === 60 || fr === 200) m += 0.05;
      if (smooth) { u = f.f(m, t); vu = f.speed; } else { const ds = (t - tS) / 1000; if (ds > 0 && ds < 0.2) vu += ((m - u) / ds - vu) * 0.5; u = m; } tS = t; }
    const target = u + vu * (Math.min(0.05, (t - tS) / 1000) + (smooth ? 0.04 : 0));
    out.push([t, smooth ? glide(g, target, TAU, 1 / 60) : target]); }
  return out; };
const steps = (o, a, b) => { const x = o.filter((r) => r[0] >= a && r[0] < b).map((r) => r[1]); return x.slice(1).map((v, i) => v - x[i]); };
const rms = (d) => Math.sqrt(d.reduce((p, q) => p + q * q, 0) / d.length), jerk = (d) => d.slice(1).reduce((p, v, i) => p + Math.abs(v - d[i]), 0) / (d.length - 1);
const lag = (o) => { let best = 0, bl = 1e9; for (let L = 0; L <= 250; L += 5) { const e = o.filter((r) => r[0] > 1500 && r[0] < 2700).reduce((p, r) => p + Math.abs(r[1] - truth(r[0] - L)), 0); if (e < bl) { bl = e; best = L; } } return best; };
const raw = run(false), sm = run(true);
ok('a still hand: the cursor shakes at least 15 times less', rms(steps(sm, 300, 1400)) * 15 < rms(steps(raw, 300, 1400)), (rms(steps(raw, 300, 1400)) / rms(steps(sm, 300, 1400))).toFixed(0) + ' times');
ok('a one-sighting spike of 5% moves the cursor less than 0.3%', Math.max(...steps(sm, 900, 1400).map(Math.abs)) < 0.003, (100 * Math.max(...steps(sm, 900, 1400).map(Math.abs))).toFixed(2) + '%');
ok('a moving hand: speed changes at least 3 times more gently', jerk(steps(sm, 1600, 2500)) * 3 < jerk(steps(raw, 1600, 2500)), (jerk(steps(raw, 1600, 2500)) / jerk(steps(sm, 1600, 2500))).toFixed(1) + ' times');
ok('the cursor is no more than 110 ms behind the true hand (70 of it the camera)', lag(sm) <= 110, lag(sm) + ' ms');
ok('the cursor ends on the hand', Math.abs(sm[sm.length - 1][1] - 0.6) < 0.004, sm[sm.length - 1][1].toFixed(4));
// an order: the view asked to turn half a radian in 15 parts, then left to finish
{ const g = { x: 0, v: 0 }; let want = 0, prev = 0, pd = 0, worst = 0, top = 0, past = 0;
  for (let fr = 0; fr < 150; fr++) { if (fr % 2 === 0 && fr < 30) want += 0.5 / 15; const x = glide(g, want, 0.11, 1 / 60, 2.6), d = x - prev; worst = Math.max(worst, Math.abs(d - pd)); pd = d; prev = x; top = Math.max(top, d * 60); if (x > want + 1e-9) past++; }
  ok('an order is carried out in full', Math.abs(g.x - 0.5) < 1e-3, g.x.toFixed(4));
  ok('...without ever passing what was asked', past === 0, past);
  ok('...with no sudden change of speed', worst < 0.004, worst.toFixed(4));
  const h = { x: 0, v: 0 }; let fast = 0, p2 = 0; for (let fr = 0; fr < 120; fr++) { const x = glide(h, 10, 0.11, 1 / 60, 2.6); fast = Math.max(fast, (x - p2) * 60); p2 = x; }
  ok('...and never faster than the top speed (2.6 a second)', fast <= 2.6 + 1e-6, fast.toFixed(2)); }
console.log(failed ? failed + ' check(s) failed.' : 'All hand smoothing checks passed.');
process.exit(failed ? 1 : 0);
