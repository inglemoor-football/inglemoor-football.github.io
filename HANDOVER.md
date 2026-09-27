# Inglemoor Football — Project Handover

Everything a new chat needs to pick this up cold.
Written 2026-09-27 at v0.9.39, updated for **v0.9.40** (Spirit Wear cards + booster shop QR).

---

## 1. What this is

The website for **Inglemoor High School Viking football** and the IHS Viking
Gridiron Booster Club, in Kenmore, WA. Graham Comley runs it as a booster
volunteer (board role: "Spiritwear & Website").

It replaced a Sports Connect site. It is deliberately **one self-contained
`index.html`** — no build step, no framework, no dependencies, no database.
All editable content lives in a `SITE` object in the first ~380 lines.
Everything below that is styling and render logic.

The reason for that design: the board turns over. Whoever inherits this needs
to be able to open one file, find a commented block, change some text, and
commit. Keep it that way.

---

## 2. Links — all copyable

**Site**
- Live site: https://inglemoorfootball.com
- Admin page: https://inglemoorfootball.com/admin.html
- Repo: https://github.com/inglemoor-football/inglemoor-football.github.io
- Raw index.html (for checking live state):
  https://raw.githubusercontent.com/inglemoor-football/inglemoor-football.github.io/main/index.html
- Actions tab: https://github.com/inglemoor-football/inglemoor-football.github.io/actions

**Backend**
- Worker endpoint: https://inglemoor-scores.grahamcomley.workers.dev
- Worker name: `inglemoor-scores` (Cloudflare, Graham's personal account)
- R2 bucket: `inglemoor-photos`, bound into the Worker as `PHOTOS`

**Outbound links the site uses**
- Booster shop (Zeffy): https://www.zeffy.com/en-US/ticketing/2025-viking-booster-shop
- Team gear: https://inglemoorvikingsfootball.fusion-brands.com/
- Booster dues: https://www.zeffy.com/en-US/ticketing/2026-booster-dues-2
- Donate: https://www.zeffy.com/en-US/donation-form/075378d9-5861-44b8-88a9-2759636a8055
- Volunteer: https://www.signupgenius.com/go/70A0D49AFA628AAF94-62398519-season#/
- Tickets: https://gofan.co/school/WA23232
- Stream: https://www.nfhsnetwork.com/schools/inglemoor-high-school-kenmore-wa
- Instagram: https://www.instagram.com/inglemoorfootball/
- Facebook: https://www.facebook.com/ihsvikingfootballboosters/
- Junior program: https://www.inglemoorvikings.org/

**Accounts**
- Domain: GoDaddy, paid through August 2034
- Calendar: Google Calendar on `ihsvikingfootball@gmail.com`
- Board contact: `ihsvikingfootball@gmail.com`

**Graham's local repo path (Windows)**
```
C:\Users\graha\GitHub\inglemoor-football.github.io
```
Extract zips to **that folder** — the repo root, not a subfolder. This was
confused once and produced duplicate nested folders. Confirm it if unsure.

---

## 3. How Graham works — read this before doing anything

- **Ask before building.** Bring "should we do this / how should we do this"
  as a question rather than producing something that then gets deleted. He
  will often say "what questions do you have?" — that is an invitation to
  ask several, and he answers them all.
- **Always give copyable links.** Every single time he needs to check
  something, hand him the URL. He has asked for this explicitly more than
  once: *"give me copyable links for every thing you want me to check."*
- **Always show consolidated deploy steps plus a short summary of what's
  going in.** His words: *"always show the consolidated deployment steps and
  a quick summary of what is going in."*
- **Version every deploy** as `v0.9.xx — short name`. He reuses these as
  commit messages.
- **Commit messages should cover everything in the commit,** not just the
  headline change. He called this out directly.
- **When he's mid-setup, paste code into the chat.** Don't hand him a zip to
  download and extract when he's on step 8 of 12 in a Cloudflare dashboard:
  *"for the code in 9 remember to just paste it here. no download and zip
  stuff."*
- **When he asks for steps, number them 1, 2, 3.** Literally. He has asked
  for "step by step PLEASE" more than once after getting prose.
- **Use contractions.** He asked for this in the copy and it applies to
  chat too.
- **He works from a Windows PC and an iPhone.** Some tasks he'll ask to do
  from the phone — check whether that's realistic before saying yes. Editing
  code and pushing from a phone is something he explicitly does not want.
- **He verifies.** He checks work on the real site and reports precisely
  what's wrong. Don't claim something is fixed without actually verifying it.

---

## 4. Deploy process

The four steps, in this order, every time:

1. GitHub Desktop → **Fetch origin**, then **Pull origin**
2. Extract the zip over `C:\Users\graha\GitHub\inglemoor-football.github.io`
3. Check the changed-files list — count should match, and **nothing under `data/`**
4. Commit with the version message and push

Live in about a minute.

**Why pull first is non-negotiable:** the calendar workflow commits to the
repo hourly, and score posts from the admin page commit directly to
`index.html`. Graham's local copy goes stale fast. This has already nearly
caused data loss — a stale copy would have wiped three posted scores and
reverted the record from 3-1 to 1-0.

**`data/` is written by the workflow and by nobody else.** If it appears in
the changed-files list, untick it.

**Before building any zip that contains `index.html`:** fetch the live file
and compare the scores. Use WebFetch on the raw URL with a **cache-busting
query string** — WebFetch caches for 15 minutes and has served stale reads
in this project before:

```
https://raw.githubusercontent.com/inglemoor-football/inglemoor-football.github.io/main/index.html?cb=<anything>
```

---

## 5. Test process

Agreed with Graham now that the site is live:

1. **Automated verification** in the sandbox — parse check, selector check,
   asset-existence check, orphan-element check, geometry measurement across
   widths (see §9).
2. **`preview.bat`** — he double-clicks it and the real site opens at
   `http://localhost:8000/`. Uses PowerShell's `System.Net.HttpListener`.
   **Do not rewrite this to use Python** — Python isn't installed on his
   machine, and `where python` falsely succeeds because Windows ships a
   Store stub.
3. **Staging site** for big changes only.

Rollback drill: GitHub Desktop → **History** → right-click the commit →
**Revert**. Every version ever committed is kept.

---

## 6. How the site works

**Content** — everything editable is in the `SITE` object, first ~380 lines
of `index.html`, every block commented. Sections in page order:

```
hero → Spirit Wear → Donate → Volunteer → Schedule → Team →
Events → Coaches → Photos → Boosters → History → Committed → Sponsors
```

**Nav order must match document order.** The scroll-spy that highlights the
current section builds its target list from the nav links and assumes they're
in document order (`// sections are in document order`). Reorder sections and
you must reorder the nav the same way.

**What updates itself**
- **Calendar** — a GitHub Action (`.github/workflows/calendar.yml`) pulls the
  Google Calendar hourly at `:17` and commits `data/events.json`. Deliberately
  not `:00` — GitHub delays scheduled runs at the top of the hour.
- **Game states** — countdown, the "in progress" badge at kickoff, and
  "Final · score pending" afterwards are all derived from kickoff time plus
  `SITE.gameLengthMinutes` (165). Nothing triggers them.
- **Record and colours** — computed from the scores. Post a score and the
  record, hero and win/loss colours all follow.

**Ties work.** A 21-21 game reads `T`, and the record renders `1-0-1` format
only when a tie exists. This was a bug once; don't reintroduce it.

**Committed section** — a justified grid of commitment posters. Tile heights
are uniform per row and rows are centred, because justifying to the page edge
made some athletes look more important than others, which Graham rejected.
The row-height search nudges the height to avoid stranding a single poster on
the last row, and prefers taller rows. On phones each poster goes full width;
a poster too short to carry its caption on top gets the caption underneath
instead (the `.stacked` variant).

**Photos** — justified grid, fixed row heights, centred rows. Images resize
in the browser before upload (canvas: 2200px display + 900px thumbnail).

**Spirit Wear** — every store card is the same size (v0.9.40 dropped the
double-width lead card; Graham said it looked bad). The first store in
`SITE.shop.stores` comes first and gets the gold top edge.

**Booster shop QR** — a store with `qr:"images/qr/..."` gets a "Show QR code"
button that opens the QR full screen (reuses the coach pop-up styles), so a
parent can scan it and pay on their own phone. It shows on phones too, on
purpose: the use case is Graham holding his phone out.
`https://inglemoorfootball.com/#shop-qr` opens it straight away; Graham saves
that to his iPhone home screen. Closing clears the hash so the link keeps
working. **The QR encodes the URL itself** — the Zeffy link has "2025" in it,
so if the shop URL ever changes, regenerate `images/qr/booster-shop.svg` in the
same build. Verify any new QR by decoding it (OpenCV `QRCodeDetector` works in
the sandbox) before shipping.

---

## 7. The admin page

`https://inglemoorfootball.com/admin.html`, password-gated, works on a phone.

- **Scores** — pick the game, type the final, save. Live in about a minute
  (that's the GitHub Pages rebuild, not a delay in the Worker).
- **Photos** — pick a game, the panel expands inline underneath that game's
  row, drop photos or video in. Live straight away.
- **Hero image** — collapsed section at the bottom.

Scores commit straight to the repo. Photos go to R2, not git.

**Login verifies the password before showing anything.** It didn't originally
— it only loaded the game list, so any password got you in and then failed at
save. Fixed by adding a `check` action to the Worker. Don't regress this.

---

## 8. The Cloudflare Worker

Source of record is in the repo at `worker/site-worker.js` (reference copy —
the deployed version lives in Cloudflare).

```
Secrets:   ADMIN_PASSWORD, GITHUB_TOKEN
Variables: REPO_OWNER, REPO_NAME, ALLOWED_ORIGIN
Binding:   PHOTOS -> R2 bucket "inglemoor-photos"
```

The GitHub token is a fine-grained token held server-side so it never touches
the browser. `ALLOWED_ORIGIN` accepts several origins comma-separated; the
Worker echoes back whichever one matched.

**Actions:** `img`, `list`, `counts` are public GET. `check`, `score`,
`upload`, `delete` are POST and password-gated.

**Score patching** is a targeted regex that only ever writes `us`/`them` on an
existing schedule line:

```js
const re = new RegExp(
  '^(\\s*\\{ date:"' + date + '"[^}]*?)(,\\s*us:\\s*-?\\d+\\s*,\\s*them:\\s*-?\\d+)?(\\s*\\},?)$', "m");
```

Plus a safety net that **rejects any edit changing the file's line count, or
its length by more than 40 characters.** That guard is what stops a bad regex
from destroying the site. Leave it in.

**Do not put the admin password in any file, zip, or chat message.** It lives
only as a Cloudflare secret.

---

## 9. Hard-won rules — I broke these, don't repeat them

**Never make range-based or line-index edits to `index.html`.**
I broke the stylesheet **four separate times** by cutting between two comment
markers without verifying the end marker was the next block, swallowing 8–13KB
of live CSS each time. I also deleted the entire Photos renderer, the preview
banner, and the past-seasons renderer the same way. Graham caught these on the
live site.

**The rule:** every edit is a single-string replacement, guarded by an
assertion that the anchor appears exactly once.

```python
def rep(old, new):
    assert s.count(old) == 1, 'count=%d' % s.count(old)
    s = s.replace(old, new)
```

Two edits once failed silently because the anchor `$("#heroFacts")` appears in
both the next-game and season-complete branches. Assert the count; don't
assume.

**After editing, verify:**
- CSS braces balance
- every mount point (`#xxxMount`, `#xxxGrid`, …) still has a renderer
  referencing it
- no orphan elements — a section header with its content renderer deleted
- every `images/...` reference resolves to a real file (skip matches inside
  comments — the SITE block has documentation examples like
  `images/sponsors/acme.png` that intentionally don't exist)

**Committed lightbox "See the post"** used `.hide`, which only existed in
admin.html, so the button always showed and kept Quentin Moore's link for
every athlete. Fixed in v0.9.40 with `.cmlink.hide{display:none}`. If you add
a class toggle, grep that the class is actually styled in *this* file.

**Don't overstate.** I once told Graham the sponsor row "doesn't lazy-load."
It does. Check before asserting, and correct yourself explicitly when wrong.

**Image compression:** reserve JPEG for true photographs only — test is
colour count > 8000 **and** fully opaque. Flat artwork and logos get
`Image.quantize(colors=256, method=FASTOCTREE)` as PNG. My first pass
converted everything to JPEG and put visible ringing on two sponsor logos.

**Copy rule: never use the word "fees" anywhere on the site.** Graham's
instruction: *"No Fees anywhere — we can say donate but not fees."*

---

## 10. Things to refuse

**Scraping MaxPreps or ArbiterLive.** Asked repeatedly and under pressure.
ArbiterLive's robots.txt disallows automated access; MaxPreps' terms prohibit
automated collection. Loading the MaxPreps widget hidden and reading its data
is impossible client-side (same-origin policy), and fetching it server-side to
strip the numbers is scraping with extra steps.

**The school's AD saying it's okay does not change this** — the AD can't waive
a third party's terms. The two routes that could actually work:
1. Arbiter partner API, requested through the AD
2. MaxPreps contacted directly by the school

This is why the admin page exists. It's the answer to this problem.

**Generating likenesses of real people.** When no photo existed for an
athlete, ask Graham for one rather than inventing an image.

**Team photo resolution** is capped at 1600px to protect the photographer's
print sales (prints at roughly 5.3×2.2in versus 21.8×9in from the original).
Graham was told plainly that no technical measure can actually prevent
downloading.

---

## 11. Current state — v0.9.40

**Record: 3-1**

| Date | Opponent | Result |
|---|---|---|
| Sep 5 | Juanita | W 23-21 |
| Sep 11 | Highline | W 17-13 |
| Sep 18 | Mercer Island | L 3-10 |
| Sep 25 | Interlake | W 28-7 |
| Oct 2 | Newport | — |
| Oct 9 | Redmond | — |
| Oct 16 | Lake Washington | — |
| Oct 24 | Liberty | — |

**Committed — 10 athletes**

| Year | Name | College | Pos |
|---|---|---|---|
| 2027 | Ben Rainwater | Boise State | OT |
| 2026 | Zach Eubanks | Whitworth | DB |
| 2025 | Brandon Henkens | Puget Sound | DL |
| 2024 | Will Frank | Pacific Lutheran | QB/CB |
| 2024 | Matteus Senna | Montana Western | WR/S |
| 2024 | Christian Solomona | Central Washington | LB |
| 2020 | Trevor Thurman | Eastern Washington | DE |
| 2019 | Quentin Moore | Washington | TE (NFL badge — Commanders) |
| 2019 | Braden Dick | Pacific Lutheran | DL |
| 2017 | Max Larson | Pacific Lutheran | DE |

Larson's and Solomona's cards were **built from scratch** in this project —
no school artwork existed. Dick's is PLU's official graphic. The rest are
school- or college-made.

**Sponsors — 15 logos**, in three tiers (Gold, Silver, Community). All
processed onto white boxes with the logo maximised in the box. Not linked —
Graham said *"skip the URLs for now. We aren't linking them."*

---

## 12. Backlog

Agreed post-launch housekeeping, none of it urgent:

- Move the Cloudflare Worker and R2 bucket off Graham's personal account to
  one owned by `ihsvikingfootball@gmail.com`
- Move the Worker to a club domain, e.g. `scores.inglemoorfootball.com`
- Add a second GitHub org owner
- Move the GoDaddy account to the booster email

Open threads:

- **Spirit wear product images (Zeffy, not the website)** — Graham has Nike
  sweatshirts, with beanies and trucker hats coming. These are product photos
  for Zeffy listings; nothing on inglemoorfootball.com uses them. Parked until
  Graham raises it. Still unanswered when he does: floor photo, cut out on
  white, or transparent. Ask him for a previous image he liked and match it.
- Hero record label reads "KingCo Mountain" under an overall record. Graham:
  keep it for now.
- Small known bugs, not fixed: the season-complete hero shows W–L and drops
  ties; admin.html colours a tied score red like a loss; the hero's "Game X of
  9" counts the playoff placeholder.
- Sponsor website URLs — deliberately skipped
- Optional: note on Solomona's tile that he came via College of the Redwoods
- Optional: ~4KB of dead CSS. Recommended leaving it.

---

## 13. Sandbox notes for the next assistant

**What's blocked**
- `curl`/`wget` to most hosts — the agent proxy refuses with a 403 CONNECT.
  Use **WebFetch** for raw.githubusercontent.com. npm and pip work
  (pip needs `--break-system-packages`).
- **Google Fonts are blocked.** Headless Chromium falls back to a much wider
  font, so the nav appears to overflow and captions measure taller than they
  really are. Measurements are therefore **conservative** — the real site is
  tighter than what the sandbox shows. Don't chase phantom overflow bugs in
  the header or board table; verify against a screenshot before believing one.
- The live site does **not** load in the sandbox browser.

**What works**
- Playwright + Chromium at
  `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.
  Don't run `playwright install`.
- PIL, scipy, numpy for image work.
- Rendering HTML → PNG for card generation. Only DejaVu Sans Condensed Bold
  is available locally, so athletic display type is synthesized with CSS
  `transform: scaleX()` plus `skewX()`.

**Useful verification scripts** used in this project: geometry measurement
across 7–9 viewport widths, row-overflow and page-h-scroll detection, and
orphan-row detection for the committed grid. Rebuild them rather than
trusting a single screenshot — the 380px caption-overflow bug and the
760–850px cramped-tile bug were both found by measurement, not by looking.

---

## 14. File inventory

```
index.html      The entire website — content, styling, logic (~118KB)
admin.html      Private page for posting scores and photos
preview.bat     Local preview server (PowerShell — not Python)
README.md       Board-facing documentation
HANDOVER.md     This file
images/
  committed/    10 commitment posters
  coaches/      11 headshots
  sponsors/     15 logos
  team-2026.jpg Full squad photo, capped at 1600px
  qr/           booster-shop.svg — QR for the Zeffy booster shop
  viking-v*.png Logo variants
scripts/        fetch_calendar.py
worker/         site-worker.js (reference copy)
.github/        calendar.yml workflow
data/           WRITTEN BY THE WORKFLOW — never edit, never ship in a zip
```
