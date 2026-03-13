from django.db.models import F
from django.views.generic import TemplateView

from linuxfr.models import Page, Profile, SitemapEntry


class IndexView(TemplateView):
    template_name = "linuxfr/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sitemap_entries_count"] = SitemapEntry.objects.count()
        context["pages_count"] = Page.objects.count()
        context["missing_pages_count"] = SitemapEntry.objects.filter(
            page__isnull=True
        ).count()
        context["out_of_date_pages_count"] = Page.objects.filter(
            fetched_at__lt=F("sitemap_entry__last_modified")
        ).count()
        context["profiles_count"] = Profile.objects.count()

        return context
