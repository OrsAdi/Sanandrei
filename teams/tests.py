from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.urls import reverse

from . import frf, stats
from .models import Match, MatchEvent, Player, Team
from .sync import save_match_details, save_round_matches

TZ = ZoneInfo("Europe/Bucharest")

ROUND_HTML = """
<div class="panel-calendar-match "><div class="">
<div class="row"><div class="col-lg-12 hidden-sm hidden-xs">
  <div class="col-sm-6 col-xs-12 text-left matchCompetitionList">Sambata, 3  Octombrie 2026, 11:00</div>
  <div class="col-sm-6 col-xs-12 text-right matchCompetitionList">Teren: Comunal / CARANI</div>
</div></div>
<div class="row"><div class="col-lg-12 hidden-sm hidden-xs">
  <div class="col-lg-4 col-md-3 text-right matchTeamList"><a href="https://www.frf-ajf.ro/timis/echipe/cs-snandrei-timi-205.html">CS Sânandrei Timiș</a></div>
  <div class="col-lg-2 col-md-2 text-center matchScoreList"><a href="https://www.frf-ajf.ro/timis/meciuri/cs-snandrei-timi-as-reca-1227060.html">2 - 1 (0-0)</a></div>
  <div class="col-lg-4 col-md-3 text-left matchTeamList"><a href="https://www.frf-ajf.ro/timis/echipe/as-reca-259.html">AS Recaș</a></div>
</div></div></div></div>
<div class="panel-calendar-match "><div class="">
<div class="row"><div class="col-lg-12 hidden-sm hidden-xs">
  <div class="col-sm-6 col-xs-12 text-left matchCompetitionList">Joi, 1 Ianuarie 1970, hh:mm</div>
  <div class="col-sm-6 col-xs-12 text-right matchCompetitionList">Teren: Comunal / PARTA</div>
</div></div>
<div class="row"><div class="col-lg-12 hidden-sm hidden-xs">
  <div class="col-lg-4 col-md-3 text-right matchTeamList"><a href="https://www.frf-ajf.ro/timis/echipe/as-reca-259.html">AS Recaș</a></div>
  <div class="col-lg-2 col-md-2 text-center matchScoreList"><a href="https://www.frf-ajf.ro/timis/meciuri/as-reca-cs-snandrei-timi-1227200.html">?-?</a></div>
  <div class="col-lg-4 col-md-3 text-left matchTeamList"><a href="https://www.frf-ajf.ro/timis/echipe/cs-snandrei-timi-205.html">CS Sânandrei Timiș</a></div>
</div></div></div></div>
"""


def _player_row(pid, name, born="10-07-1985"):
    return f"""
<div class="row "><div class="images"><img src="https://www.frf-ajf.ro/poze_jucatori/avatar.jpg"></div>
<div class="summary entry-summary"><h5 class="product_title entry-title">
<a href="https://www.frf-ajf.ro/timis/jucatori/x-{pid}.html">{name}</a></h5>
<p><b>Carnet: </b>TM{pid}&nbsp; {born}</p></div></div>"""


def _event(kind, minute, side, body):
    col = '<div class="col-sm-6 col-sm-offset-6 " data-align="right">' if side == "away" else '<div class="col-sm-6">'
    return f'{col}<div class="timeline_box timeline_box_{kind}"><div class="date">{minute}\'</div><p>{body}</p></div></div>'


def _link(pid, name):
    return f'<a href="https://www.frf-ajf.ro/timis/jucatori/x-{pid}.html">{name}</a>'


HOME_STARTERS = [(i, f"Acasa {i}") for i in range(1, 12)]
AWAY_STARTERS = [(i, f"Oaspete {i}") for i in range(101, 112)]

MATCH_HTML = (
    '<div class="delegaribox">Pauza: 0-0</div>'
    '<table><tr><td><strong>Arbitru</strong><br/><a href="#">Brasoveanu Alexandru</a></td></tr></table>'
    '<div class="col-md-4 blueColored"><h4>Titulari</h4>'
    + "".join(_player_row(i, n) for i, n in HOME_STARTERS)
    + "<h4>Rezerve</h4>" + _player_row(12, "Rezerva Acasa") + "</div>"
    '<div class="col-md-4 blueColored"><h4>Titulari</h4>'
    + "".join(_player_row(i, n) for i, n in AWAY_STARTERS)
    + "<h4>Rezerve</h4></div>"
    '<div class="col-md-4"><div class="timeline_bar"><div class="row">'
    + _event("YC", 32, "home", _link(5, "Acasa 5") + "<br/><span style='font-size:10px;'>CG: da dovada de comportament nesportiv</span>")
    + _event("CH", 46, "home", "Intră: " + _link(12, "Rezerva Acasa") + "<br/>Iese: " + _link(1, "Acasa 1"))
    + _event("G", 52, "home", _link(3, "Acasa 3") + "<br/><span style='font-size:10px;'>Gol</span>")
    + _event("G", 70, "away", _link(104, "Oaspete 4") + "<br/><span style='font-size:10px;'>Gol</span>")
    + _event("G", 72, "away", _link(105, "Oaspete 5") + "<br/><span style='font-size:10px;'>Gol(a)</span>")
    + _event("RC", 80, "away", _link(106, "Oaspete 6") + "<br/><span style='font-size:10px;'>CR: primeste un al doilea avertisment in acelasi meci</span>")
    + "</div></div></div>"
)


class ParserTests(TestCase):
    def test_parse_round(self):
        matches = frf.parse_round(ROUND_HTML, 7)
        self.assertEqual(len(matches), 2)
        played, pending = matches
        self.assertEqual(played["frf_id"], 1227060)
        self.assertEqual(played["home"]["frf_id"], 205)
        self.assertEqual(played["away"]["name"], "AS Recaș")
        self.assertEqual((played["home_score"], played["away_score"], played["ht_home"], played["ht_away"]), (2, 1, 0, 0))
        self.assertEqual(played["date"], datetime(2026, 10, 3, 11, 0))
        self.assertEqual(played["venue"], "Comunal / CARANI")
        self.assertFalse(pending["is_finished"])
        self.assertIsNone(pending["date"], "data placeholder 1970 trebuie ignorată")

    def test_parse_match(self):
        data = frf.parse_match(MATCH_HTML)
        self.assertEqual(data["referee"], "Brasoveanu Alexandru")
        self.assertEqual(data["ht"], (0, 0))
        self.assertEqual(len(data["home_players"]), 12)
        self.assertEqual(sum(p["is_starter"] for p in data["home_players"]), 11)
        kinds = [(e["kind"], e["side"], e["minute"]) for e in data["events"]]
        self.assertEqual(kinds, [
            ("yellow", "home", 32), ("sub", "home", 46), ("goal", "home", 52),
            ("goal", "away", 70), ("own_goal", "away", 72), ("second_yellow", "away", 80),
        ])
        sub = data["events"][1]
        self.assertEqual((sub["player_id"], sub["player_out_id"]), (12, 1))

    def test_compute_minutes(self):
        data = frf.parse_match(MATCH_HTML)
        home = frf.compute_minutes(data["home_players"], [e for e in data["events"] if e["side"] == "home"])
        self.assertEqual(home[1], (0, 46, 46))
        self.assertEqual(home[12], (46, None, 44))
        self.assertEqual(home[2], (0, None, 90))
        away = frf.compute_minutes(data["away_players"], [e for e in data["events"] if e["side"] == "away"])
        self.assertEqual(away[106], (0, 80, 80), "eliminatul iese din joc")

    def test_parse_ro_datetime(self):
        self.assertEqual(frf.parse_ro_datetime("Duminica, 22 Martie 2027, 16:30"), datetime(2027, 3, 22, 16, 30))
        self.assertIsNone(frf.parse_ro_datetime("Data nu este disponibila, hh:mm"))


class SyncAndStatsTests(TestCase):
    def setUp(self):
        save_round_matches(frf.parse_round(ROUND_HTML, 7))
        self.match = Match.objects.get(frf_id=1227060)
        save_match_details(self.match, frf.parse_match(MATCH_HTML))
        self.ours = Team.objects.get(frf_id=205)
        self.other = Team.objects.get(frf_id=259)

    def test_sync_creates_data(self):
        self.assertEqual(Team.objects.count(), 2)
        self.assertEqual(Match.objects.count(), 2)
        self.assertTrue(self.match.details_synced)
        self.assertEqual(self.match.appearances.count(), 23)
        own_goal = self.match.events.get(kind=MatchEvent.OWN_GOAL)
        self.assertEqual(own_goal.team, self.other)

    def test_resync_is_idempotent(self):
        save_match_details(self.match, frf.parse_match(MATCH_HTML))
        self.assertEqual(self.match.appearances.count(), 23)
        self.assertEqual(self.match.events.count(), 6)

    def test_score_change_resets_details(self):
        rows = frf.parse_round(ROUND_HTML.replace("2 - 1 (0-0)", "3 - 1 (0-0)"), 7)
        save_round_matches(rows)
        self.match.refresh_from_db()
        self.assertEqual(self.match.home_score, 3)
        self.assertFalse(self.match.details_synced)

    def test_standings(self):
        table = stats.standings()
        self.assertEqual(table[0].team, self.ours)
        self.assertEqual((table[0].points, table[0].gf, table[0].ga, table[0].form), (3, 2, 1, ["V"]))
        self.assertEqual(table[1].points, 0)

    def test_points_adjustment(self):
        self.ours.points_adjustment = -6
        self.ours.save()
        table = stats.standings()
        self.assertEqual(table[0].team, self.other)
        self.assertEqual(table[1].points, -3)

    def test_player_stats_and_scorers(self):
        players = {p.frf_id: p for p in stats.player_stats(team=self.ours)}
        self.assertEqual(players[3].goals, 1)
        self.assertEqual(players[5].yellows, 1)
        self.assertEqual(players[12].minutes, 44)
        scorers = stats.top_scorers()
        self.assertEqual({s["player"].frf_id for s in scorers}, {3, 104}, "autogolul nu contează la golgeteri")
        away = {p.frf_id: p for p in stats.player_stats(team=self.other)}
        self.assertEqual((away[106].yellows, away[106].reds), (1, 1))

    def test_team_summary(self):
        s = stats.team_summary(self.ours)
        self.assertEqual((s["won"], s["gf"], s["ga"], s["home"]["points"]), (1, 2, 1, 3))
        minutes = stats.goal_minutes(self.ours)
        self.assertEqual(sum(b["scored"] for b in minutes), 2)
        self.assertEqual(sum(b["conceded"] for b in minutes), 1)


class ViewTests(TestCase):
    def setUp(self):
        save_round_matches(frf.parse_round(ROUND_HTML, 7))
        self.match = Match.objects.get(frf_id=1227060)
        save_match_details(self.match, frf.parse_match(MATCH_HTML))

    def test_pages_render(self):
        player = Player.objects.get(frf_id=3)
        team = Team.objects.get(frf_id=259)
        urls = [
            reverse("home"), reverse("squad_list"), reverse("fixtures"), reverse("standings"),
            reverse("standings_view", args=["deplasare", 7]), reverse("fixtures_round", args=[7]),
            reverse("stats"), reverse("team_list"),
            team.get_absolute_url(), self.match.get_absolute_url(),
            Match.objects.get(frf_id=1227200).get_absolute_url(),
            player.get_absolute_url(), reverse("search"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_invalid_round_or_venue_is_404(self):
        self.assertEqual(self.client.get(reverse("standings_view", args=["general", 99])).status_code, 404)
        self.assertEqual(self.client.get(reverse("standings_view", args=["altceva", 7])).status_code, 404)
        self.assertEqual(self.client.get(reverse("fixtures_round", args=[99])).status_code, 404)

    def test_search_page_contains_index(self):
        response = self.client.get(reverse("search"))
        self.assertContains(response, 'id="search-index"')
        self.assertContains(response, "Acasa 3")

    def test_squad_groups_by_position(self):
        Player.objects.filter(frf_id=1).update(position="Portar", number=1)
        response = self.client.get(reverse("squad_list"))
        self.assertContains(response, "Portari")
        self.assertContains(response, "#1")

    def test_empty_database(self):
        Team.objects.all().delete()
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)
        self.assertEqual(self.client.get(reverse("squad_list")).status_code, 404)
