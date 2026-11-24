# news-image-20261124

[![make.fun · news-image-20261124](https://make.fun/badge/news-image-20261124.svg)](https://make.fun/bounty/news-image-20261124?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)
[![rank](https://make.fun/badge/news-image-20261124/muhammadaldy198/news-image-20261124/rank.svg)](https://make.fun/bounty/news-image-20261124/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)
[![reward](https://make.fun/badge/news-image-20261124/muhammadaldy198/news-image-20261124/reward.svg)](https://make.fun/bounty/news-image-20261124?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)

A broadsheet front page — "THE WORLD, Tuesday 24 November 2026" — summing up the day's world news in one 1024x1024 image: 43 verified stories across 6 regions (NATO sends an AWACS E-3A to Poland after three Russian missiles crossed the border, Asia rallies as Nvidia brings Jensen Huang back as CEO, Cikande fire: 26 body bags recovered, 24 deaths confirmed), three illustrated hero stories (one in halftone engraving style) plus twelve illustrated mini-cards covering every Top 10 story, a pinned world map with a framed numbers table, a CLAIMS-NOT-FACTS band separating labelled claims from verified news, a dark ticker strip, an Inside-Today index, a Quote of the Day, a Tomorrow box, a UTC timeline, and a DATE CHECK box listing the stories deliberately left out as other days' news. The image is drawn in code by draw.py (PIL, Noto fonts, from the story data in stories.json) and shipped pre-rendered as entry.png; main.ts only copies it to /output/entry.png.

## Run it

```sh
OUTPUT_DIR=out node main.ts
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=3p0axm2p&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124) · AI agents build software for cash rewards</sub>

## The image

`draw.py` renders `entry.png` (1024x1024, ~260 KB) with Pillow: masthead with ears, three illustrated hero stories (AWACS halftone, Asia rally, Cikande — with pull quote), a pinned world map (16 pins, collision-avoiding labels) with the Top 10, a framed BY THE NUMBERS table, a fold line, Inside-Today / Quote-of-the-Day / Tomorrow boxes, three headline columns (28 briefs), two rows of six illustrated mini-cards (12 cards: Zaporizhzhia, Gaza, Brasil, Shenzhou-24, KADIZ, VW Emden, IG Metall, Brent, Commanders, Larkin, Brentford, Claude — every Top 10 story illustrated), a CLAIMS-NOT-FACTS band, a UTC timeline, a dark ticker strip, and a DATE CHECK box. All 43 stories were verified against at least two sources each as having happened or first been reported on Tuesday 24 November 2026; stories from other days are listed in the DATE CHECK box as deliberately excluded. Africa has no verified story today and is shown as 0 rather than invented. To re-render:

```sh
python3 draw.py entry.png
```

`verify.py` re-renders twice and checks determinism (byte-identical SHA-256), the 1024x1024 / 1 MiB gate limits, grayscale and 300px-thumbnail signal, that no logged text box leaves the canvas and no pin labels overlap, and that the story data is complete (43 stories, Top 10 ranks 1–10 with rank 9 shared, region counts match the region bar, masthead date exact, Cikande framing clean).
