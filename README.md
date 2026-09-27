# Inglemoor Vikings Football

The website for Inglemoor High School Viking football and the
IHS Viking Gridiron Booster Club. Live at **inglemoorfootball.com**.

Built and maintained by the booster club. No build step, no
dependencies, no database, and nothing to pay for except the
domain renewal.

## What's here

    index.html      The entire website — content, styling and logic
    admin.html      Private page for posting scores and photos
    preview.bat     Double-click to preview the site before pushing
    HANDOVER.md     Full technical notes — infrastructure, process, history
    images/         Logos, coach headshots, sponsors, commitments
    data/           Calendar feed — written automatically, don't edit
    scripts/        Fetches the Google Calendar
    worker/         Copy of the Cloudflare code, for reference only

## The two ways to change things

### 1. The admin page — for anything during the season

Go to **inglemoorfootball.com/admin.html** and enter the booster
password. Works on a phone.

  - **Scores** — pick the game, type the final, save. Live in a minute.
  - **Photos** — pick a game, drop photos or video in. Live straight away.
  - **Hero image** — the action shot at the top of the site.

Scores commit straight to this repository. Photos go to Cloudflare
R2 storage, not to git.

### 2. Editing index.html — for everything else

Rosters, coaches, board members, sponsors, commitments, the spirit
wear stores and all the written copy live in the `SITE` block at the
top of `index.html`, in the first ~380 lines. Every section is
commented.

Edit it on github.com or with GitHub Desktop, commit, and it is
live in about a minute.

**Before pushing, double-click `preview.bat`.** It opens the real
site at localhost:8000 so you can check your change. Close the
black window when you're done.

## What updates itself

  - **Calendar** — pulled from the football Google Calendar every
    hour by a GitHub Action. Change the calendar, the site follows.
  - **Countdown and game states** — the countdown, the "in progress"
    badge at kickoff and "score pending" afterwards are all worked
    out from the kickoff time. Nobody triggers them.
  - **Record and colours** — calculated from the scores. Post a score
    and the record, the hero and the win/loss colours all follow.

## Deploying a new version

Always **pull before you extract**, or you will get a merge conflict:

  1. GitHub Desktop → Fetch origin, then Pull origin
  2. Extract the zip over the repository folder
  3. Check the changed files list — nothing under `data/`
  4. Commit and push

`data/` is written by the workflow and by nobody else. If it shows
up as a change, untick it.

## If the page goes blank

You broke the JavaScript — almost always a missing quote or comma.
Open `index.html` on github.com, click **History**, find the last
working version, click **Raw**, copy it, paste it back over the
broken one, and commit.

Every version ever committed is kept. Nothing is lost.

## Where things live

    Site            GitHub Pages, this repository
    Domain          GoDaddy, paid through August 2034
    Scores/photos   Cloudflare Worker + R2 bucket
    Calendar        Google Calendar (ihsvikingfootball@gmail.com)

## Colours

    Gold    #FEB72E    sampled from the official logo
    Shadow  #BF8A23
    Black   #000000
    Grey    #A1A8AC

## Questions

The booster board: **ihsvikingfootball@gmail.com**
