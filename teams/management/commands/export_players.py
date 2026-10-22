"""
Creează câte un fișier content/jucatori/<frf_id>.yml pentru fiecare jucător al clubului,
ca să poată fi editat în Pages CMS (număr, post, poză, descriere) și ales în Primul 11.

Fișierele existente nu sunt suprascrise; se actualizează doar câmpurile venite de pe FRF
(nume, în lot), pe care clubul nu le poate edita.
"""

import json

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
        self.update_lineup_choices(folder)

    # ------------------------------------------------------------------ Primul 11 în Pages CMS

    LINEUP_FIELDS = [
        ("portar", "Portar", None, ""),
        ("fundasi", "Fundași", 6, "De la dreapta la stânga, cum apar pe teren."),
        ("mijlocasi", "Mijlocași", 6, ""),
        ("mijlocasi_ofensivi", "Mijlocași ofensivi (opțional, ex. pentru 4-2-3-1)", 6, ""),
        ("atacanti", "Atacanți", 6, ""),
        ("rezerve", "Rezerve", 12, ""),
    ]
    START = "      # >>> LISTA JUCĂTORI"
    END = "      # <<< LISTA JUCĂTORI"

    DAYS = ["lun", "mar", "mie", "joi", "vin", "sâm", "dum"]

    def upcoming_matches(self, limit=6):
        """Următoarele meciuri ale echipei: (etapa, „Etapa 10 · A – B · sâm 17.10, 11:00”)."""
        from django.utils import timezone

        team = stats.our_team()
        if team is None:
            return []
        result = []
        for m in [m for m in stats.team_matches(team) if not m.is_finished][:limit]:
            if m.date:
                d = timezone.localtime(m.date)
                when = f"{self.DAYS[d.weekday()]} {d:%d.%m}, {d:%H:%M}"
            else:
                when = "dată neanunțată"
            result.append((str(m.round), f"Etapa {m.round} · {m.home.name} – {m.away.name} · {when}"))
        return result

    def update_lineup_choices(self, folder):
        """
        Scrie în .pages.yml lista completă de jucători pentru câmpurile din Primul 11,
        ca listă derulantă (select). Ordinea: jucătorii din lot după număr, apoi după nume;
        la final cei care nu mai sunt în lotul oficial.
        """
        # .pages.yml stă lângă folderul content/ (în teste, un folder temporar)
        config = content.content_dir().parent / ".pages.yml"
        if not config.exists():
            return
        text = config.read_text(encoding="utf-8")
        if self.START not in text or self.END not in text:
            self.stdout.write("Atenție: marcajele LISTA JUCĂTORI lipsesc din .pages.yml, lista nu a fost actualizată.")
            return

        players = []
        for path in folder.glob("*.yml"):
            data = content.read_yaml(path, {}) or {}
            if not data.get("frf_id"):
                continue
            number = data.get("numar")
            in_squad = data.get("in_lot") is not False
            label = data.get("nume") or str(data["frf_id"])
            if number not in (None, ""):
                label = f"{number} · {label}"
            if data.get("pozitie"):
                label += f" ({data['pozitie']})"
            if not in_squad:
                label += " – nu mai e în lot"
            sort_number = number if isinstance(number, int) else 999
            players.append(((not in_squad, sort_number, data.get("nume") or ""), str(data["frf_id"]), label))
        players.sort()

        q = json.dumps  # JSON e YAML valid și pune ghilimele corect pentru orice nume
        lines = [self.START + " – generată automat la fiecare sincronizare (export_players). Nu editați manual."]
        lines += [
            "      - name: meci",
            "        label: \"Meciul\"",
            "        type: select",
            "        required: true",
            "        description: \"Echipa apare pe site pentru acest meci și dispare singură după ce s-a jucat.\"",
            "        options:",
            "          placeholder: Alegeți meciul",
            "          values:",
        ]
        for value, mlabel in self.upcoming_matches():
            lines.append(f"            - {{ name: {q(value)}, label: {q(mlabel, ensure_ascii=False)} }}")
        for name, label, max_count, description in self.LINEUP_FIELDS:
            lines += [f"      - name: {name}", f"        label: {q(label, ensure_ascii=False)}", "        type: select"]
            if description:
                lines.append(f"        description: {q(description, ensure_ascii=False)}")
            lines.append("        options:")
            if max_count:
                lines += ["          multiple: true", f"          max: {max_count}"]
            lines.append("          placeholder: Alegeți din listă")
            lines.append("          values:")
            for _, frf_id, plabel in players:
                lines.append(f"            - {{ name: {q(frf_id)}, label: {q(plabel, ensure_ascii=False)} }}")
        lines.append(self.END)

        before = text[:text.index(self.START)]
        after = text[text.index(self.END) + len(self.END):]
        new_text = before + "\n".join(lines) + after
        if new_text != text:
            config.write_text(new_text, encoding="utf-8")
            self.stdout.write(f"Lista pentru Primul 11 actualizată în .pages.yml ({len(players)} jucători).")
