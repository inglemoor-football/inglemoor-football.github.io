# Inglemoor Vikings Football

The website for Inglemoor High School Viking football and the
IHS Viking Gridiron Booster Club. Live at inglemoorfootball.com.

## What's here

    index.html        The entire website — content, styling and logic
    post-news.html    Optional private tool for posting announcements
    images/           Logos and photos

That's it. No build step, no dependencies, no database.

## Making a change

Everything editable lives in the `SITE` block at the top of
`index.html`, in the first 200 lines. Each section is commented.

Adding a score after a game:
  1. Open index.html, click the pencil icon
  2. Find the game in `schedule`
  3. Add `us: 28, them: 14` to that line
  4. Commit

The record, the win/loss colours, the season strip and the
countdown to the next game all update on their own.

## Publishing

Committing to `main` publishes automatically through GitHub Pages.
Live in about a minute. Watch the Actions tab for the green tick.

## If the page goes blank

You broke the JavaScript — almost always a missing quote or comma.
Open index.html, click History, find the last working version,
click Raw, copy it, and paste it back over the broken one.

Every version ever committed is kept. Nothing is lost.

## Colours

    Gold    #FEB72E    sampled from the official logo
    Shadow  #BF8A23
    Black   #000000
    Grey    #A1A8AC
