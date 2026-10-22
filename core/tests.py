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
