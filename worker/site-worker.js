/**
 * Inglemoor football — site backend
 *
 * Runs on Cloudflare. Does four things and nothing else:
 *   - writes a game score into index.html
 *   - stores photos and video in R2
 *   - lists what is stored for a game
 *   - serves those files back to the website
 *
 * Secrets:   ADMIN_PASSWORD, GITHUB_TOKEN
 * Variables: REPO_OWNER, REPO_NAME, ALLOWED_ORIGIN
 * Binding:   PHOTOS  ->  R2 bucket "inglemoor-photos"
 *
 * Reading is open, because the photos are public anyway.
 * Writing and deleting need the password.
 */

const MAX_UPLOAD = 80 * 1024 * 1024;          // 80 MB, enough for a short clip
const OK_TYPES = ["image/jpeg", "image/png", "image/webp", "video/mp4", "video/quicktime"];

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const action = url.searchParams.get("action") || "";
    const cors = {
      "Access-Control-Allow-Origin": env.ALLOWED_ORIGIN || "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, X-Auth",
      "Access-Control-Max-Age": "86400",
    };

    if (request.method === "OPTIONS") return new Response(null, { headers: cors });

    try {
      // ---------- public reads ----------
      if (request.method === "GET" && action === "img")    return serveFile(url, env);
      if (request.method === "GET" && action === "list")   return listGame(url, env, cors);
      if (request.method === "GET" && action === "counts") return allCounts(env, cors);

      // ---------- everything below needs the password ----------
      if (request.method !== "POST") {
        return json({ ok: false, error: "Not a valid request." }, 400, cors);
      }

      const given = (request.headers.get("X-Auth") || "").trim();
      const stored = (env.ADMIN_PASSWORD || "").trim();
      if (!stored) return json({ ok: false, error: "ADMIN_PASSWORD is not set on the Worker." }, 500, cors);
      if (given !== stored) {
        await new Promise(r => setTimeout(r, 700));
        return json({ ok: false, error: "Wrong password." }, 401, cors);
      }

      // lets the admin page check the password before showing anything
      if (action === "check")  return json({ ok: true }, 200, cors);
      if (action === "score")  return saveScore(request, env, cors);
      if (action === "upload") return upload(request, url, env, cors);
      if (action === "delete") return remove(url, env, cors);

      return json({ ok: false, error: "Unknown action." }, 400, cors);

    } catch (err) {
      return json({ ok: false, error: "Server error: " + (err && err.message) }, 500, cors);
    }
  },
};

/* ============================================================
   PHOTOS
   Keys look like:  photos/2026-09-05/1730altq3.jpg
                    thumbs/2026-09-05/1730altq3.jpg
                    hero/current.jpg
   ============================================================ */

async function serveFile(url, env) {
  const key = url.searchParams.get("key") || "";
  if (!safeKey(key)) return new Response("Bad key", { status: 400 });

  const obj = await env.PHOTOS.get(key);
  if (!obj) return new Response("Not found", { status: 404 });

  const headers = new Headers();
  obj.writeHttpMetadata(headers);
  headers.set("etag", obj.httpEtag);
  headers.set("Cache-Control", "public, max-age=31536000, immutable");
  headers.set("Access-Control-Allow-Origin", "*");
  return new Response(obj.body, { headers });
}

async function listGame(url, env, cors) {
  const game = url.searchParams.get("game") || "";
  if (!/^[\w-]{1,32}$/.test(game)) return json({ ok: false, error: "Bad game id." }, 400, cors);

  const listed = await env.PHOTOS.list({ prefix: `photos/${game}/`, include: ["customMetadata"] });
  const files = listed.objects.map(o => {
    const m = o.customMetadata || {};
    return {
      key: o.key,
      thumb: o.key.replace(/^photos\//, "thumbs/"),
      w: +m.w || 0,
      h: +m.h || 0,
      video: (m.kind === "video"),
      uploaded: o.uploaded,
    };
  }).sort((a, b) => String(a.key).localeCompare(String(b.key)));

  return json({ ok: true, game, files }, 200, cors);
}

async function allCounts(env, cors) {
  const listed = await env.PHOTOS.list({ prefix: "photos/", limit: 1000 });
  const counts = {};
  listed.objects.forEach(o => {
    const g = o.key.split("/")[1];
    if (g) counts[g] = (counts[g] || 0) + 1;
  });
  const hero = await env.PHOTOS.head("hero/current.jpg");
  return json({ ok: true, counts, hero: !!hero }, 200, cors);
}

async function upload(request, url, env, cors) {
  const game = url.searchParams.get("game") || "";
  const kind = url.searchParams.get("kind") || "photo";   // photo | thumb | hero
  const name = url.searchParams.get("name") || "";
  const type = request.headers.get("Content-Type") || "";
  const w = url.searchParams.get("w") || "0";
  const h = url.searchParams.get("h") || "0";
  const isVideo = url.searchParams.get("video") === "1";

  if (!OK_TYPES.includes(type.split(";")[0])) {
    return json({ ok: false, error: "That file type is not allowed." }, 400, cors);
  }
  if (kind !== "hero" && !/^[\w-]{1,32}$/.test(game)) {
    return json({ ok: false, error: "Bad game id." }, 400, cors);
  }
  if (!/^[\w][\w.-]{0,60}$/.test(name)) {
    return json({ ok: false, error: "Bad file name." }, 400, cors);
  }

  const body = await request.arrayBuffer();
  if (body.byteLength === 0) return json({ ok: false, error: "Empty file." }, 400, cors);
  if (body.byteLength > MAX_UPLOAD) {
    return json({ ok: false, error: "That file is too large. Limit is 80 MB." }, 413, cors);
  }

  let key;
  if (kind === "hero")      key = "hero/current.jpg";
  else if (kind === "thumb") key = `thumbs/${game}/${name}`;
  else                       key = `photos/${game}/${name}`;

  await env.PHOTOS.put(key, body, {
    httpMetadata: { contentType: type.split(";")[0] },
    customMetadata: { w, h, kind: isVideo ? "video" : "image" },
  });

  return json({ ok: true, key }, 200, cors);
}

async function remove(url, env, cors) {
  const key = url.searchParams.get("key") || "";
  if (!safeKey(key)) return json({ ok: false, error: "Bad key." }, 400, cors);
  await env.PHOTOS.delete(key);
  await env.PHOTOS.delete(key.replace(/^photos\//, "thumbs/"));   // its thumbnail too
  return json({ ok: true }, 200, cors);
}

function safeKey(k) {
  return /^(photos|thumbs)\/[\w-]{1,32}\/[\w][\w.-]{0,60}$/.test(k) || k === "hero/current.jpg";
}

/* ============================================================
   SCORES
   ============================================================ */

async function saveScore(request, env, cors) {
  let body;
  try { body = await request.json(); }
  catch { return json({ ok: false, error: "Could not read that request." }, 400, cors); }

  const { date, us, them } = body || {};
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(date || ""))) {
    return json({ ok: false, error: "That date does not look right." }, 400, cors);
  }
  const a = Number(us), b = Number(them);
  if (!Number.isInteger(a) || !Number.isInteger(b) || a < 0 || b < 0 || a > 199 || b > 199) {
    return json({ ok: false, error: "Scores must be whole numbers between 0 and 199." }, 400, cors);
  }
  if (!env.GITHUB_TOKEN) return json({ ok: false, error: "GITHUB_TOKEN is missing." }, 500, cors);

  const api = `https://api.github.com/repos/${env.REPO_OWNER}/${env.REPO_NAME}/contents/index.html`;
  const gh = {
    "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
    "Accept": "application/vnd.github+json",
    "User-Agent": "inglemoor-site-worker",
  };

  const getRes = await fetch(api, { headers: gh });
  if (!getRes.ok) return json({ ok: false, error: `Could not read the site file (${getRes.status}).` }, 502, cors);
  const file = await getRes.json();
  const html = decodeB64(file.content);

  const re = new RegExp(
    '^(\\s*\\{ date:"' + date + '"[^}]*?)(,\\s*us:\\s*-?\\d+\\s*,\\s*them:\\s*-?\\d+)?(\\s*\\},?)$',
    "m"
  );
  if (!re.test(html)) return json({ ok: false, error: "No game on the schedule for that date." }, 404, cors);

  const updated = html.replace(re, (m, head, old, tail) => `${head}, us:${a}, them:${b}${tail}`);
  if (updated === html) return json({ ok: true, changed: false, message: "That score was already saved." }, 200, cors);

  if (Math.abs(updated.length - html.length) > 40 ||
      updated.split("\n").length !== html.split("\n").length) {
    return json({ ok: false, error: "Edit looked wrong, so nothing was saved." }, 500, cors);
  }

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
    return json({ ok: false, error: `Save failed (${putRes.status}). ${detail.slice(0, 140)}` }, 502, cors);
  }

  return json({ ok: true, changed: true, message: `Saved ${a}–${b}. Live in about a minute.` }, 200, cors);
}

/* ---------- helpers ---------- */

function json(obj, status, cors) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...cors, "Content-Type": "application/json" },
  });
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
