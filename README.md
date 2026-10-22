# CS Sânandrei Timiș – site oficial

Website for **CS Sânandrei Timiș** in **Liga a IV-a Timiș (2026/2027)**. Built with Django and published as a
**static site on GitHub Pages** (free, nothing to host or patch). Match data is imported automatically from
[frf-ajf.ro](https://www.frf-ajf.ro/timis/competitii-fotbal/liga-a-iv-a-16445); the club edits news, the
starting XI, players, shop and sponsors in **[Pages CMS](https://pagescms.org)** without touching code.

Guide for the club (in Romanian): **[GHID_CLUB.md](GHID_CLUB.md)**.

## How it works

```
frf-ajf.ro ──sync_frf──► data/frf.sqlite3 ─┐
                                           ├─► build_static ──► dist/ ──► GitHub Pages
Pages CMS ──commit──► content/ + media/ ───┘   (Django renders every page to HTML)
```

The GitHub Action [`.github/workflows/site.yml`](.github/workflows/site.yml) runs:

| When | What |
|---|---|
| Every day at 07:00, and every 2 h on Sat/Sun afternoons | `sync_frf` → commits the database **only if match data changed** → rebuild + deploy |
| Every push to `master` (each save in Pages CMS is a push) | rebuild + deploy, no sync (~2 min) |
| Actions → **Site** → *Run workflow* (tick *full* for a complete re-import) | sync + rebuild + deploy |

If frf-ajf.ro is down the site is still published with the existing data. If a page link is broken,
the build fails and the previous version stays online.

## One-time setup (≈15 minutes)

1. **Merge to `master`.**
2. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
3. **Actions → Site → Run workflow.** The first sync imports the whole league (1–2 min). The site appears at
   `https://orsadi.github.io/Sanandrei/`.
4. **Forms → email.** Create a free access key at [web3forms.com](https://web3forms.com) with the club's email
   address, then add it under **Settings → Secrets and variables → Actions → Variables** as `WEB3FORMS_KEY`.
   Without it, the contact and order forms open the visitor's email app instead.
5. **Pages CMS.** Sign in at [app.pagescms.org](https://app.pagescms.org) with GitHub, install the Pages CMS
   GitHub App on this repo, open the repo, then **Collaborators → invite** the club people by email.
   They don't need a GitHub account.
6. *(Optional)* **Own domain**, e.g. `cssanandrei.ro`: add the variable `SITE_CNAME=cssanandrei.ro`, point the
   domain's DNS to GitHub Pages and set it in **Settings → Pages → Custom domain**.

**Moving over existing admin edits** (shirt numbers, positions, photos from the old Django admin): copy your old
`db.sqlite3` to `data/frf.sqlite3` and the `media/` folder into the repo, run
`uv run python manage.py export_players`, commit. Existing files in `content/jucatori/` are never overwritten.

## What the club edits (Pages CMS)

| Section | File(s) | Notes |
|---|---|---|
| Știri | `content/stiri/*.md` | title, date, summary, photo, Markdown text, published on/off |
| Primul 11 | `content/primul11.yml` | round number + players per line (GK, DEF, MID, AM, FW) + bench + coach. Shown on the home page and the match page as a pitch graphic; hidden automatically once that round is played |
| Jucători | `content/jucatori/<frf_id>.yml` | shirt number, position, photo, bio. Files are created by the sync from the FRF roster; name and FRF id are read-only |
| Magazin | `content/produse/*.md` | name, category, price, photo, sizes, in stock, description |
| Sponsori | `content/sponsori.yml` | name, logo, website |
| Setări site | `content/setari.yml` | email, phone, stadium, footer text, Facebook/Instagram |

Uploaded photos go to `media/`; the build shrinks big phone photos automatically (originals stay in the repo).

## Pages

| URL | What |
|---|---|
| `/` | Home: next match + countdown, **starting XI**, last result, form, standings, our scorers, next round |
| `/lot/` | Squad grouped by position with per-player stats |
| `/jucator/<id>/` | Player profile: minutes, goals, cards, match-by-match log |
| `/meciuri/`, `/meciuri/etapa/<n>/` | Our fixtures and results + every round of the league |
| `/meci/<id>/` | Match centre: timeline, line-ups, referee, head-to-head (announced XI before kick-off) |
| `/clasament/`, `/clasament/<general\|acasa\|deplasare>/etapa/<n>/` | Standings: overall / home / away, after any round |
| `/statistici/` | Team stats, charts, sortable player table, league top scorers, fair-play, records |
| `/echipe/`, `/echipe/<slug>/` | Every league team |
| `/stiri/`, `/contact/`, `/cauta/` | News, contact form (Web3Forms), player/team search (in the browser) |
| `/magazin/` | Shop: cart kept in the browser, order emailed to the club (payment at pickup) |

## Local development

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py sync_frf          # or: seed_demo on an empty DB to test offline
uv run python manage.py export_players
uv run python manage.py load_content
uv run python manage.py runserver          # http://127.0.0.1:8000
```

Build the static site exactly like the Action does:

```bash
uv run python manage.py build_static --out dist   # SITE_URL_PREFIX defaults to "/"
python -m http.server -d dist                     # http://127.0.0.1:8000
```

`build_static` starts at `/` and follows every internal link, so new pages are picked up automatically; links with
query strings (`?x=`) are rejected because they can't work on a static host.

Environment variables: `SITE_URL_PREFIX` (`/` for a custom domain), `SITE_DOMAIN` (for `sitemap.xml`),
`SITE_CNAME`, `WEB3FORMS_KEY`, `DJANGO_DB` (default `data/frf.sqlite3`), `CONTENT_DIR` (default `content/`).

## Data notes

- Standings are ordered like frf-ajf.ro: points → goal difference → goals scored.
- Minutes played are derived from line-ups, substitutions and red cards (90' per match).
- Own goals count for the opponent and are excluded from top scorers.
- Point deductions: set `points_adjustment` on the team (Django admin locally, then commit `data/frf.sqlite3`).
- New season: update `FRF_COMPETITION_URL` and `SEASON` at the bottom of `config/settings.py`, delete
  `data/frf.sqlite3`, run the workflow with *full*.

## Tests

```bash
uv run python manage.py test
```
