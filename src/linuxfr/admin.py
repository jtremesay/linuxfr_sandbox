from django.contrib import admin

# Register your models here.
from .models import ContentNode, Page, Profile, SitemapEntry


@admin.register(SitemapEntry)
class SitemapEntryAdmin(admin.ModelAdmin):
    list_display = (
        "location",
        "kind",
        "last_modified",
        "change_frequency",
        "priority",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "kind",
        "last_modified",
        "change_frequency",
        "created_at",
        "updated_at",
    )
    search_fields = ("location",)


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("sitemap_entry", "fetched_at", "created_at", "updated_at")
    list_filter = ("sitemap_entry__kind", "fetched_at", "created_at", "updated_at")
    search_fields = ("sitemap_entry__location",)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user_name", "display_name")
    search_fields = ("user_name", "display_name")


@admin.register(ContentNode)
class ContentNodeAdmin(admin.ModelAdmin):
    list_display = (
        "url",
        "page",
        "parent",
        "kind",
        "title",
        "author",
        "score",
        "created_at",
        "updated_at",
    )
    list_filter = ("kind", "created_at", "updated_at")
    search_fields = ("url", "title", "content")
