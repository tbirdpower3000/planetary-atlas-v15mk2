// Live-flight relay for the Planetary Modeling Atlas, as a Cloudflare Worker (free plan is plenty).
//
// Why: the OpenSky Network doesn't let other websites read its data, so a browser page can't fetch it. This Worker
// fetches it for the page and adds the permission header (CORS) that lets the atlas read it, with no delay beyond
// OpenSky's own. It only answers the sites listed in ALLOW, so nobody else can use up your OpenSky allowance.
//
// Optional but recommended: a free OpenSky account. Anonymous use allows about 100 worldwide snapshots a day (one
// every 15 minutes); with an account it is about 1,000 a day (one every 2 minutes) at 5-second resolution.
// Add your OpenSky API client as two secrets in the Worker's Settings → Variables and Secrets:
//   OPENSKY_CLIENT_ID     and     OPENSKY_CLIENT_SECRET
//
// The atlas reads the same format OpenSky returns (/api/states/all), so nothing else needs changing.

const ALLOW = [
  'https://tbirdpower3000.github.io', // the atlas on GitHub Pages
  'null', // the atlas opened as a downloaded file
];

let last = null; // the latest snapshot, shared by everyone this Worker serves
let token = null; // OpenSky access token, renewed before it expires (they last 30 minutes)

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const cors = {
      'Access-Control-Allow-Origin': ALLOW.includes(origin) ? origin : ALLOW[0],
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      Vary: 'Origin',
    };
    if (request.method === 'OPTIONS') return new Response(null, { headers: cors });
    if (origin && !ALLOW.includes(origin)) return new Response('Not allowed for this site', { status: 403, headers: cors });

    const authed = !!(env.OPENSKY_CLIENT_ID && env.OPENSKY_CLIENT_SECRET);
    const keepFor = (authed ? 120 : 900) * 1000; // stays inside OpenSky's daily allowance
    if (!last || Date.now() - last.at > keepFor) {
      try {
        const headers = { 'User-Agent': 'planetary-atlas-relay' };
        if (authed) headers.Authorization = 'Bearer ' + (await getToken(env));
        const up = await fetch('https://opensky-network.org/api/states/all', { headers });
        if (up.status === 429 && last) {
          // allowance used up for today: keep serving the last snapshot
        } else if (!up.ok) {
          throw new Error('OpenSky answered ' + up.status);
        } else {
          last = { at: Date.now(), body: await up.text() };
        }
      } catch (e) {
        if (!last) return json({ error: String(e.message || e) }, 502, cors);
      }
    }
    return new Response(last.body, {
      headers: { ...cors, 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'X-Snapshot-Age': String(Math.round((Date.now() - last.at) / 1000)) },
    });
  },
};

async function getToken(env) {
  if (token && token.until > Date.now()) return token.value;
  const r = await fetch('https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ grant_type: 'client_credentials', client_id: env.OPENSKY_CLIENT_ID, client_secret: env.OPENSKY_CLIENT_SECRET }),
  });
  if (!r.ok) throw new Error('OpenSky sign-in failed (' + r.status + '): check the two secrets');
  const j = await r.json();
  token = { value: j.access_token, until: Date.now() + ((j.expires_in || 1800) - 120) * 1000 };
  return token.value;
}

const json = (o, status, cors) => new Response(JSON.stringify(o), { status, headers: { ...cors, 'Content-Type': 'application/json' } });
