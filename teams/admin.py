from django.conf import settings
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path

from .models import Appearance, Match, MatchEvent, Player, SyncRun, Team
from .sync import run_sync


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "frf_id", "venue", "points_adjustment"]
    list_editable = ["venue", "points_adjustment"]
    search_fields = ["name"]
    readonly_fields = ["frf_id", "frf_url", "logo_url"]


class OurPlayersFilter(admin.SimpleListFilter):
    title = "echipă"
    parameter_name = "ai_nostri"

    def lookups(self, request, model_admin):
        return [("1", settings.CLUB_NAME)]

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(team__frf_id=settings.OUR_TEAM_FRF_ID)
        return queryset


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ["name", "team", "number", "position", "birth_date", "registered"]
    list_editable = ["number", "position"]
    list_filter = [OurPlayersFilter, "position", "registered", "team"]
    search_fields = ["name", "card_number"]
    readonly_fields = ["frf_id", "photo_url"]
    list_select_related = ["team"]
    fieldsets = [
        ("Editabile", {"fields": ["number", "position", "bio", "image"]}),
        ("Importate de pe FRF", {"fields": ["name", "team", "birth_date", "card_number", "registered", "frf_id", "photo_url"]}),
    ]


class AppearanceInline(admin.TabularInline):
    model = Appearance
    extra = 0
    autocomplete_fields = ["player"]


class EventInline(admin.TabularInline):
    model = MatchEvent
    extra = 0
    autocomplete_fields = ["player", "player_out"]
    fk_name = "match"


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ["round", "date", "home", "score", "away", "is_finished", "details_synced"]
    list_display_links = ["round", "date"]
    list_filter = ["round", "is_finished", "details_synced"]
    search_fields = ["home__name", "away__name"]
    list_select_related = ["home", "away"]
    inlines = [EventInline, AppearanceInline]


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = ["started_at", "finished_at", "ok"]
    readonly_fields = ["started_at", "finished_at", "ok", "summary"]
    change_list_template = "admin/teams/syncrun/change_list.html"

    def has_add_permission(self, request):
        return False

    def get_urls(self):
        return [path("sync-now/", self.admin_site.admin_view(self.sync_now), name="teams_sync_now")] + super().get_urls()

    def sync_now(self, request):
        if request.method != "POST":
            return redirect("admin:teams_syncrun_changelist")
        try:
            run = run_sync(full=request.POST.get("full") == "1")
            messages.success(request, "Sincronizare reușită.\n" + run.summary)
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"Sincronizarea a eșuat: {exc}")
        return redirect("admin:teams_syncrun_changelist")
