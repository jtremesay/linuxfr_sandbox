from celery import shared_task
from django.db.transaction import atomic
from tqdm import tqdm

from linuxfr.client import LinuxFrClient
from linuxfr.models import SitemapEntry


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
                SitemapEntry.objects.update_or_create(
                    location=entry_data.location,
                    defaults={
                        "kind": entry_data.kind,
                        "last_modified": entry_data.last_modified,
                        "change_frequency": entry_data.change_frequency,
                        "priority": entry_data.priority,
                    },
                )
