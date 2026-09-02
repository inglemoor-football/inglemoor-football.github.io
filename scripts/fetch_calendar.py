#!/usr/bin/env python3
"""
Pull the public IHS Viking Football Google Calendar and write data/events.json.

Run by .github/workflows/calendar.yml three times a day. Standard library
only, so the workflow needs no pip install and has nothing to go stale.

To change what gets published, edit the settings block below.
"""

import json, os, re, sys, urllib.request, datetime as dt
from zoneinfo import ZoneInfo

# ----------------------------------------------------------------- settings
ICS_URL   = "https://calendar.google.com/calendar/ical/ihsvikingfootball%40gmail.com/public/basic.ics"
TZ        = ZoneInfo("America/Los_Angeles")
DAYS      = 180         # how far ahead to look — covers the whole season
MAX       = 300         # most events to publish
OUT       = "data/events.json"

# Titles matching these are dropped. Empty by default — the calendar
# is published exactly as the team keeps it, varsity games included.
SKIP = []
# ---------------------------------------------------------------------------

UTC = ZoneInfo("UTC")


def unescape(s):
    return (s.replace("\\n", " ").replace("\\,", ",")
             .replace("\\;", ";").replace("\\\\", "\\").strip())


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "inglemoor-football-site/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def parse_events(raw):
    """Split the ICS into dicts. Unfolds the 75-character line wrapping first."""
    raw = raw.replace("\r\n ", "").replace("\r\n\t", "").replace("\r\n", "\n")
    raw = raw.replace("\n ", "").replace("\n\t", "")
    out = []
    for block in raw.split("BEGIN:VEVENT")[1:]:
        block = block.split("END:VEVENT")[0]
        ev = {}
        for line in block.split("\n"):
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            name = key.split(";")[0]
            if name == "EXDATE":
                ev.setdefault("_EXDATE", []).append((key, val))
            elif name not in ev:
                ev[name] = val
                ev[name + "_PARAMS"] = key
        out.append(ev)
    return out


def to_dt(value, params=""):
    """Return (datetime in Pacific, is_all_day)."""
    v = value.strip()
    if re.fullmatch(r"\d{8}", v):
        return dt.datetime.strptime(v, "%Y%m%d").replace(tzinfo=TZ), True
    if v.endswith("Z"):
        return dt.datetime.strptime(v, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).astimezone(TZ), False
    m = re.search(r"TZID=([^;:]+)", params)
    try:
        zone = ZoneInfo(m.group(1)) if m else TZ
    except Exception:
        zone = TZ
    return dt.datetime.strptime(v, "%Y%m%dT%H%M%S").replace(tzinfo=zone).astimezone(TZ), False


def rrule_dates(start, rule, window_end):
    """Expand DAILY and WEEKLY recurrences. Anything else yields just the start."""
    parts = dict(p.split("=", 1) for p in rule.split(";") if "=" in p)
    freq = parts.get("FREQ", "")
    if freq not in ("DAILY", "WEEKLY"):
        return [start]

    interval = int(parts.get("INTERVAL", 1))
    count = int(parts["COUNT"]) if "COUNT" in parts else None
    until = None
    if "UNTIL" in parts:
        try:
            until = to_dt(parts["UNTIL"])[0]
        except Exception:
            until = None

    days = None
    if freq == "WEEKLY" and "BYDAY" in parts:
        ix = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}
        days = {ix[d[-2:]] for d in parts["BYDAY"].split(",") if d[-2:] in ix}

    out, cur, n = [], start, 0
    guard = 0
    while cur <= window_end and guard < 4000:
        guard += 1
        if until and cur > until:
            break
        if count is not None and n >= count:
            break
        if days is None or cur.weekday() in days:
            out.append(cur)
            n += 1
        cur += dt.timedelta(days=1 if freq == "DAILY" else 1)
        if freq == "DAILY" and interval > 1:
            cur += dt.timedelta(days=interval - 1)
    return out


def main():
    try:
        raw = fetch(ICS_URL)
    except Exception as e:
        print(f"Could not fetch the calendar: {e}", file=sys.stderr)
        return 1
    if "BEGIN:VCALENDAR" not in raw:
        print("That URL did not return a calendar. Is it still public?", file=sys.stderr)
        return 1

    now = dt.datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    end = now + dt.timedelta(days=DAYS)
    skip = [re.compile(p, re.I) for p in SKIP]

    rows = []
    for ev in parse_events(raw):
        if "DTSTART" not in ev:
            continue
        title = unescape(ev.get("SUMMARY", ""))
        if not title or any(p.search(title) for p in skip):
            continue

        start, all_day = to_dt(ev["DTSTART"], ev.get("DTSTART_PARAMS", ""))

        # occurrences the organiser deleted
        excluded = set()
        for key, val in ev.get("_EXDATE", []):
            for piece in val.split(","):
                try:
                    excluded.add(to_dt(piece, key)[0])
                except Exception:
                    pass

        starts = rrule_dates(start, ev["RRULE"], end) if "RRULE" in ev else [start]

        for when in starts:
            if when in excluded or when < now or when > end:
                continue
            rows.append({
                "start":    when.isoformat(),
                "allDay":   all_day,
                "title":    title,
                "location": unescape(ev.get("LOCATION", "")),
            })

    # de-duplicate, then sort
    seen, clean = set(), []
    for r in sorted(rows, key=lambda r: r["start"]):
        k = (r["start"], r["title"])
        if k in seen:
            continue
        seen.add(k)
        clean.append(r)
    clean = clean[:MAX]

    payload = {
        "updated": dt.datetime.now(TZ).isoformat(timespec="seconds"),
        "windowDays": DAYS,
        "events": clean,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)
        f.write("\n")

    # GitHub disables scheduled workflows in public repos after 60 days
    # with no repository activity. Writing this once a week counts as
    # activity, so the refresh keeps running through the off-season.
    year, week, _ = dt.date.today().isocalendar()
    beat = os.path.join(os.path.dirname(OUT), "heartbeat.txt")
    stamp = f"{year}-W{week:02d}\n"
    if not os.path.exists(beat) or open(beat).read() != stamp:
        with open(beat, "w") as f:
            f.write(stamp)
        print(f"Heartbeat set to {stamp.strip()}")

    print(f"Wrote {len(clean)} events to {OUT}")
    for r in clean[:10]:
        print("   ", r["start"][:16].replace("T", "  "), r["title"][:44])
    return 0


if __name__ == "__main__":
    sys.exit(main())
