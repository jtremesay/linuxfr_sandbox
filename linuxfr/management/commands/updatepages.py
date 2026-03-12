import datetime
import logging

from django.core.management.base import BaseCommand
from django.db.models import F, Q
from hishel.httpx import SyncCacheClient as Client
from tqdm import tqdm

from linuxfr.models import Page, PageContent

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Downloads and stores the HTML content of pages that are new or have been modified since the last fetch."

    def handle(self, *args, **options):
        with Client() as client:
            pages_to_fetch = Page.objects.filter(
                Q(content__isnull=True) | Q(last_modified__gt=F("content__fetched_at"))
            ).order_by("url")
            for page in tqdm(pages_to_fetch, desc="Fetching pages"):
                tqdm.write(f"Fetching page: {page.url}")
                try:
                    response = client.get(page.url)
                    response.raise_for_status()
                except Exception as e:
                    logger.error(f"Failed to fetch {page.url}: {e}")
                    continue

                PageContent.objects.update_or_create(
                    page=page,
                    defaults={
                        "html": response.text,
                        "fetched_at": datetime.datetime.now(tz=datetime.timezone.utc),
                    },
                )
