"""
Creează câte un fișier content/jucatori/<frf_id>.yml pentru fiecare jucător al clubului,
ca să poată fi editat în Pages CMS (număr, post, poză, descriere) și ales în Primul 11.

Fișierele existente nu sunt suprascrise; se actualizează doar câmpurile venite de pe FRF
(nume, în lot), pe care clubul nu le poate edita.
"""

from django.core.management.base import BaseCommand
from django.db.models import Q

from core import content
from teams import stats
from teams.models import Player

FRF_FIELDS = ("nume", "in_lot")


class Command(BaseCommand):
    help = "Creează/actualizează fișierele jucătorilor din content/jucatori/."

    def handle(self, *args, **options):
        team = stats.our_team()
        if team is None:
            self.stdout.write("Echipa noastră nu e încă în baza de date.")
            return
        folder = content.content_dir() / "jucatori"
        players = (Player.objects.filter(team=team, frf_id__isnull=False)
                   .filter(Q(registered=True) | Q(appearances__isnull=False)).distinct())
        created = updated = 0
        for p in players:
            path = folder / f"{p.frf_id}.yml"
            frf_values = {"nume": p.name, "in_lot": p.registered}
            if path.exists():
                data = content.read_yaml(path, {}) or {}
                if any(data.get(k) != v for k, v in frf_values.items()):
                    data.update(frf_values)
                    content.write_yaml(path, data)
                    updated += 1
                continue
            content.write_yaml(path, {
                "frf_id": p.frf_id,
                **frf_values,
                "numar": p.number,
                "pozitie": p.position or "",
                "poza": f"/media/{p.image.name}" if p.image else "",
                "descriere": p.bio or "",
            })
            created += 1
        self.stdout.write(f"Fișiere jucători: {created} create, {updated} actualizate.")
