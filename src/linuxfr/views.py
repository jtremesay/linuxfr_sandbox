from django.views.generic import TemplateView

from linuxfr.models import (
    ContentNode,
    ContentNodeEmbedding,
    Page,
    Profile,
    SitemapEntry,
)


class IndexView(TemplateView):
    template_name = "linuxfr/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sitemap_entries_count"] = SitemapEntry.objects.count()
        context["pages_count"] = Page.objects.count()
        context["missing_pages_count"] = (
            context["sitemap_entries_count"] - context["pages_count"]
        )
        context["profiles_count"] = Profile.objects.count()
        context["content_nodes_count"] = ContentNode.objects.count()
        context["embedding_vectors_count"] = ContentNodeEmbedding.objects.count()
        context["content_nodes_without_embedding_vectors_count"] = (
            context["content_nodes_count"] - context["embedding_vectors_count"]
        )
        context["content_nodes_without_embedding_vectors_pct"] = (
            100
            * context["content_nodes_without_embedding_vectors_count"]
            / context["content_nodes_count"]
        )

        return context
