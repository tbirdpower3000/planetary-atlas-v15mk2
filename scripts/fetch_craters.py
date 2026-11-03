"""Fetch lunar crater catalogs that are only published inside large archives, and pack them for the atlas.

Runs on GitHub Actions (see .github/workflows/fetch-craters.yml). Writes craters/*.json in the atlas's compact
crater format: int16 lat*360, int16 lon*180 (east, -180..180), uint16 diameter km*20, little-endian, base64,
sorted by diameter, largest first.

Povilaitis et al. (2018): six LROC shapefile ZIPs of about 320 MB each. Only the attribute table (.dbf, which holds
each crater's centre and diameter) is read, using HTTP range requests, so a few MB are downloaded per part instead of
the polygon outlines.
Head et al. (2010): the LOLA large-crater catalog (craters >= 20 km), a CSV on Brown University's site.
"""
import base64, json, re, struct, sys, urllib.parse, urllib.request, zlib, datetime

UA = 'planetary-modeling-atlas crater fetcher (github.com/tbirdpower3000/planetary-atlas-v15mk2)'
TODAY = datetime.date.today().isoformat()
LOG = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def get(url, rng=None, referer=None):
    h = {'User-Agent': UA}
    if rng:
        h['Range'] = 'bytes=%d-%d' % rng
    if referer:
        h['Referer'] = referer
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=120) as r:
        return r.status, dict(r.headers), r.read()


def pack(world, lat, lon, d, source, extra=None):
    order = sorted(range(len(d)), key=lambda i: -d[i])
    la = struct.pack('<%dh' % len(order), *[max(-32767, min(32767, round(lat[i] * 360))) for i in order])
    lo = struct.pack('<%dh' % len(order), *[round((((lon[i] + 180) % 360) - 180) * 180) for i in order])
    dd = struct.pack('<%dH' % len(order), *[min(65535, round(d[i] * 20)) for i in order])
    out = {'kind': 'atlas-craters', 'world': world, 'n': len(order), 'order': 'diameter, largest first',
           'scale': {'lat': 360, 'lon': 180, 'd': 20},
           'note': 'int16 lat*360, int16 lon*180 (east, -180..180), uint16 diameter km*20; little-endian, base64',
           'source': source, 'lat': base64.b64encode(la).decode(), 'lon': base64.b64encode(lo).decode(),
           'd': base64.b64encode(dd).decode()}
    if extra:
        out.update({k: [v[i] for i in order] if isinstance(v, list) else v for k, v in extra.items()})
    return out


# ---------- zip over HTTP range requests ----------
def zip_entries(url, referer):
    st, h, b = get(url, (0, 3), referer)
    if st != 206 or b[:2] != b'PK':
        raise RuntimeError(f'no range support or not a zip (status {st}, first bytes {b[:8]!r}, type {h.get("Content-Type")})')
    total = int(h['Content-Range'].split('/')[1])
    tail = get(url, (max(0, total - 65536), total - 1), referer)[2]
    e = tail.rfind(b'PK\x05\x06')
    n, cdsize, cdoff = struct.unpack('<HII', tail[e + 10:e + 20])
    if cdoff == 0xFFFFFFFF:  # zip64
        l = tail.rfind(b'PK\x06\x06')
        n, cdsize, cdoff = struct.unpack('<QQQ', tail[l + 32:l + 56])
    cd = get(url, (cdoff, cdoff + cdsize - 1), referer)[2]
    out, p = [], 0
    for _ in range(n):
        meth, = struct.unpack('<H', cd[p + 10:p + 12])
        csz, usz, nl, xl, cl = struct.unpack('<IIHHH', cd[p + 20:p + 34])
        lho, = struct.unpack('<I', cd[p + 42:p + 46])
        name = cd[p + 46:p + 46 + nl].decode('utf-8', 'replace')
        if 0xFFFFFFFF in (csz, usz, lho):  # zip64 extra field
            x = cd[p + 46 + nl:p + 46 + nl + xl]
            q = 0
            while q < len(x):
                tag, sz = struct.unpack('<HH', x[q:q + 4])
                if tag == 1:
                    vals = list(struct.unpack('<%dQ' % (sz // 8), x[q + 4:q + 4 + sz]))
                    if usz == 0xFFFFFFFF: usz = vals.pop(0)
                    if csz == 0xFFFFFFFF: csz = vals.pop(0)
                    if lho == 0xFFFFFFFF: lho = vals.pop(0)
                q += 4 + sz
        out.append(dict(name=name, meth=meth, csz=csz, usz=usz, lho=lho))
        p += 46 + nl + xl + cl
    return out, total


def zip_read(url, ent, referer):
    lh = get(url, (ent['lho'], ent['lho'] + 29), referer)[2]
    nl, xl = struct.unpack('<HH', lh[26:30])
    start = ent['lho'] + 30 + nl + xl
    raw = get(url, (start, start + ent['csz'] - 1), referer)[2]
    return raw if ent['meth'] == 0 else zlib.decompress(raw, -15)


def dbf(b):
    n, hl, rl = struct.unpack('<IHH', b[4:12])
    fields, p = [], 32
    while b[p] != 0x0D:
        name = b[p:p + 11].split(b'\0')[0].decode()
        fields.append((name, chr(b[p + 11]), b[p + 16]))
        p += 32
    rows = []
    for k in range(n):
        r = b[hl + k * rl:hl + (k + 1) * rl]
        if r[:1] == b'*':
            continue  # deleted
        q, row = 1, {}
        for name, t, ln in fields:
            row[name] = r[q:q + ln].decode('latin-1').strip()
            q += ln
        rows.append(row)
    return fields, rows


def povilaitis():
    parts = ['0TO90E', '90ETO180E', '0TO90W', '90WTO180W', 'NPOLE', 'SPOLE']
    base = 'https://pds.lroc.im-ldi.com/data/LRO-L-LROC-5-RDR-V1.0/LROLRC_2001/EXTRAS/SHAPEFILE/'
    lat, lon, d, q = [], [], [], []
    for part in parts:
        ref = f'https://data.lroc.im-ldi.com/lroc/view_rdr/SHAPEFILE_LROC_5TO20KM_CRATERS_{part}'
        got = False
        for suffix in ('_180.ZIP', '.ZIP', '_360.ZIP'):
            url = f'{base}LROC_5TO20KM_CRATERS_{part}/LROC_5TO20KM_CRATERS_{part}{suffix}'
            try:
                ents, total = zip_entries(url, ref)
            except Exception as e:
                log(f'  {part}{suffix}: {e}')
                continue
            dbfs = [e for e in ents if e['name'].upper().endswith('.DBF')]
            log(f'  {part}{suffix}: {total / 1e6:.0f} MB zip, entries: ' + ', '.join(f"{e['name']} ({e['usz'] / 1e6:.1f} MB)" for e in ents))
            for ent in dbfs:
                fields, rows = dbf(zip_read(url, ent, ref))
                log(f'    {ent["name"]}: {len(rows)} rows, fields {[f[0] for f in fields]}')
                for r in rows:
                    r = {k.upper(): v for k, v in r.items()}  # the tables spell the fields Diam_km, x_coord, y_coord, tag
                    try:
                        x, y, dk = float(r['X_COORD']), float(r['Y_COORD']), float(r['DIAM_KM'])
                    except (KeyError, ValueError):
                        continue
                    lat.append(y); lon.append(x); d.append(dk); q.append(1 if '?' in r.get('TAG', '') else 0)
            got = bool(dbfs)
            if got:
                break
        if not got:
            log(f'  {part}: NOT FETCHED')
    log(f'Povilaitis total: {len(d)} craters, {sum(q)} marked questionable')
    if d:
        src = ('Povilaitis, R. Z., Robinson, M. S., van der Bogert, C. H., Hiesinger, H., Meyer, H. M., & Ostrach, L. R. (2018). '
               'Crater density differences: Exploring regional resurfacing, secondary crater populations, and crater saturation '
               'equilibrium on the moon. Planetary and Space Science 162, 41-51, doi:10.1016/j.pss.2017.05.006. '
               f'LROC 5-20 km crater shapefiles (attribute tables only), retrieved {TODAY}.')
        json.dump(pack('moon', lat, lon, d, src, {'questionable': q}), open('craters/craters-moon-povilaitis2018.json', 'w'),
                  separators=(',', ':'))


def head2010():
    page = 'http://www.planetary.brown.edu/html_pages/LOLAcraters.html'
    try:
        html = get(page)[2].decode('latin-1')
    except Exception as e:
        log(f'Head 2010: page not reachable: {e}')
        return
    links = re.findall(r'href="([^"]+\.csv)"', html, re.I)
    log(f'Head 2010: csv links {links}')
    if not links:
        return
    url = urllib.parse.urljoin(page, links[0])
    txt = get(url)[2].decode('latin-1')
    lines = [l for l in txt.splitlines() if l.strip()]
    hdr = [h.strip().lower() for h in lines[0].split(',')]
    log(f'Head 2010: header {hdr}, {len(lines) - 1} rows')
    find = lambda *keys: next(i for i, h in enumerate(hdr) if any(k in h for k in keys))
    ix, iy, idm = find('lon'), find('lat'), find('diam')
    lat, lon, d = [], [], []
    for l in lines[1:]:
        c = l.split(',')
        try:
            lon.append(float(c[ix])); lat.append(float(c[iy])); d.append(float(c[idm]))
        except (ValueError, IndexError):
            pass
    src = ('Head, J. W., Fassett, C. I., Kadish, S. J., Smith, D. E., Zuber, M. T., Neumann, G. A., & Mazarico, E. (2010). '
           'Global distribution of large lunar craters: Implications for resurfacing and impactor populations. Science 329, '
           f'1504-1507, doi:10.1126/science.1195050. LolaLargeLunarCraterCatalog.csv from Brown University, retrieved {TODAY}.')
    json.dump(pack('moon', lat, lon, d, src), open('craters/craters-moon-head2010.json', 'w'), separators=(',', ':'))
    log(f'Head 2010: {len(d)} craters')


if __name__ == '__main__':
    import os
    os.makedirs('craters', exist_ok=True)
    for f in (povilaitis, head2010):
        try:
            f()
        except Exception as e:
            log(f'{f.__name__} failed: {e!r}')
    open('craters/fetch-log.txt', 'w').write('\n'.join(LOG) + '\n')
