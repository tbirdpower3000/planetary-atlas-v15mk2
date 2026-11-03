"""Live-flight snapshot for the atlas. Browsers can't read the free flight feeds directly (none of them allows other
websites), so this GitHub job reads one worldwide snapshot every few minutes and publishes it as flights.json on the
repo's `live` branch, which raw.githubusercontent.com serves to any website. The format is OpenSky's own /states/all
(trimmed to the fields the atlas uses), so the page reads it the same way."""
import json, os, time, urllib.parse, urllib.request, sys

UA = 'planetary-modeling-atlas live-flight relay (github.com/tbirdpower3000/planetary-atlas-v15mk2)'


def get(url, timeout=60, headers=None):
    h = {'User-Agent': UA, 'Accept': 'application/json', **(headers or {})}
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        return json.load(r)


def opensky_token():
    """With the repo secrets OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET set, sign in to OpenSky (10x the daily
    allowance and sharper data); without them the job stays anonymous."""
    cid, sec = os.environ.get('OPENSKY_CLIENT_ID'), os.environ.get('OPENSKY_CLIENT_SECRET')
    if not (cid and sec):
        return None
    body = urllib.parse.urlencode({'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': sec}).encode()
    req = urllib.request.Request('https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token', data=body,
                                 headers={'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)['access_token']
    except Exception as e:
        print('OpenSky sign-in failed, staying anonymous:', repr(e), flush=True)
        return None


def opensky():
    tok = opensky_token()
    j = get('https://opensky-network.org/api/states/all', headers={'Authorization': 'Bearer ' + tok} if tok else None)
    st = []
    for v in j.get('states') or []:
        if v[5] is None or v[6] is None or v[8]:
            continue  # no position, or on the ground
        r = lambda x, n: None if x is None else round(x, n)
        # icao24, callsign, country, time_position, last_contact, lon, lat, baro_alt, on_ground, velocity, track, vertical_rate, sensors, geo_alt
        st.append([v[0], (v[1] or '').strip(), v[2], v[3], v[4], r(v[5], 4), r(v[6], 4), r(v[7], 0), False, r(v[9], 1), r(v[10], 1), r(v[11], 1), None, r(v[13], 0)])
    return {'time': j.get('time') or int(time.time()), 'source': 'OpenSky Network (opensky-network.org), ' + ('signed-in' if tok else 'anonymous') + ' /states/all', 'states': st}


def airplaneslive():
    # fallback: a ring of 250 nm queries is too many for one run, so only the busiest regions
    pts = [(40, -100), (50, 10), (35, 120), (25, 50), (-25, 135), (-15, -50), (60, -120), (45, 75)]
    st, seen = [], set()
    for la, lo in pts:
        try:
            j = get(f'https://api.airplanes.live/v2/point/{la}/{lo}/250')
        except Exception as e:
            print('airplanes.live', la, lo, e, flush=True)
            continue
        for a in j.get('ac', []):
            if a.get('lat') is None or a.get('alt_baro') == 'ground' or a['hex'] in seen:
                continue
            seen.add(a['hex'])
            ft = lambda x: None if not isinstance(x, (int, float)) else round(x * 0.3048, 0)
            st.append([a['hex'], (a.get('flight') or '').strip(), a.get('t') or '', None, None, round(a['lon'], 4), round(a['lat'], 4), ft(a.get('alt_baro')), False,
                       round((a.get('gs') or 0) * 0.514444, 1), a.get('track'), round((a.get('baro_rate') or 0) * 0.00508, 1), None, ft(a.get('alt_geom'))])
        time.sleep(1.1)
    return {'time': int(time.time()), 'source': 'airplanes.live (regional queries; OpenSky was unavailable)', 'states': st}


out = None
for f in (opensky, airplaneslive):
    try:
        out = f()
        print(f.__name__, len(out['states']), 'aircraft', flush=True)
        if len(out['states']) > 100:
            break
    except Exception as e:
        print(f.__name__, 'failed:', repr(e), flush=True)
if not out or not out['states']:
    sys.exit('no flight source answered')
json.dump(out, open('flights.json', 'w'), separators=(',', ':'))
print('wrote flights.json', round(len(open('flights.json').read()) / 1e6, 2), 'MB', flush=True)
