"""Date demonstrative (liga inventată) pentru a testa site-ul fără acces la frf-ajf.ro.

    python manage.py seed_demo          # NU rulați pe baza de date reală
"""

import random
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from teams.models import Match, Player, SyncRun, Team
from teams.sync import save_match_details, save_round_matches


NAMES = ["Popescu", "Ionescu", "Marin", "Stan", "Dumitru", "Lazăr", "Tudor", "Moldovan", "Rusu", "Oprea",
         "Barbu", "Ilie", "Ene", "Florea", "Toma", "Crăciun", "Nistor", "Cozma", "Avram", "Sima"]
FIRST = ["Andrei", "Mihai", "Alex", "Ionuț", "Vlad", "Darius", "Paul", "Robert", "Sergiu", "Cosmin"]
TEAMS = ["CS Sânandrei Timiș", "AS Recaș", "CS Giroc", "ACS Dumbrăvița", "CS Ghiroda", "AS Becicherecu Mic",
         "CS Jimbolia", "ACS Lugoj II", "CS Făget", "AS Pișchia"]


class Command(BaseCommand):
    help = "Încarcă o ligă demonstrativă (doar pentru testare locală)."

    def add_arguments(self, parser):
        parser.add_argument("--played", type=int, default=9, help="Câte etape să fie disputate.")

    def handle(self, *args, **opts):
        if Match.objects.exists():
            raise CommandError("Baza de date are deja meciuri. Folosiți o bază de date goală.")
        rnd = random.Random(7)
        teams = [{"frf_id": settings.OUR_TEAM_FRF_ID if i == 0 else 900 + i, "name": n, "url": ""}
                 for i, n in enumerate(TEAMS)]
        squads = {t["frf_id"]: [{"frf_id": t["frf_id"] * 100 + k,
                                 "name": f"{rnd.choice(NAMES)} {rnd.choice(FIRST)}",
                                 "birth_date": None, "card_number": "", "photo_url": ""}
                                for k in range(1, 19)] for t in teams}

        # programare tur-retur (round robin)
        ids = list(range(len(teams)))
        rounds = []
        for r in range(len(teams) - 1):
            pairs = [(ids[i], ids[-1 - i]) for i in range(len(teams) // 2)]
            rounds.append(pairs if r % 2 == 0 else [(b, a) for a, b in pairs])
            ids = [ids[0]] + [ids[-1]] + ids[1:-1]
        rounds += [[(b, a) for a, b in pairs] for pairs in rounds]

        start = datetime(2026, 8, 15, 11, 0)
        frf_match = 1_000_000
        for n, pairs in enumerate(rounds, start=1):
            matches = []
            for h, a in pairs:
                frf_match += 1
                played = n <= opts["played"]
                hs, as_ = (rnd.choice([0, 0, 1, 1, 2, 2, 3, 4]), rnd.choice([0, 0, 1, 1, 2, 3])) if played else (None, None)
                matches.append({
                    "frf_id": frf_match, "frf_url": "", "round": n,
                    "date": start + timedelta(days=7 * (n - 1)), "venue": "Teren Comunal",
                    "home": teams[h], "away": teams[a], "home_score": hs, "away_score": as_,
                    "ht_home": None, "ht_away": None, "is_finished": played,
                })
            save_round_matches(matches)

        for m in Match.objects.filter(is_finished=True).select_related("home", "away"):
            details = {"referee": "Arbitru Demo", "ht": (min(m.home_score, 1), min(m.away_score, 1)),
                       "home_players": [], "away_players": [], "events": []}
            for side, team, goals in (("home", m.home, m.home_score), ("away", m.away, m.away_score)):
                squad = squads[team.frf_id]
                lineup = [dict(p, is_starter=i < 11) for i, p in enumerate(rnd.sample(squad, 14))]
                details[f"{side}_players"] = lineup
                starters = [p for p in lineup if p["is_starter"]]
                for _ in range(goals):
                    details["events"].append({"minute": rnd.randint(3, 90), "side": side, "kind": "goal",
                                              "player_id": rnd.choice(starters[1:])["frf_id"], "player_out_id": None})
                if rnd.random() < .6:
                    details["events"].append({"minute": rnd.randint(10, 85), "side": side, "kind": "yellow",
                                              "player_id": rnd.choice(starters)["frf_id"], "player_out_id": None})
                for k, sub in enumerate(lineup[11:]):
                    details["events"].append({"minute": 60 + k * 8, "side": side, "kind": "sub",
                                              "player_id": sub["frf_id"], "player_out_id": starters[10 - k]["frf_id"]})
            save_match_details(m, details)

        ours = Team.objects.get(frf_id=settings.OUR_TEAM_FRF_ID)
        Player.objects.filter(team=ours).update(registered=True)
        positions = ["Portar"] * 2 + ["Fundaș"] * 6 + ["Mijlocaș"] * 6 + ["Atacant"] * 4
        for i, p in enumerate(Player.objects.filter(team=ours).order_by("frf_id")):
            p.number, p.position = i + 1, positions[i % len(positions)]
            p.save()
        SyncRun.objects.create(ok=True, summary="demo").__class__.objects.update(finished_at=datetime.now().astimezone())
        self.stdout.write(self.style.SUCCESS(f"Ligă demo: {Match.objects.count()} meciuri, {Player.objects.count()} jucători."))
