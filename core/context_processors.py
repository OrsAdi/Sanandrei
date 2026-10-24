from django.conf import settings

from teams.models import SyncRun

from . import content


def club(request):
    last_sync = SyncRun.objects.filter(ok=True).only("finished_at").first()
    cfg = content.site_settings()
    return {
        "SOCIAL_LINKS": content.social_links(cfg),
        "CLUB_NAME": settings.CLUB_NAME,
        "CLUB_SHORT_NAME": settings.CLUB_SHORT_NAME,
        **cfg,
        "WEB3FORMS_KEY": settings.WEB3FORMS_KEY,
        "COMPETITION_NAME": settings.COMPETITION_NAME,
        "SEASON": settings.SEASON,
        "FRF_TEAM_URL": settings.FRF_TEAM_URL,
        "FRF_COMPETITION_URL": settings.FRF_COMPETITION_URL,
        "OUR_TEAM_FRF_ID": settings.OUR_TEAM_FRF_ID,
        "last_sync": last_sync.finished_at if last_sync else None,
    }
