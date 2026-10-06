from collections import defaultdict

from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from . import stats
from .models import Appearance, Match, MatchEvent, Player, Team

POSITION_GROUPS = [
    ("Portar", "Portari"),
    ("Fundaș", "Fundași"),
    ("Mijlocaș", "Mijlocași"),
    ("Atacant", "Atacanți"),
]


def _our_team_or_404():
    team = stats.our_team()
    if team is None:
        raise Http404("Datele nu au fost încă importate. Rulați: python manage.py sync_frf")
    return team


def squad_list(request):
    team = _our_team_or_404()
    players = stats.player_stats(team=team)
    active = [p for p in players if p.apps]
    others = sorted((p for p in players if not p.apps and p.registered and p.team_id == team.pk),
                    key=lambda p: p.name)

    sort_key = lambda p: (p.number is None, p.number or 0, -p.minutes, p.name)  # noqa: E731
    groups = []
    for code, label in POSITION_GROUPS:
        members = sorted((p for p in active if p.position == code), key=sort_key)
        if members:
            groups.append({"label": label, "players": members})
    unassigned = sorted((p for p in active if not p.position), key=sort_key)
    if unassigned:
        groups.append({"label": "Jucători folosiți în acest sezon" if not groups else "Alți jucători", "players": unassigned})

    return render(request, "teams/squad.html", {
        "team": team,
        "groups": groups,
        "others": others,
        "total_used": len(active),
    })


def player_detail(request, pk):
    player = get_object_or_404(Player.objects.select_related("team"), pk=pk)
    [player_s] = stats.player_stats(players=[player])
    appearances = (Appearance.objects.filter(player=player)
                   .select_related("match__home", "match__away", "team").order_by("match__round"))
    events_by_match = defaultdict(list)
    for e in MatchEvent.objects.filter(player=player).exclude(kind=MatchEvent.SUB):
        events_by_match[e.match_id].append(e)
    log = []
    for a in appearances:
        m = a.match
        log.append({
            "appearance": a,
            "match": m,
            "opponent": m.opponent_of(a.team),
            "home": m.home_id == a.team_id,
            "result": m.result_for(a.team),
            "events": events_by_match.get(m.pk, []),
        })
    return render(request, "teams/player_detail.html", {"player": player_s, "log": log})


def fixtures(request):
    """Programul și rezultatele echipei noastre + navigare pe etape pentru toată liga."""
    team = _our_team_or_404()
    matches = list(stats.team_matches(team))
    played = [m for m in matches if m.is_finished]
    upcoming = [m for m in matches if not m.is_finished]
    for m in matches:
        m.our_result = m.result_for(team)
        m.is_home = m.home_id == team.pk

    total_rounds = Match.objects.order_by("-round").values_list("round", flat=True).first() or 0
    try:
        selected_round = int(request.GET.get("etapa", 0))
    except ValueError:
        selected_round = 0
    if not 1 <= selected_round <= total_rounds:
        selected_round = stats.last_played_round() or 1
    round_matches = Match.objects.filter(round=selected_round).select_related("home", "away")

    return render(request, "teams/fixtures.html", {
        "team": team,
        "played": list(reversed(played)),
        "upcoming": upcoming,
        "rounds": range(1, total_rounds + 1),
        "selected_round": selected_round,
        "round_matches": round_matches,
    })


def match_detail(request, pk):
    match = get_object_or_404(Match.objects.select_related("home", "away"), pk=pk)
    apps = list(match.appearances.select_related("player"))
    events = list(match.events.select_related("player", "player_out", "team"))

    player_events = defaultdict(list)
    for e in events:
        if e.player_id and e.kind != MatchEvent.SUB:
            player_events[e.player_id].append(e)
    for a in apps:
        a.events = player_events.get(a.player_id, [])

    def lineup(team):
        side = [a for a in apps if a.team_id == team.pk]
        return [a for a in side if a.is_starter], [a for a in side if not a.is_starter]

    home_start, home_bench = lineup(match.home)
    away_start, away_bench = lineup(match.away)
    h2h = [m for m in stats.head_to_head(match.home, match.away) if m.pk != match.pk]

    table = stats.standings() if Match.objects.filter(is_finished=True).exists() else []
    positions = {r.team.pk: r for r in table}

    return render(request, "teams/match_detail.html", {
        "match": match,
        "events": events,
        "home_start": home_start, "home_bench": home_bench,
        "away_start": away_start, "away_bench": away_bench,
        "h2h": h2h,
        "home_row": positions.get(match.home_id),
        "away_row": positions.get(match.away_id),
    })


def standings(request):
    venue = request.GET.get("tip", "all")
    if venue not in ("all", "home", "away"):
        venue = "all"
    last = stats.last_played_round()
    try:
        upto = int(request.GET.get("etapa", last))
    except ValueError:
        upto = last
    upto = max(1, min(upto, last)) if last else 0
    table = stats.standings(venue=venue, upto_round=upto or None)
    return render(request, "teams/standings.html", {
        "table": table,
        "venue": venue,
        "upto": upto,
        "rounds": range(1, last + 1),
        "last_round": last,
        "total_teams": len(table),
    })


def stats_list(request):
    team = _our_team_or_404()
    matches = list(stats.finished_matches())
    table = stats.standings(matches=matches)
    our_row = next((r for r in table if r.team.pk == team.pk), None)
    players = [p for p in stats.player_stats(team=team) if p.apps]
    players.sort(key=lambda p: (-p.goals, -p.minutes, p.name))

    history = stats.position_history(team, matches)
    summary = stats.team_summary(team)
    return render(request, "teams/stats.html", {
        "team": team,
        "our_row": our_row,
        "summary": summary,
        "summary_sides": [("Acasă", summary["home"]), ("Deplasare", summary["away"])],
        "players": players,
        "scorers": stats.top_scorers(limit=20),
        "league": stats.league_overview(matches),
        "rankings": stats.team_rankings(table),
        "discipline": stats.discipline_table(),
        "carded": stats.most_carded(10),
        "goal_minutes": stats.goal_minutes(team),
        "history": history,
        "history_chart": _history_chart(history, len(table)),
    })


def team_list(request):
    table = stats.standings()
    return render(request, "teams/team_list.html", {"table": table})


def team_detail(request, slug):
    team = get_object_or_404(Team, slug=slug)
    matches = list(stats.team_matches(team))
    played = [m for m in matches if m.is_finished]
    for m in matches:
        m.team_result = m.result_for(team)
        m.is_home = m.home_id == team.pk
    table = stats.standings()
    row = next((r for r in table if r.team.pk == team.pk), None)
    players = [p for p in stats.player_stats(team=team) if p.apps]
    players.sort(key=lambda p: (-p.goals, -p.minutes, p.name))
    ours = stats.our_team()
    h2h = list(stats.head_to_head(team, ours)) if ours and ours.pk != team.pk else []
    history = stats.position_history(team)
    return render(request, "teams/team_detail.html", {
        "team": team,
        "row": row,
        "summary": stats.team_summary(team, played),
        "played": list(reversed(played)),
        "upcoming": [m for m in matches if not m.is_finished],
        "players": players,
        "h2h": h2h,
        "goal_minutes": stats.goal_minutes(team),
        "history": history,
        "history_chart": _history_chart(history, len(table)),
    })


def _history_chart(history, team_count, width=640, height=220, pad=28):
    """Coordonatele pentru graficul SVG cu evoluția locului în clasament."""
    if not history or team_count < 2:
        return None
    n = len(history)
    inner_w = width - 2 * pad
    inner_h = height - 2 * pad
    step = inner_w / max(n - 1, 1)
    points = []
    for i, h in enumerate(history):
        x = pad + (i * step if n > 1 else inner_w / 2)
        y = pad + (h["position"] - 1) / (team_count - 1) * inner_h
        points.append({"x": round(x, 1), "y": round(y, 1), **h})
    gridlines = []
    for pos in sorted({1, (team_count + 1) // 2, team_count}):
        gridlines.append({"pos": pos, "y": round(pad + (pos - 1) / (team_count - 1) * inner_h, 1)})
    return {
        "width": width, "height": height, "pad": pad,
        "points": points,
        "polyline": " ".join(f"{p['x']},{p['y']}" for p in points),
        "gridlines": gridlines,
        "right": width - pad,
        "bottom": height - pad + 18,
    }


def search(request):
    q = request.GET.get("q", "").strip()
    players = teams = []
    if len(q) >= 2:
        players = Player.objects.filter(Q(name__icontains=q)).select_related("team")[:30]
        teams = Team.objects.filter(name__icontains=q)[:10]
    return render(request, "teams/search.html", {"q": q, "players": players, "teams": teams})
