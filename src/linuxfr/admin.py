from django.contrib import admin

# Register your models here.
from .models import SitemapEntry


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
    list_filter = ("kind", "last_modified")
    search_fields = ("location",)
