from django.contrib import admin

from .models import ContactMessage, News, Sponsor


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ["title", "published_at", "is_published"]
    list_filter = ["is_published"]
    prepopulated_fields = {"slug": ["title"]}
    search_fields = ["title", "body"]


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ["subject", "name", "email", "created_at", "is_read"]
    list_filter = ["is_read"]
    list_editable = ["is_read"]
    readonly_fields = ["name", "email", "phone", "subject", "message", "created_at"]


@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = ["name", "website", "order"]
    list_editable = ["order"]
