"""Calculul clasamentului și al statisticilor, pornind de la meciurile din baza de date."""

from collections import defaultdict
from dataclasses import dataclass, field

from django.conf import settings
from django.db.models import Count, Max, Q, Sum

from .models import Appearance, Match, MatchEvent, Player, Team


def our_team():
    return Team.objects.filter(frf_id=settings.OUR_TEAM_FRF_ID).first()


def finished_matches():
    return Match.objects.filter(is_finished=True).select_related("home", "away")


def last_played_round():
    return finished_matches().aggregate(r=Max("round"))["r"] or 0


# --------------------------------------------------------------------------- clasament

@dataclass
class Row:
    team: Team
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    gf: int = 0
    ga: int = 0
    adjustment: int = 0
    results: list = field(default_factory=list)  # [(round, 'V'/'E'/'I', match)]
    position: int = 0

    @property
    def gd(self):
        return self.gf - self.ga

    @property
    def points(self):
        return self.won * 3 + self.drawn + self.adjustment

    @property
    def form(self):
        return [r for _, r, _ in sorted(self.results, key=lambda x: x[0])[-5:]]

    @property
    def form_matches(self):
        return [(r, m) for _, r, m in sorted(self.results, key=lambda x: x[0])[-5:]]

    @property
    def ppg(self):
        return round(self.points / self.played, 2) if self.played else 0


def _tally(rows, match, venue):
    h, a = match.home, match.away
    hs, as_ = match.home_score, match.away_score
    sides = []
    if venue in ("all", "home"):
        sides.append((h, hs, as_))
    if venue in ("all", "away"):
        sides.append((a, as_, hs))
    for team, gf, ga in sides:
        row = rows[team.pk]
        row.played += 1
        row.gf += gf
        row.ga += ga
        if gf > ga:
            row.won += 1
            res = "V"
        elif gf < ga:
            row.lost += 1
            res = "I"
        else:
            row.drawn += 1
            res = "E"
        row.results.append((match.round, res, match))


def standings(venue="all", upto_round=None, matches=None):
    """
    Clasamentul, ordonat ca pe frf-ajf.ro: puncte, golaveraj, goluri marcate.
    venue: "all", "home" (doar meciurile de acasă) sau "away".
    """
    if matches is None:
        matches = list(finished_matches())
    if upto_round is not None:
        matches = [m for m in matches if m.round <= upto_round]
    teams = {t.pk: t for t in Team.objects.all()}
    rows = {pk: Row(team=t, adjustment=t.points_adjustment if venue == "all" else 0) for pk, t in teams.items()}
    for m in matches:
        _tally(rows, m, venue)

    ordered = sorted(rows.values(), key=lambda r: (-r.points, -r.gd, -r.gf, r.team.name))
    for i, row in enumerate(ordered, 1):
        row.position = i
    return ordered


def position_history(team, matches=None):
    """Locul ocupat de echipă după fiecare etapă: [(etapa, loc, puncte)]."""
    if matches is None:
        matches = list(finished_matches())
    last = max((m.round for m in matches), default=0)
    history = []
    for rnd in range(1, last + 1):
        table = standings(upto_round=rnd, matches=matches)
        row = next((r for r in table if r.team.pk == team.pk), None)
        if row:
            history.append({"round": rnd, "position": row.position, "points": row.points})
    return history


# --------------------------------------------------------------------------- echipă

def team_matches(team):
    return (Match.objects.filter(Q(home=team) | Q(away=team))
            .select_related("home", "away").order_by("round", "date"))


def team_summary(team, matches=None):
    """Statistici agregate pentru o echipă (din perspectiva ei)."""
    if matches is None:
        matches = [m for m in team_matches(team) if m.is_finished]
    s = {
        "played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0,
        "clean_sheets": 0, "failed_to_score": 0, "over_2_5": 0, "btts": 0,
        "home": {"played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0},
        "away": {"played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0},
        "biggest_win": None, "biggest_loss": None,
        "ht_leading": 0, "ht_leading_won": 0, "comebacks": 0,
    }
    for m in matches:
        gf, ga = m.goals_for(team), m.goals_against(team)
        res = m.result_for(team)
        bucket = s["home"] if m.home_id == team.pk else s["away"]
        for target in (s, bucket):
            target["played"] += 1
            target["gf"] += gf
            target["ga"] += ga
            target[{"V": "won", "E": "drawn", "I": "lost"}[res]] += 1
        s["clean_sheets"] += ga == 0
        s["failed_to_score"] += gf == 0
        s["over_2_5"] += gf + ga > 2
        s["btts"] += gf > 0 and ga > 0
        if res == "V" and (s["biggest_win"] is None or gf - ga > s["biggest_win"][1]):
            s["biggest_win"] = (m, gf - ga)
        if res == "I" and (s["biggest_loss"] is None or ga - gf > s["biggest_loss"][1]):
            s["biggest_loss"] = (m, ga - gf)
        if m.has_halftime:
            ht_f = m.ht_home if m.home_id == team.pk else m.ht_away
            ht_a = m.ht_away if m.home_id == team.pk else m.ht_home
            if ht_f > ht_a:
                s["ht_leading"] += 1
                s["ht_leading_won"] += res == "V"
            if ht_f < ht_a and res in ("V", "E"):
                s["comebacks"] += 1
    for target in (s, s["home"], s["away"]):
        target["gd"] = target["gf"] - target["ga"]
        target["points"] = target["won"] * 3 + target["drawn"]
    p = s["played"] or 1
    s["gf_avg"] = round(s["gf"] / p, 2)
    s["ga_avg"] = round(s["ga"] / p, 2)
    s["win_pct"] = round(100 * s["won"] / p)
    s["streak"] = current_streak(team, matches)
    s["unbeaten"] = unbeaten_run(team, matches)
    return s


def current_streak(team, matches):
    ordered = sorted(matches, key=lambda m: (m.round, m.date or 0))
    if not ordered:
        return None
    last = ordered[-1].result_for(team)
    count = 0
    for m in reversed(ordered):
        if m.result_for(team) != last:
            break
        count += 1
    return {"result": last, "count": count}


def unbeaten_run(team, matches):
    count = 0
    for m in sorted(matches, key=lambda m: (m.round, m.date or 0), reverse=True):
        if m.result_for(team) == "I":
            break
        count += 1
    return count


def goal_minutes(team):
    """Goluri marcate / primite pe intervale de 15 minute."""
    buckets = ["1-15", "16-30", "31-45+", "46-60", "61-75", "76-90+"]

    def bucket(minute):
        if minute <= 15:
            return 0
        if minute <= 30:
            return 1
        if minute <= 45:
            return 2
        if minute <= 60:
            return 3
        if minute <= 75:
            return 4
        return 5

    scored = [0] * 6
    conceded = [0] * 6
    events = MatchEvent.objects.filter(
        Q(match__home=team) | Q(match__away=team),
        kind__in=[MatchEvent.GOAL, MatchEvent.PENALTY, MatchEvent.OWN_GOAL],
    ).select_related("match")
    for e in events:
        for_team = e.team_id == team.pk
        if e.kind == MatchEvent.OWN_GOAL:
            for_team = not for_team
        (scored if for_team else conceded)[bucket(e.minute)] += 1
    peak = max(scored + conceded + [1])
    return [
        {"label": label, "scored": s, "conceded": c, "scored_pct": round(100 * s / peak), "conceded_pct": round(100 * c / peak)}
        for label, s, c in zip(buckets, scored, conceded)
    ]


def head_to_head(team_a, team_b):
    return (Match.objects.filter(Q(home=team_a, away=team_b) | Q(home=team_b, away=team_a))
            .select_related("home", "away").order_by("round"))


# --------------------------------------------------------------------------- jucători

def player_stats(team=None, players=None):
    """
    Statistici pentru fiecare jucător: meciuri, titular, minute, goluri,
    autogoluri, cartonașe. Întoarce o listă de Player cu atribute adăugate.
    """
    qs = Player.objects.select_related("team")
    if team is not None:
        qs = qs.filter(Q(team=team) | Q(appearances__team=team)).distinct()
    if players is not None:
        qs = qs.filter(pk__in=[p.pk for p in players])

    app_filter = Q(appearances__team=team) if team is not None else Q()
    ev_filter = Q(events__team=team) if team is not None else Q()
    qs = qs.annotate(
        apps=Count("appearances", filter=app_filter, distinct=True),
        starts=Count("appearances", filter=app_filter & Q(appearances__is_starter=True), distinct=True),
        minutes=Sum("appearances__minutes_played", filter=app_filter),
    )
    players = list(qs)
    ev = MatchEvent.objects.filter(player__in=players)
    if team is not None:
        ev = ev.filter(team=team)
    counts = defaultdict(lambda: defaultdict(int))
    for row in ev.values("player_id", "kind").annotate(n=Count("id")):
        counts[row["player_id"]][row["kind"]] += row["n"]
    for p in players:
        c = counts[p.pk]
        p.goals = c[MatchEvent.GOAL] + c[MatchEvent.PENALTY]
        p.penalties = c[MatchEvent.PENALTY]
        p.own_goals = c[MatchEvent.OWN_GOAL]
        p.yellows = c[MatchEvent.YELLOW] + c[MatchEvent.SECOND_YELLOW]
        p.reds = c[MatchEvent.RED] + c[MatchEvent.SECOND_YELLOW]
        p.subs_in = (p.apps or 0) - (p.starts or 0)
        p.minutes = p.minutes or 0
        p.minutes_per_goal = round(p.minutes / p.goals) if p.goals else None
    return players


def top_scorers(limit=None, team=None):
    qs = (MatchEvent.objects.filter(kind__in=MatchEvent.GOAL_KINDS, player__isnull=False)
          .values("player_id", "team_id")
          .annotate(goals=Count("id"), penalties=Count("id", filter=Q(kind=MatchEvent.PENALTY)))
          .order_by("-goals"))
    if team is not None:
        qs = qs.filter(team=team)
    rows = list(qs)
    players = Player.objects.in_bulk([r["player_id"] for r in rows])
    teams = Team.objects.in_bulk([r["team_id"] for r in rows])
    apps = dict(Appearance.objects.filter(player_id__in=players.keys())
                .values_list("player_id").annotate(n=Count("id")))
    result = []
    for r in rows:
        player = players[r["player_id"]]
        result.append({
            "player": player, "team": teams[r["team_id"]], "goals": r["goals"],
            "penalties": r["penalties"], "apps": apps.get(player.pk, 0),
        })
    result.sort(key=lambda x: (-x["goals"], x["apps"], x["player"].name))
    rank = 0
    prev = None
    for i, r in enumerate(result, 1):
        if r["goals"] != prev:
            rank = i
            prev = r["goals"]
        r["rank"] = rank
    return result[:limit] if limit else result


def discipline_table():
    """Cartonașe pe echipe."""
    rows = []
    data = {r["team_id"]: r for r in MatchEvent.objects.values("team_id").annotate(
        yellow=Count("id", filter=Q(kind__in=[MatchEvent.YELLOW, MatchEvent.SECOND_YELLOW])),
        red=Count("id", filter=Q(kind__in=[MatchEvent.RED, MatchEvent.SECOND_YELLOW])),
    )}
    for team in Team.objects.all():
        d = data.get(team.pk, {"yellow": 0, "red": 0})
        rows.append({"team": team, "yellow": d["yellow"], "red": d["red"], "points": d["yellow"] + 3 * d["red"]})
    rows.sort(key=lambda r: (r["points"], r["team"].name))
    return rows


def most_carded(limit=15):
    rows = (MatchEvent.objects.filter(player__isnull=False, kind__in=[
        MatchEvent.YELLOW, MatchEvent.SECOND_YELLOW, MatchEvent.RED])
        .values("player_id", "team_id")
        .annotate(
            yellow=Count("id", filter=Q(kind__in=[MatchEvent.YELLOW, MatchEvent.SECOND_YELLOW])),
            red=Count("id", filter=Q(kind__in=[MatchEvent.RED, MatchEvent.SECOND_YELLOW])),
        ))
    rows = list(rows)
    players = Player.objects.in_bulk([r["player_id"] for r in rows])
    teams = Team.objects.in_bulk([r["team_id"] for r in rows])
    for r in rows:
        r["player"] = players[r["player_id"]]
        r["team"] = teams[r["team_id"]]
    rows.sort(key=lambda r: (-(r["red"] * 3 + r["yellow"]), r["player"].name))
    return rows[:limit]


# --------------------------------------------------------------------------- ligă

def league_overview(matches=None):
    if matches is None:
        matches = list(finished_matches())
    n = len(matches)
    goals = sum(m.home_score + m.away_score for m in matches)
    home_wins = sum(m.home_score > m.away_score for m in matches)
    away_wins = sum(m.home_score < m.away_score for m in matches)
    draws = n - home_wins - away_wins
    biggest = max(matches, key=lambda m: (abs(m.home_score - m.away_score), m.home_score + m.away_score), default=None)
    highest = max(matches, key=lambda m: (m.home_score + m.away_score, -m.round), default=None)
    total_fixtures = Match.objects.count()
    pct = lambda x: round(100 * x / n) if n else 0  # noqa: E731
    return {
        "played": n,
        "total": total_fixtures,
        "goals": goals,
        "goals_per_match": round(goals / n, 2) if n else 0,
        "minutes_per_goal": round(90 * n / goals) if goals else None,
        "home_wins": home_wins, "away_wins": away_wins, "draws": draws,
        "home_pct": pct(home_wins), "away_pct": pct(away_wins), "draw_pct": pct(draws),
        "biggest_win": biggest,
        "highest_scoring": highest,
        "clean_sheets": sum((m.home_score == 0) + (m.away_score == 0) for m in matches),
        "btts_pct": pct(sum(m.home_score > 0 and m.away_score > 0 for m in matches)),
        "over_2_5_pct": pct(sum(m.home_score + m.away_score > 2 for m in matches)),
        "yellows": MatchEvent.objects.filter(kind__in=[MatchEvent.YELLOW, MatchEvent.SECOND_YELLOW]).count(),
        "reds": MatchEvent.objects.filter(kind__in=[MatchEvent.RED, MatchEvent.SECOND_YELLOW]).count(),
    }


def team_rankings(table):
    """Cele mai bune atacuri / apărări etc. pornind de la clasament."""
    played = [r for r in table if r.played]
    if not played:
        return {}
    return {
        "best_attack": max(played, key=lambda r: (r.gf, -r.played)),
        "best_defence": min(played, key=lambda r: (r.ga, r.played)),
        "worst_attack": min(played, key=lambda r: (r.gf, r.played)),
        "worst_defence": max(played, key=lambda r: (r.ga, -r.played)),
        "most_draws": max(played, key=lambda r: r.drawn),
    }
