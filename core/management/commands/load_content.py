"""Importă în baza de date conținutul editat în Pages CMS (folderul content/)."""

from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from core import content
from core.models import News, Sponsor
from shop.models import Category, Order, OrderItem, Product
from teams.models import Player


class Command(BaseCommand):
    help = "Încarcă știrile, sponsorii, produsele și datele jucătorilor din folderul content/."

    @transaction.atomic
    def handle(self, *args, **options):
        self.warnings = []
        self.stdout.write(f"Știri: {self.load_news()}")
        self.stdout.write(f"Sponsori: {self.load_sponsors()}")
        self.stdout.write(f"Produse: {self.load_products()}")
        self.stdout.write(f"Jucători actualizați: {self.load_players()}")
        for w in self.warnings:
            self.stdout.write(self.style.WARNING(f"Atenție: {w}"))

    def load_news(self):
        News.objects.all().delete()
        count = 0
        for path in content.collection("stiri"):
            data, body = content.read_frontmatter(path)
            title = (data.get("titlu") or "").strip()
            if not title:
                self.warnings.append(f"{path.name}: știrea nu are titlu, a fost sărită")
                continue
            published_at = content.to_datetime(data.get("data"))
            if published_at is None:
                self.warnings.append(f"{path.name}: dată lipsă sau invalidă, se folosește data de azi")
            News.objects.create(
                title=title[:200],
                slug=slugify(path.stem)[:50] or f"stire-{count}",
                summary=(data.get("rezumat") or "")[:300],
                body=body,
                image=content.media_name(data.get("imagine")),
                is_published=content.as_bool(data.get("publicat")),
                **({"published_at": published_at} if published_at else {}),
            )
            count += 1
        return count

    def load_sponsors(self):
        Sponsor.objects.all().delete()
        items = content.read_yaml(content.content_dir() / "sponsori.yml", []) or []
        if isinstance(items, dict):  # format alternativ: {sponsori: [...]}
            items = items.get("sponsori") or []
        for i, item in enumerate(items):
            Sponsor.objects.create(
                name=(item.get("nume") or "Sponsor")[:100],
                logo=content.media_name(item.get("logo")),
                website=item.get("site") or "",
                order=i,
            )
        return len(items)

    def load_products(self):
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        count = 0
        for path in content.collection("produse"):
            data, body = content.read_frontmatter(path)
            name = (data.get("nume") or "").strip()
            if not name:
                continue
            try:
                price = Decimal(str(data.get("pret") or 0).replace(",", "."))
            except InvalidOperation:
                self.warnings.append(f"{path.name}: preț invalid")
                price = Decimal("0")
            category = None
            if data.get("categorie"):
                cname = str(data["categorie"]).strip()
                category, _ = Category.objects.get_or_create(slug=slugify(cname) or "altele", defaults={"name": cname})
            sizes = data.get("marimi") or []
            if isinstance(sizes, str):
                sizes = sizes.split(",")
            Product.objects.create(
                name=name[:120],
                slug=slugify(path.stem)[:50],
                category=category,
                description=body,
                price=price,
                image=content.media_name(data.get("imagine")),
                sizes=",".join(str(s).strip() for s in sizes if str(s).strip())[:100],
                stock=1 if content.as_bool(data.get("in_stoc")) else 0,
                is_active=content.as_bool(data.get("activ")),
            )
            count += 1
        return count

    def load_players(self):
        count = 0
        for path in content.collection("jucatori", "*.yml"):
            data = content.read_yaml(path, {}) or {}
            try:
                frf_id = int(data.get("frf_id") or path.stem)
            except ValueError:
                continue
            player = Player.objects.filter(frf_id=frf_id).first()
            if player is None:
                continue
            number = data.get("numar")
            try:
                number = int(number) if number not in (None, "") else None
            except (TypeError, ValueError):
                number = None
            position = data.get("pozitie") or ""
            if position not in dict(Player.POSITIONS):
                position = ""
            player.number = number
            player.position = position
            player.bio = data.get("descriere") or ""
            player.image = content.media_name(data.get("poza"))
            player.save(update_fields=["number", "position", "bio", "image"])
            count += 1
        return count
