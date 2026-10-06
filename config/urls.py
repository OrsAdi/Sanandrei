from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.views import contact, home, news_detail, news_list
from teams import views as teams_views

admin.site.site_header = "CS Sânandrei Timiș – Administrare"
admin.site.site_title = "CS Sânandrei Admin"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("contact/", contact, name="contact"),
    path("stiri/", news_list, name="news_list"),
    path("stiri/<slug:slug>/", news_detail, name="news_detail"),
    path("lot/", teams_views.squad_list, name="squad_list"),
    path("jucator/<int:pk>/", teams_views.player_detail, name="player_detail"),
    path("meciuri/", teams_views.fixtures, name="fixtures"),
    path("meci/<int:pk>/", teams_views.match_detail, name="match_detail"),
    path("clasament/", teams_views.standings, name="standings"),
    path("statistici/", teams_views.stats_list, name="stats"),
    path("echipe/", teams_views.team_list, name="team_list"),
    path("echipe/<slug:slug>/", teams_views.team_detail, name="team_detail"),
    path("cauta/", teams_views.search, name="search"),
    path("magazin/", include("shop.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
