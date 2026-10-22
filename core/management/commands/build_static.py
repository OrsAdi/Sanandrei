"""
Generează site-ul static (pentru GitHub Pages) în folderul dist/.

Pornește de la pagina principală și urmează toate linkurile interne, deci orice pagină
la care se poate ajunge din site e generată automat. Dacă un link duce la o pagină
inexistentă, comanda se oprește cu eroare (site-ul vechi rămâne online).

    python manage.py load_content      # întâi conținutul din content/
    python manage.py build_static      # apoi site-ul
"""

import html
import os
import re
import shutil
import time
from collections import deque
from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import Client

LINK_RE = re.compile(r'\s(?:href|src)="([^"]*)"')
SKIP_SCHEMES = ("http://", "https://", "mailto:", "tel:", "javascript:", "data:", "//")
SEEDS = ["/", "/404.html", "/cauta/", "/magazin/cos/", "/magazin/comanda/"]


class Command(BaseCommand):
    help = "Generează site-ul static în dist/ (toate paginile la care se ajunge din pagina principală)."

    def add_arguments(self, parser):
        parser.add_argument("--out", default="dist", help="Folderul de ieșire (implicit: dist).")

    def handle(self, *args, **options):
        started = time.monotonic()
        out = Path(options["out"]).resolve()
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)

        prefix = settings.SITE_URL_PREFIX  # "/" sau "/Sanandrei/"
        self._copy_tree(settings.BASE_DIR / "static", out / "static")
        self._copy_tree(Path(settings.MEDIA_ROOT), out / "media")
        self._shrink_images(out / "media")

        client = Client(raise_request_exception=True)
        queue = deque(SEEDS)
        seen = set(SEEDS)
        pages = []
        broken = []  # (pagina, link, motiv) – opresc publicarea
        missing_media = set()  # poze lipsă – doar avertisment
        referrer = {s: "(start)" for s in SEEDS}

        while queue:
            path = queue.popleft()
            response = client.get(path)
            expected = 404 if path == "/404.html" else 200
            if response.status_code != expected:
                broken.append((referrer[path], path, response.status_code))
                continue
            body = response.content.decode("utf-8")
            self._write(out, path, body)
            pages.append(path)

            for raw in LINK_RE.findall(body):
                link = html.unescape(raw).strip()
                if not link or link.startswith(("#", "?")) or link.lower().startswith(SKIP_SCHEMES):
                    if link.startswith("?"):
                        broken.append((path, link, "link cu parametri – nu funcționează pe un site static"))
                    continue
                parts = urlsplit(link)
                target = parts.path
                if parts.query:
                    broken.append((path, link, "link cu parametri – nu funcționează pe un site static"))
                    continue
                if not target.startswith(prefix):
                    broken.append((path, link, "link în afara site-ului (lipsește prefixul)"))
                    continue
                local = "/" + target[len(prefix):]
                if local.startswith(("/static/", "/media/")):
                    if not (out / local.lstrip("/")).exists():
                        if local.startswith("/media/"):
                            missing_media.add(local)
                        else:
                            broken.append((path, link, "fișier lipsă"))
                    continue
                if local.startswith("/admin/"):
                    continue
                if local not in seen:
                    seen.add(local)
                    referrer[local] = path
                    queue.append(local)

        for m in sorted(missing_media):
            self.stdout.write(self.style.WARNING(f"Atenție: poza {m} nu există în media/ (a fost ștearsă?)"))
        if broken:
            for page, link, why in broken[:50]:
                self.stderr.write(f"  {page} → {link}: {why}")
            raise CommandError(f"{len(broken)} linkuri sau fișiere stricate – site-ul NU a fost publicat.")

        (out / ".nojekyll").write_text("")
        if os.environ.get("SITE_CNAME"):
            (out / "CNAME").write_text(os.environ["SITE_CNAME"].strip() + "\n")
        self._write_sitemap(out, pages, prefix)
        self.stdout.write(self.style.SUCCESS(
            f"Gata: {len(pages)} pagini în {out} ({time.monotonic() - started:.0f}s)."))

    @staticmethod
    def _copy_tree(src, dst):
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".gitkeep", ".DS_Store"))

    def _shrink_images(self, folder, max_side=1600):
        """Pozele de pe telefon (5 MB+) sunt micșorate în dist/; originalele rămân în repo."""
        from PIL import Image, ImageOps

        shrunk = 0
        for path in folder.rglob("*"):
            if path.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp") or path.stat().st_size < 300_000:
                continue
            try:
                with Image.open(path) as im:
                    im = ImageOps.exif_transpose(im)
                    if max(im.size) > max_side:
                        im.thumbnail((max_side, max_side))
                    if path.suffix.lower() in (".jpg", ".jpeg"):
                        im.convert("RGB").save(path, quality=82, optimize=True, progressive=True)
                    else:
                        im.save(path, optimize=True)
                shrunk += 1
            except Exception as exc:  # noqa: BLE001 - o poză stricată nu oprește site-ul
                self.stderr.write(f"Poza {path.name} nu a putut fi micșorată: {exc}")
        if shrunk:
            self.stdout.write(f"Poze optimizate: {shrunk}")

    @staticmethod
    def _write(out, path, body):
        if path.endswith(".html"):
            target = out / path.lstrip("/")
        else:
            target = out / path.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")

    @staticmethod
    def _write_sitemap(out, pages, prefix):
        domain = (os.environ.get("SITE_DOMAIN") or settings.SITE_DOMAIN).rstrip("/")
        if not domain:
            return
        urls = "".join(f"<url><loc>{domain}{prefix}{p.lstrip('/')}</loc></url>"
                       for p in pages if not p.endswith(".html"))
        (out / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n', encoding="utf-8")
        (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {domain}{prefix}sitemap.xml\n")
