"""Atlas test bot (v15mk2).

Runs on GitHub (see .github/workflows/atlas-bot.yml) and writes a report to the job summary:
  1. Planet packs: every file in index.json opens, its grids and images decode, sizes.
  2. The page: loads, lands on Mars and comes back (the globe fades in inside the Solar System box), opens Earth,
     checks Earth's photo layers and live-data switches, the Moon's crater rings and a crater count, Mars through time, the Sources page, the real-time clock, and that there are no script errors.
  3. Live data: whether each source answers and whether it lets a web page read the answer (the CORS header).
     Report only; it never fails the run.
Exit code 1 if part 1 or 2 finds a problem.
"""
import asyncio, base64, json, os, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'bot-output'; OUT.mkdir(exist_ok=True)
PORT = 8765
LOCAL_LIBS = os.environ.get('ATLAS_LOCAL_LIBS')   # offline runs: a folder with three.min.js and OrbitControls.js
ORIGIN = 'https://tbirdpower3000.github.io'
problems, notes, rows = [], [], []

def problem(msg): problems.append(msg); print('PROBLEM:', msg, flush=True)

def check_packs():
    ix = json.loads((ROOT / 'index.json').read_text()); total = 0
    for e in ix:
        f = ROOT / Path(e['file']).name
        if not f.exists(): problem(f"{e['id']}: file {f.name} is missing"); continue
        mb = f.stat().st_size / 1e6; total += mb
        try: d = json.loads(f.read_text())
        except Exception as x: problem(f"{e['id']}: not valid JSON ({x})"); continue
        bad = [f'no {k}' for k in ('id', 'name', 'radiusKm') if k not in d]
        for g in d.get('grids', []):
            r, c = g.get('rows'), g.get('cols')
            try:
                n = len(base64.b64decode(g.get('b64') or g.get('data') or ''))
                if not r or not c or c != 2 * (r - 1) or n != r * c * 2: bad.append(f"grid {g.get('id')} is {r}x{c} with {n} bytes")
            except Exception as x: bad.append(f"grid {g.get('id')} won't decode ({x})")
        for im in d.get('images', []):
            if not im.get('src', '').startswith('data:image/') or len(im['src']) < 1000: bad.append(f"image {im.get('id')} looks empty")
        layers = len(d.get('grids', [])) + len(d.get('images', []))
        if not layers: bad.append('no layers')
        if bad: problem(f"{e['id']}: " + '; '.join(bad))
        rows.append((e['name'], f'{mb:.1f} MB', layers, 'ok' if not bad else 'problem'))
    notes.append(f'{len(ix)} packs, {total:.0f} MB in all.')

async def page_bot():
    from playwright.async_api import async_playwright
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
                                        executable_path=os.environ.get('ATLAS_CHROME') or None)
            pg = await b.new_page(viewport={'width': 1100, 'height': 800})
            if LOCAL_LIBS:
                async def route(r):
                    u = r.request.url
                    for k in ('three.min.js', 'OrbitControls.js'):
                        if u.endswith(k): return await r.fulfill(path=os.path.join(LOCAL_LIBS, k), content_type='application/javascript')
                    return await (r.continue_() if '127.0.0.1' in u else r.abort())
                await pg.route('**/*', route)
            errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            def step(name, ok, detail=''):
                print(('ok   ' if ok else 'FAIL ') + name, detail, flush=True)
                if not ok: problem(f'{name} {detail}'.strip())
            async def until(js, secs=25):
                t = time.time()
                while time.time() - t < secs:
                    if await pg.evaluate(js): return round(time.time() - t, 1)
                    await pg.wait_for_timeout(200)
                return None
            t0 = time.time()
            await pg.goto(f'http://127.0.0.1:{PORT}/index.html')
            await pg.wait_for_function('document.getElementById("busy").hidden', timeout=90000)
            notes.append(f'Page ready in {time.time() - t0:.1f} s (software graphics, so slower than a real computer).')
            step('Starts in real time', await pg.evaluate('(document.querySelector("#warp button[aria-pressed=true]")||{}).textContent==="▶ Real time"'))
            step('Clock shows the time of day', 'UTC' in await pg.inner_text('#mapDate'))
            await pg.evaluate('document.getElementById("mapStage").scrollIntoView({block:"start"})')
            await pg.evaluate('[...document.querySelectorAll("#mapLabels span")].find(s=>s.textContent==="Mars").click()')
            await pg.wait_for_timeout(1800)
            await pg.click('#mapGo'); t = await until('window.atlasDive&&window.atlasDive()==="mapStage"')
            step('Land on globe: the globe fades in inside the Solar System box', t is not None, f'({t} s)')
            await pg.wait_for_timeout(1500); await (await pg.query_selector('#mapStage')).screenshot(path=str(OUT / 'mars-landed.png'))
            await pg.click('#toMap'); t = await until('window.atlasDive&&window.atlasDive()===null')
            step('↑ Solar System fades back to the map', t is not None, f'({t} s)')
            await pg.evaluate('document.querySelector("#bodies button[data-id=earth]").click()')
            t = await until('document.getElementById("bName").textContent==="Earth"&&document.getElementById("busy").hidden', 40)
            step('Choosing Earth from the list opens it', t is not None, f'({t} s)')
            await pg.evaluate('document.getElementById("stage").scrollIntoView({block:"center"})'); await pg.wait_for_timeout(1500)
            step('Earth shows the live-data switches', await pg.evaluate('!document.getElementById("liveT").hidden'))
            lay = await pg.inner_text('#layerSeg')
            step('Earth has its photo layers', all(x in lay for x in ('Visible colour', 'Visible colour with clouds', 'Night lights')))
            await pg.evaluate("document.querySelector('#layerSeg button[data-id=visc]').click()"); await pg.wait_for_timeout(2000)
            await (await pg.query_selector('#stage')).screenshot(path=str(OUT / 'earth-clouds.png'))
            await pg.evaluate("document.querySelector('#layerSeg button[data-id=blend]').click()"); await pg.wait_for_timeout(2500)
            bl = await pg.evaluate('window.atlasBlend && window.atlasBlend()')
            step('Earth has Imagery + relief, built from its photo', bool(bl) and bl['layer'] == 'blend' and bl['w'] > 0, f"({bl and bl['w']}x{bl and bl['h']} from {bl and bl['base']})")
            # craters: the Moon's catalog streams in, draws rings, and a count of Mare Crisium gives a mare-like age
            await pg.evaluate('document.querySelector("#bodies button[data-id=moon]").click()')
            await until('document.getElementById("bName").textContent==="Moon"&&document.getElementById("busy").hidden', 40)
            await pg.wait_for_timeout(800)
            await pg.click('#crOn'); t = await until('window.atlasCraters&&window.atlasCraters().rings>0', 90)
            step('Moon craters stream in and draw', t is not None, f'({t} s)')
            await pg.select_option('#crR', '200'); await pg.evaluate('window.CR_TAP(17,59)'); await pg.wait_for_timeout(1500)
            c = await pg.evaluate('window.atlasCraters().last')
            step('Crater count of Mare Crisium gives a mare age (3.2-3.8 Ga)', bool(c) and 3.2 < c['T'] < 3.8, f"({c and round(c['T'], 2)} Ga from {c and c['n']} craters)")
            await (await pg.query_selector('#stage')).screenshot(path=str(OUT / 'moon-craters.png'))
            # Mars through time: the data streams in, Ancient Mars is a layer, and the Arabia ocean fills
            await pg.evaluate('document.querySelector("#bodies button[data-id=mars]").click()')
            await until('document.getElementById("bName").textContent==="Mars"&&document.getElementById("busy").hidden', 40)
            t = await until('window.atlasMars&&window.atlasMars().on', 60)
            step('Mars through time loads with Mars', t is not None and await pg.evaluate('!document.getElementById("mlab").hidden'), f'({t} s)')
            await pg.click('#mlAncGo'); await pg.wait_for_timeout(1500)
            m = await pg.evaluate('window.atlasMars()')
            step('Ancient Mars shows on the globe', m['layer'] == 'anc' and m['anc'], f"({m['overlays']} overlays)")
            await pg.check('#mlWater'); await pg.select_option('#mlWMode', 'arabia'); await pg.wait_for_timeout(3000)
            m = await pg.evaluate('window.atlasMars()')
            step('The northern ocean fills to the Arabia shoreline', m['water'] and abs(m['level'] + 2611) < 1, f"(sea level {m['level']} m)")
            await (await pg.query_selector('#stage')).screenshot(path=str(OUT / 'mars-ocean.png'))
            st = await pg.evaluate("fetch('sources.html').then(r=>r.status)")
            step('The project Sources page is there', st == 200, f'(HTTP {st})')
            step('No script errors', not errs, '; '.join(errs[:3]))
            await b.close()
    finally:
        srv.terminate()

def probe(name, url):
    req = urllib.request.Request(url, headers={'Origin': ORIGIN, 'User-Agent': 'planetary-atlas bot'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return (name, r.status, r.headers.get('Access-Control-Allow-Origin') or 'none')
    except urllib.error.HTTPError as x: return (name, x.code, x.headers.get('Access-Control-Allow-Origin') or 'none')
    except Exception as x: return (name, 'no answer', str(x)[:60])

def live():
    return [probe('OpenSky flights', 'https://opensky-network.org/api/states/all?lamin=45.8&lomin=5.9&lamax=47.8&lomax=10.5'),
            probe('CelesTrak satellites', 'https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE'),
            probe('adsb.lol flights', 'https://api.adsb.lol/v2/point/40.7/-74.0/100'),
            probe('adsb.fi flights', 'https://opendata.adsb.fi/api/v2/lat/40.7/lon/-74.0/dist/100')]

def report(live_rows):
    L = ['# Atlas test bot (v15mk2)', '', '**' + ('All checks passed.' if not problems else f'{len(problems)} problem(s) found.') + '**', '']
    if problems: L += ['## Problems', ''] + [f'- {p}' for p in problems] + ['']
    L += ['## Notes', ''] + [f'- {n}' for n in notes] + ['']
    L += ['## Live data (a web page can read it only if the CORS header allows it)', '', '| Source | Answer | CORS header |', '|---|---|---|'] + [f'| {a} | {b} | {c} |' for a, b, c in live_rows]
    L += ['', '## Planet packs', '', '| World | Size | Layers | Check |', '|---|---|---|---|'] + [f'| {a} | {b} | {c} | {d} |' for a, b, c, d in rows]
    text = '\n'.join(L) + '\n'; (OUT / 'report.md').write_text(text)
    if os.environ.get('GITHUB_STEP_SUMMARY'): open(os.environ['GITHUB_STEP_SUMMARY'], 'a').write(text)
    print(text)

if __name__ == '__main__':
    check_packs()
    try: asyncio.run(page_bot())
    except Exception as x: problem(f'The page test stopped early: {x}')
    report(live() if not os.environ.get('ATLAS_SKIP_LIVE') else [('live checks', 'skipped', '')])
    sys.exit(1 if problems else 0)
