# CS Sânandrei Timiș – site oficial

Django website for **CS Sânandrei Timiș** in **Liga a IV-a Timiș (2026/2027)**. Same structure as
[Oravita](https://github.com/OrsAdi/Oravita) (`config/`, `core/`, `teams/`, `shop/`), but all match data
is imported automatically from [frf-ajf.ro](https://www.frf-ajf.ro/timis/competitii-fotbal/liga-a-iv-a-16445).

## Quick start

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py sync_frf          # imports the whole league (~1–2 min the first time)
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

## Pages

| URL | What |
|---|---|
| `/` | Home: next match + live countdown, last result, form, standings, our scorers, next round |
| `/lot/` | Squad grouped by position (Portari / Fundași / Mijlocași / Atacanți) with per-player stats |
| `/jucator/<id>/` | Player profile: minutes, goals, cards, match-by-match log |
| `/meciuri/` | Our fixtures and results + every round of the league |
| `/meci/<id>/` | Match centre: timeline (goals, cards, subs), line-ups, referee, head-to-head |
| `/clasament/` | Standings: overall / home / away, “after round N”, form with scores |
| `/statistici/` | Team stats, position-by-round chart, goal-timing chart, sortable player table, league top scorers, fair-play, records |
| `/echipe/`, `/echipe/<slug>/` | Every league team: results, stats, players, record vs. Sânandrei |
| `/stiri/`, `/contact/`, `/cauta/` | News, contact form (saved in Admin, honeypot anti-spam), player/team search |
| `/magazin/` | Club shop: products, sizes, session cart, order request (payment at pickup) |

## Keeping data up to date

`sync_frf` is incremental: it re-reads all 30 rounds and only downloads details for newly finished
matches (a few seconds when nothing changed). Options: `--full` (re-import every match), `--no-roster`, `--workers N`.

Ways to run it:
- **Admin → Sync runs → “Sincronizează acum”** (button).
- **Scheduled**, e.g. every Saturday/Sunday evening:
  - Linux cron: `0 20 * * 6,0 cd /path/to/site && uv run python manage.py sync_frf`
  - Windows Task Scheduler: run `uv run python manage.py sync_frf` in the project folder.

## What you edit in Admin

FRF has no shirt numbers, positions or photos, so these are editable per player (**Players**, filter
“CS Sânandrei Timiș”): `number`, `position`, `bio`, `image`. The sync never overwrites them.
Also in Admin: news, sponsors (shown on the home page), contact messages, shop products/orders,
and `points_adjustment` on a team if a disciplinary committee deducts points.

## Notes

- Standings are ordered like frf-ajf.ro: points → goal difference → goals scored.
  Computed numbers were checked against the official standings, top scorers and league stats pages.
- Minutes played are derived from line-ups, substitutions and red cards (90' per match).
- Own goals count for the opponent and are excluded from top scorers.
- Config lives at the bottom of `config/settings.py` (`OUR_TEAM_FRF_ID`, `FRF_COMPETITION_URL`, `SEASON`, contact info).
  For a new season, update `FRF_COMPETITION_URL` and `SEASON`.
- Production: set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`, `CLUB_EMAIL`, `CLUB_PHONE`, then `collectstatic`.

## Tests

```bash
uv run python manage.py test
```
