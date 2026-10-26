import shutil
import tempfile
from pathlib import Path

import yaml
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from teams import frf
from teams.models import Match, Player
from teams.sync import save_match_details, save_round_matches
from teams.tests import MATCH_HTML, ROUND_HTML

from . import content
from .models import News, Sponsor


class ContentTestCase(TestCase):
    """Folosește un folder content/ temporar."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        override = override_settings(CONTENT_DIR=self.tmp / "content")
        override.enable()
        self.addCleanup(override.disable)
        (self.tmp / "content").mkdir()

    def write(self, rel, text):
        path = self.tmp / "content" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


class NewsAndSettingsTests(ContentTestCase):
    def test_news_loaded_from_markdown(self):
        self.write("stiri/2026-10-20-victorie.md",
                   "---\ntitlu: Victorie\ndata: 2026-10-20T18:30\nimagine: /media/stiri/a.jpg\n---\nText **gros**\n\n![x](/media/stiri/a.jpg)\n")
        self.write("stiri/2026-10-21-ciorna.md", "---\ntitlu: Ascunsă\npublicat: false\n---\nx")
        call_command("load_content", stdout=open("/dev/null", "w"))
        item = News.objects.get(slug="2026-10-20-victorie")
        self.assertEqual(item.image.name, "stiri/a.jpg")
        self.assertIn("<strong>gros</strong>", item.body_html)
        self.assertIn('src="/media/stiri/a.jpg"', item.body_html)
        response = self.client.get(reverse("news_list"))
        self.assertContains(response, "Victorie")
        self.assertNotContains(response, "Ascunsă")
        self.assertEqual(self.client.get(reverse("news_detail", args=["2026-10-21-ciorna"])).status_code, 404)

    def test_reload_replaces_old_news(self):
        path = self.write("stiri/a.md", "---\ntitlu: Prima\n---\nx")
        call_command("load_content", stdout=open("/dev/null", "w"))
        path.unlink()
        call_command("load_content", stdout=open("/dev/null", "w"))
        self.assertFalse(News.objects.exists())

    def test_sponsors_and_settings(self):
        self.write("sponsori.yml", "- nume: Primăria\n  site: https://example.com\n")
        self.write("setari.yml", "email: club@example.com\ntelefon: '0722 000 000'\n")
        call_command("load_content", stdout=open("/dev/null", "w"))
        self.assertEqual(Sponsor.objects.get().name, "Primăria")
        response = self.client.get(reverse("contact"))
        self.assertContains(response, "club@example.com")
        self.assertContains(response, "0722 000 000")
        self.assertContains(response, 'data-web3form="contact"')


class HomeDesignTests(ContentTestCase):
    def test_slideshow_from_cms(self):
        self.write("slideshow.yml", yaml.safe_dump([
            {"imagine": "/media/slides/a.jpg", "titlu": "Victorie!", "eticheta": "Meci", "link": "/meciuri/"},
            {"imagine": "/media/slides/b.jpg", "activ": False},
            {"titlu": ""},
        ]))
        slides = content.slideshow()
        self.assertEqual(len(slides), 1, "slide-urile ascunse sau goale nu apar")
        self.assertEqual(slides[0]["image"], "/media/slides/a.jpg")
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Victorie!")
        self.assertContains(response, 'class="slide-img"')

    def test_automatic_slides_and_no_cards_without_news(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "data-slider")
        self.assertNotContains(response, "feature-card")
        self.assertContains(response, "<span>Portocaliu</span>")

    def test_cards_are_the_two_latest_news(self):
        for i, title in enumerate(["Veche", "Mijloc", "Nouă"]):
            self.write(f"stiri/2026-10-1{i}-x{i}.md", f"---\ntitlu: {title}\ndata: 2026-10-1{i}T10:00\n---\nx")
        self.write("stiri/2026-10-19-ascunsa.md", "---\ntitlu: Ascunsă\ndata: 2026-10-19T10:00\npublicat: false\n---\nx")
        call_command("load_content", stdout=open("/dev/null", "w"))
        html = self.client.get(reverse("home")).content.decode()
        cards = html[html.index('class="featured"'):html.index("</section>", html.index('class="featured"'))]
        self.assertEqual(cards.count("feature-card"), 2)
        self.assertIn("Nouă", cards)
        self.assertIn("Mijloc", cards)
        self.assertNotIn("Veche", cards)
        self.assertNotIn("Ascunsă", cards)

    def test_site_link_prefix(self):
        with override_settings(SITE_URL_PREFIX="/Sanandrei/"):
            self.assertEqual(content.site_link("/contact/"), "/Sanandrei/contact/")
            self.assertEqual(content.site_link("stiri/"), "/Sanandrei/stiri/")
            self.assertEqual(content.site_link("/Sanandrei/lot/"), "/Sanandrei/lot/")
            self.assertEqual(content.site_link("https://facebook.com/x"), "https://facebook.com/x")
        self.assertEqual(content.site_link("/contact/"), "/contact/")

    def test_social_links_and_motto_from_settings(self):
        self.write("setari.yml", "facebook: https://facebook.com/club\nmoto: Mândria comunei\n")
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'href="https://facebook.com/club"')
        self.assertContains(response, "<span>Mândria</span>")


class PlayersAndLineupTests(ContentTestCase):
    def setUp(self):
        super().setUp()
        save_round_matches(frf.parse_round(ROUND_HTML, 7))
        save_match_details(Match.objects.get(frf_id=1227060), frf.parse_match(MATCH_HTML))
        Player.objects.filter(team__frf_id=205).update(registered=True)

    def test_export_players_then_load_edits(self):
        call_command("export_players", stdout=open("/dev/null", "w"))
        path = self.tmp / "content" / "jucatori" / "3.yml"
        data = yaml.safe_load(path.read_text())
        self.assertEqual(data["nume"], "Acasa 3")
        data.update(numar=9, pozitie="Atacant", poza="/media/jucatori/3.jpg", descriere="Golgeter")
        path.write_text(yaml.safe_dump(data, allow_unicode=True))
        call_command("load_content", stdout=open("/dev/null", "w"))
        p = Player.objects.get(frf_id=3)
        self.assertEqual((p.number, p.position, p.image.name, p.bio), (9, "Atacant", "jucatori/3.jpg", "Golgeter"))
        # o nouă exportare nu suprascrie editările clubului
        call_command("export_players", stdout=open("/dev/null", "w"))
        self.assertEqual(yaml.safe_load(path.read_text())["numar"], 9)

    def test_export_writes_player_dropdown_for_lineup(self):
        shutil.copy(Path(__file__).resolve().parent.parent / ".pages.yml", self.tmp / ".pages.yml")
        call_command("export_players", stdout=open("/dev/null", "w"))
        path = self.tmp / "content" / "jucatori" / "3.yml"
        data = yaml.safe_load(path.read_text())
        path.write_text(yaml.safe_dump(dict(data, numar=10, pozitie="Atacant"), allow_unicode=True))
        call_command("export_players", stdout=open("/dev/null", "w"))
        config = yaml.safe_load((self.tmp / ".pages.yml").read_text())
        fields = {f["name"]: f for c in config["content"] if c["name"] == "primul11" for f in c["fields"]}
        values = fields["titulari"]["options"]["values"]
        self.assertEqual(fields["formatie"]["type"], "select")
        self.assertTrue(fields["titulari"]["options"]["multiple"])
        self.assertEqual(values[0], {"name": "3", "label": "10 · Acasa 3 (Atacant)"}, "jucătorii cu număr primii")
        self.assertEqual(len(values), Player.objects.filter(team__frf_id=205).count())

    def test_lineup_shown_for_next_match(self):
        self.write("primul11.yml", yaml.safe_dump({
            "publicat": True, "etapa": 7, "portar": "1",
            "fundasi": ["2", "3", "4", "5"], "mijlocasi": ["6", "7", "8"], "atacanti": [9, 10, 11],
            "rezerve": ["12"], "antrenor": "Ion",
        }))
        lineup = content.lineup_for_round(7)
        self.assertEqual(lineup["formation"], "4-3-3")
        self.assertTrue(lineup["complete"])
        self.assertIsNone(content.lineup_for_round(8))
        upcoming = Match.objects.get(frf_id=1227200)
        response = self.client.get(upcoming.get_absolute_url())
        self.assertContains(response, "Echipa de start")
        self.assertContains(response, "4-3-3")

    def test_match_field_and_duplicates(self):
        self.write("primul11.yml", yaml.safe_dump({
            "meci": "7", "portar": "1", "fundasi": ["2", "3", "1"], "atacanti": ["3", "9"], "rezerve": ["9", "12"],
        }))
        lineup = content.lineup_for_round(7)
        self.assertIsNotNone(lineup, "fără bifa „publicat” echipa se afișează")
        names = [p.frf_id for row in lineup["rows"] for p in row["players"]]
        self.assertEqual(sorted(names), [1, 2, 3, 9], "fiecare jucător apare o singură dată")
        self.assertEqual([p.frf_id for p in lineup["bench"]], [12])

    def test_export_lists_upcoming_matches(self):
        shutil.copy(Path(__file__).resolve().parent.parent / ".pages.yml", self.tmp / ".pages.yml")
        call_command("export_players", stdout=open("/dev/null", "w"))
        config = yaml.safe_load((self.tmp / ".pages.yml").read_text())
        fields = {f["name"]: f for c in config["content"] if c["name"] == "primul11" for f in c["fields"]}
        self.assertEqual([v["name"] for v in fields["meci"]["options"]["values"]], ["7"])
        self.assertNotIn("publicat", fields)
        self.assertEqual(fields["titulari"]["options"]["max"], 11)
        self.assertNotIn("fundasi", fields, "o singură listă de titulari, fără dubluri între linii")

    def test_starters_list_placed_by_formation(self):
        self.write("primul11.yml", yaml.safe_dump({
            "meci": "7", "formatie": "4-2-3-1",
            "titulari": [str(i) for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 3]],
            "rezerve": ["11", "12"],
        }))
        lineup = content.lineup_for_round(7)
        self.assertEqual(lineup["formation"], "4-2-3-1")
        rows = [[p.frf_id for p in r["players"]] for r in lineup["rows"]]
        self.assertEqual(rows, [[11], [8, 9, 10], [6, 7], [2, 3, 4, 5], [1]], "atac sus, portar jos")
        self.assertEqual([p.frf_id for p in lineup["bench"]], [12], "titularii nu apar la rezerve")

    def test_incomplete_starters_still_shown(self):
        self.write("primul11.yml", yaml.safe_dump({"meci": "7", "formatie": "4-3-3",
                                                   "titulari": ["1", "2", "3", "4", "5", "6"]}))
        self.assertEqual(content.lineup_for_round(7)["formation"], "4-1")

    def test_home_player_cards_follow_lineup(self):
        self.write("primul11.yml", yaml.safe_dump({
            "meci": "7", "formatie": "4-3-3", "titulari": [str(i) for i in range(1, 12)], "rezerve": ["12"]}))
        html = self.client.get(reverse("home")).content.decode()
        self.assertIn("Echipa de start", html)
        self.assertEqual(html.count('class="player-tile'), 11)
        first = html.index('class="player-tile')
        self.assertIn("Portar", html[first:first + 2500], "portarul e primul card")
        self.assertIn("tile-stats", html)
        self.assertIn("Rezerva Acasa", html[html.index("players-foot"):])

    def test_match_tiles_link_and_last5(self):
        html = self.client.get(reverse("home")).content.decode()
        upcoming, played = Match.objects.get(frf_id=1227200), Match.objects.get(frf_id=1227060)
        self.assertIn(f'class="match-tile" href="{upcoming.get_absolute_url()}"', html)
        self.assertIn(f'class="match-tile" href="{played.get_absolute_url()}"', html)
        self.assertIn(f'href="{reverse("standings")}"', html)
        self.assertEqual(html.count("Ultimele 5 rezultate"), 3)
        self.assertIn("2-1", html, "scorul ultimului meci în lista de rezultate")

    def test_season_tiles(self):
        html = self.client.get(reverse("home")).content.decode()
        self.assertEqual(html.count('class="stat-tile"'), 6)
        self.assertIn("Cea mai mare victorie: <b>2-1</b>", html, "scorul din perspectiva noastră")
        self.assertIn("Acasă vs deplasare", html)

    def test_no_player_cards_without_lineup(self):
        html = self.client.get(reverse("home")).content.decode()
        self.assertNotIn("player-tile", html)
        self.assertNotIn("players-band", html)

    def test_unpublished_lineup_hidden(self):
        self.write("primul11.yml", "publicat: false\netapa: 7\nportar: '1'\n")
        self.assertIsNone(content.lineup_for_round(7))


class BuildStaticTests(ContentTestCase):
    def test_build_writes_pages_and_no_broken_links(self):
        save_round_matches(frf.parse_round(ROUND_HTML, 7))
        save_match_details(Match.objects.get(frf_id=1227060), frf.parse_match(MATCH_HTML))
        self.write("produse/tricou.md", "---\nnume: Tricou\npret: 80\nmarimi: [M, L]\ncategorie: Echipament\n---\n")
        call_command("load_content", stdout=open("/dev/null", "w"))
        out = self.tmp / "dist"
        call_command("build_static", out=str(out), stdout=open("/dev/null", "w"))
        for page in ["index.html", "404.html", "lot/index.html", "clasament/index.html",
                     "clasament/deplasare/etapa/7/index.html", "meciuri/etapa/7/index.html",
                     "magazin/tricou/index.html", "magazin/categorie/echipament/index.html",
                     "static/css/style.css", ".nojekyll"]:
            with self.subTest(page=page):
                self.assertTrue((out / page).exists())
