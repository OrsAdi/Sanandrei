from django.conf import settings

from teams.models import SyncRun


def club(request):
    last_sync = SyncRun.objects.filter(ok=True).only("finished_at").first()
    return {
        "CLUB_NAME": settings.CLUB_NAME,
        "CLUB_SHORT_NAME": settings.CLUB_SHORT_NAME,
        "CLUB_EMAIL": settings.CLUB_EMAIL,
        "CLUB_PHONE": settings.CLUB_PHONE,
        "CLUB_VENUE": settings.CLUB_VENUE,
        "COMPETITION_NAME": settings.COMPETITION_NAME,
        "SEASON": settings.SEASON,
        "FRF_TEAM_URL": settings.FRF_TEAM_URL,
        "FRF_COMPETITION_URL": settings.FRF_COMPETITION_URL,
        "OUR_TEAM_FRF_ID": settings.OUR_TEAM_FRF_ID,
        "last_sync": last_sync.finished_at if last_sync else None,
    }
