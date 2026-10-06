"""Importă datele competiției de pe frf-ajf.ro în baza de date."""

import re
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from . import frf
from .models import Appearance, Match, MatchEvent, Player, SyncRun, Team

LOCAL_TZ = ZoneInfo("Europe/Bucharest")


def _log(log, msg):
    if log:
        log(msg)


def discover_rounds(html):
    rounds = [int(n) for n in re.findall(r"/meciuri/etapa-(\d+)\"", html)]
    return max(rounds) if rounds else 30


def _upsert_team(data):
    team, created = Team.objects.get_or_create(
        frf_id=data["frf_id"],
        defaults={
            "name": data["name"],
            "slug": _unique_slug(data["name"], data["frf_id"]),
            "frf_url": data["url"],
            "logo_url": f"{frf.BASE_URL}/upload/echipe/{data['frf_id']}.jpg",
        },
    )
    if not created and team.name != data["name"]:
        team.name = data["name"]
        team.save(update_fields=["name"])
    return team


def _unique_slug(name, frf_id):
    base = slugify(name) or f"echipa-{frf_id}"
    if Team.objects.filter(slug=base).exclude(frf_id=frf_id).exists():
        return f"{base}-{frf_id}"
    return base


def _aware(dt):
    return dt.replace(tzinfo=LOCAL_TZ) if dt else None


def save_round_matches(matches):
    """Salvează meciurile unei etape. Întoarce numărul de meciuri noi / modificate."""
    changed = 0
    for m in matches:
        home = _upsert_team(m["home"])
        away = _upsert_team(m["away"])
        values = {
            "frf_url": m["frf_url"],
            "round": m["round"],
            "date": _aware(m["date"]),
            "venue": m["venue"],
            "home": home,
            "away": away,
            "home_score": m["home_score"],
            "away_score": m["away_score"],
            "ht_home": m["ht_home"],
            "ht_away": m["ht_away"],
            "is_finished": m["is_finished"],
        }
        match = Match.objects.filter(frf_id=m["frf_id"]).first()
        if match is None:
            Match.objects.create(frf_id=m["frf_id"], **values)
            changed += 1
            continue
        score_changed = (match.home_score, match.away_score, match.is_finished) != (
            m["home_score"], m["away_score"], m["is_finished"])
        if score_changed:
            values["details_synced"] = False
        dirty = False
        for field, value in values.items():
            if getattr(match, field if field not in ("home", "away") else f"{field}_id") != (
                    value.pk if field in ("home", "away") else value):
                setattr(match, field, value)
                dirty = True
        if dirty:
            match.save()
            changed += 1
    return changed


def _upsert_player(data, team, registered=None):
    if not data.get("frf_id"):
        return None
    player = Player.objects.filter(frf_id=data["frf_id"]).first()
    if player is None:
        player = Player(frf_id=data["frf_id"])
    player.name = data["name"] or player.name
    player.team = team
    if data.get("birth_date"):
        player.birth_date = data["birth_date"]
    if data.get("card_number"):
        player.card_number = data["card_number"]
    if data.get("photo_url"):
        player.photo_url = data["photo_url"]
    if registered is not None:
        player.registered = registered
    player.save()
    return player


@transaction.atomic
def save_match_details(match, details):
    match.appearances.all().delete()
    match.events.all().delete()
    if details["referee"]:
        match.referee = details["referee"]
    if details["ht"][0] is not None:
        match.ht_home, match.ht_away = details["ht"]

    side_team = {"home": match.home, "away": match.away}
    players = {}
    for side in ("home", "away"):
        team = side_team[side]
        lineup = details[f"{side}_players"]
        side_events = [e for e in details["events"] if e["side"] == side]
        minutes = frf.compute_minutes(lineup, side_events)
        for p in lineup:
            player = _upsert_player(p, team)
            if player is None:
                continue
            players[p["frf_id"]] = player
            if p["frf_id"] in minutes:
                minute_in, minute_out, played = minutes[p["frf_id"]]
                Appearance.objects.create(
                    match=match, player=player, team=team, is_starter=p["is_starter"],
                    minute_in=minute_in, minute_out=minute_out, minutes_played=played,
                )

    for e in details["events"]:
        team = side_team[e["side"]]
        player = players.get(e["player_id"])
        if player is None and e.get("player_id"):
            player = _upsert_player({"frf_id": e["player_id"], "name": e.get("player_name", "")}, team)
        MatchEvent.objects.create(
            match=match, team=team, player=player,
            player_out=players.get(e.get("player_out_id")),
            kind=e["kind"], minute=e["minute"], detail=e.get("detail", "")[:200],
        )

    match.details_synced = True
    match.save()


def sync_roster(team, log=None):
    html = frf.fetch(f"{team.frf_url}/jucatori")
    roster = frf.parse_roster(html)
    ids = []
    with transaction.atomic():
        for p in roster:
            player = _upsert_player(p, team, registered=True)
            ids.append(player.pk)
        team.players.filter(registered=True).exclude(pk__in=ids).update(registered=False)
    _log(log, f"Lot {team.name}: {len(roster)} jucători înregistrați")
    return len(roster)


def run_sync(full=False, workers=8, log=None, with_roster=True):
    run = SyncRun.objects.create()
    lines = []

    def note(msg):
        lines.append(msg)
        _log(log, msg)

    try:
        comp_url = settings.FRF_COMPETITION_URL
        first = frf.fetch(comp_url)
        total_rounds = discover_rounds(first)
        note(f"Competiție: {total_rounds} etape")

        def load_round(n):
            return n, frf.parse_round(frf.fetch(f"{comp_url}/meciuri/etapa-{n}"), n)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            rounds = sorted(pool.map(load_round, range(1, total_rounds + 1)))
        changed = 0
        for n, matches in rounds:
            changed += save_round_matches(matches)
        note(f"Meciuri: {Match.objects.count()} în total, {changed} noi/actualizate")

        pending = Match.objects.filter(is_finished=True)
        if not full:
            pending = pending.filter(details_synced=False)
        pending = list(pending.select_related("home", "away"))
        note(f"Detalii de importat: {len(pending)} meciuri")

        def load_match(match):
            return match, frf.parse_match(frf.fetch(match.frf_url))

        with ThreadPoolExecutor(max_workers=workers) as pool:
            for match, details in pool.map(load_match, pending):
                save_match_details(match, details)
                _log(log, f"  ✓ {match}")

        if with_roster:
            ours = Team.objects.filter(frf_id=settings.OUR_TEAM_FRF_ID).first()
            if ours:
                sync_roster(ours, log=note)

        run.ok = True
    except Exception as exc:
        note(f"EROARE: {exc!r}")
        raise
    finally:
        run.finished_at = timezone.now()
        run.summary = "\n".join(lines)
        run.save()
    return run
