from django.core.management.base import BaseCommand

from teams.sync import run_sync


class Command(BaseCommand):
    help = "Importă meciurile, rezultatele, echipele de start și evenimentele din Liga a IV-a Timiș (frf-ajf.ro)."

    def add_arguments(self, parser):
        parser.add_argument("--full", action="store_true",
                            help="Reimportă detaliile tuturor meciurilor terminate, nu doar pe cele noi.")
        parser.add_argument("--workers", type=int, default=8, help="Câte pagini se descarcă în paralel.")
        parser.add_argument("--no-roster", action="store_true", help="Nu actualiza lotul oficial al clubului.")

    def handle(self, *args, **options):
        run = run_sync(
            full=options["full"],
            workers=options["workers"],
            log=self.stdout.write,
            with_roster=not options["no_roster"],
        )
        self.stdout.write(self.style.SUCCESS(f"Gata în {(run.finished_at - run.started_at).seconds}s."))
