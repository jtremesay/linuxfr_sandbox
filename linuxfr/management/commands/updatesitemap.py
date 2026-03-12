import logging

from django.core.management.base import BaseCommand
from hishel.httpx import SyncCacheClient as Client
from tqdm import tqdm

from linuxfr.crawler import get_pages_from_sitemaps
from linuxfr.models import Page

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Refresh list of known pages from sitemap"

    def handle(self, *args, **options):
        with Client() as client:
            pages = get_pages_from_sitemaps(client)

        logger.info("Fetched %d pages from sitemap", len(pages))
        old_pages = set(Page.objects.values_list("url", flat=True))
        new_pages = {page.url for page in pages}
        to_remove = old_pages - new_pages
        for url in tqdm(to_remove, desc="Removing old pages"):
            tqdm.write(f"Removing page with url: {url}")
            Page.objects.filter(url=url).delete()

        for page in tqdm(pages, desc="Processing pages"):
            tqdm.write(f"Processing page: {page.url}")
            page = Page.objects.update_or_create(
                url=page.url,
                defaults={
                    "last_modified": page.last_modified,
                    "kind": page.kind,
                },
            )
