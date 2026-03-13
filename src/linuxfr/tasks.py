import logging
from datetime import datetime, timezone

from celery import shared_task
from django.db.transaction import atomic
from tqdm import tqdm

from linuxfr.client import LinuxFrClient
from linuxfr.models import Page, SitemapEntry

logger = logging.getLogger(__name__)


@shared_task
def fetch_sitemap():
    with LinuxFrClient() as client:
        remote_sitemap_entries_data = list(client.get_sitemap_entries())

        remote_locations = {entry.location for entry in remote_sitemap_entries_data}
        local_locations = set(SitemapEntry.objects.values_list("location", flat=True))

        with atomic():
            # Delete local entries that are not in the remote sitemap
            SitemapEntry.objects.filter(
                location__in=local_locations - remote_locations
            ).delete()

            # Update or create entries from the remote sitemap
            for entry_data in tqdm(
                remote_sitemap_entries_data, desc="Updating sitemap entries"
            ):
                sm_entry, _ = SitemapEntry.objects.update_or_create(
                    location=entry_data.location,
                    defaults={
                        "kind": entry_data.kind,
                        "last_modified": entry_data.last_modified,
                        "change_frequency": entry_data.change_frequency,
                        "priority": entry_data.priority,
                    },
                )
                fetch_page.delay(sm_entry.id)


@shared_task
def fetch_page(sitemap_entry_id: int, force: bool = False):
    sitemap_entry = SitemapEntry.objects.select_related("page").get(id=sitemap_entry_id)
    try:
        page = sitemap_entry.page
    except SitemapEntry.page.RelatedObjectDoesNotExist:
        page = None

    if page and not force and page.fetched_at > sitemap_entry.updated_at:
        logger.info("Skipping fetch for %s as it is up to date", sitemap_entry.location)
        return

    with LinuxFrClient() as client:
        Page.objects.update_or_create(
            sitemap_entry=sitemap_entry,
            defaults={
                "content": client.get_page(sitemap_entry.location),
                "fetched_at": datetime.now(timezone.utc),
            },
        )
