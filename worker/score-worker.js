/**
 * Inglemoor football — score updater
 *
 * Runs on Cloudflare. Holds the GitHub token so it never reaches a phone.
 * The only thing it can change is `us` and `them` on a game that already
 * exists in index.html. It cannot touch anything else on the site.
 *
 * Secrets to set in the Cloudflare dashboard:
 *   ADMIN_PASSWORD   the shared password the board types
 *   GITHUB_TOKEN     fine-grained token, this repo only, Contents read+write
 *
 * Plain variables (not secrets):
 *   REPO_OWNER       inglemoor-football
 *   REPO_NAME        inglemoor-football.github.io
 *   ALLOWED_ORIGIN   https://inglemoor-football.github.io
 */

export default {
  async fetch(request, env) {
    const origin = env.ALLOWED_ORIGIN || "*";
    const cors = {
      "Access-Control-Allow-Origin": origin,
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      "Access-Control-Max-Age": "86400",
    };

    if (request.method === "OPTIONS") return new Response(null, { headers: cors });

    if (request.method !== "POST") {
      return json({ ok: false, error: "POST only" }, 405, cors);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ ok: false, error: "Could not read that request." }, 400, cors);
    }

    const { password, date, us, them } = body || {};

    // ---- password ----
    if (!password || !env.ADMIN_PASSWORD || !timingSafeEqual(password, env.ADMIN_PASSWORD)) {
      await new Promise(r => setTimeout(r, 700));      // slow down guessing
      return json({ ok: false, error: "Wrong password." }, 401, cors);
    }

    // ---- validate, strictly ----
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(date || ""))) {
      return json({ ok: false, error: "That date does not look right." }, 400, cors);
    }
    const a = Number(us), b = Number(them);
    if (!Number.isInteger(a) || !Number.isInteger(b) || a < 0 || b < 0 || a > 199 || b > 199) {
      return json({ ok: false, error: "Scores must be whole numbers between 0 and 199." }, 400, cors);
    }

    const owner = env.REPO_OWNER, repo = env.REPO_NAME, path = "index.html";
    const api = `https://api.github.com/repos/${owner}/${repo}/contents/${path}`;
    const gh = {
      "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
      "Accept": "application/vnd.github+json",
      "User-Agent": "inglemoor-score-updater",
    };

    // ---- read the current file ----
    const getRes = await fetch(api, { headers: gh });
    if (!getRes.ok) {
      return json({ ok: false, error: `Could not read the site file (${getRes.status}).` }, 502, cors);
    }
    const file = await getRes.json();
    const html = decodeB64(file.content);

    // ---- patch exactly one line ----
    const re = new RegExp(
      '^(\\s*\\{ date:"' + date + '"[^}]*?)(,\\s*us:\\s*-?\\d+\\s*,\\s*them:\\s*-?\\d+)?(\\s*\\},?)$',
      "m"
    );
    if (!re.test(html)) {
      return json({ ok: false, error: "No game on the schedule for that date." }, 404, cors);
    }
    const updated = html.replace(re, (m, head, old, tail) => `${head}, us:${a}, them:${b}${tail}`);

    if (updated === html) {
      return json({ ok: true, changed: false, message: "That score was already saved." }, 200, cors);
    }

    // safety net: a score edit must never change the file's shape
    if (Math.abs(updated.length - html.length) > 40 ||
        updated.split("\n").length !== html.split("\n").length) {
      return json({ ok: false, error: "Edit looked wrong, so nothing was saved." }, 500, cors);
    }

    // ---- write it back ----
    const putRes = await fetch(api, {
      method: "PUT",
      headers: { ...gh, "Content-Type": "application/json" },
      body: JSON.stringify({
        message: `Score: ${date} ${a}-${b}`,
        content: encodeB64(updated),
        sha: file.sha,
        branch: "main",
      }),
    });

    if (!putRes.ok) {
      const detail = await putRes.text();
      return json({ ok: false, error: `Save failed (${putRes.status}). ${detail.slice(0, 120)}` }, 502, cors);
    }

    return json({ ok: true, changed: true, message: `Saved ${a}–${b}. Live in about a minute.` }, 200, cors);
  },
};

/* ---------- helpers ---------- */

function json(obj, status, cors) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...cors, "Content-Type": "application/json" },
  });
}

// constant-time compare so response timing gives nothing away
function timingSafeEqual(x, y) {
  const a = new TextEncoder().encode(x), b = new TextEncoder().encode(y);
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
  return diff === 0;
}

function decodeB64(b64) {
  const bin = atob(b64.replace(/\n/g, ""));
  const bytes = Uint8Array.from(bin, c => c.charCodeAt(0));
  return new TextDecoder("utf-8").decode(bytes);
}

function encodeB64(str) {
  const bytes = new TextEncoder().encode(str);
  let bin = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  }
  return btoa(bin);
}
