import logging
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from celery import shared_task
from django.db.transaction import atomic

from linuxfr.client import LinuxFrClient
from linuxfr.models import Page, Profile, SitemapEntry

logger = logging.getLogger(__name__)


@shared_task
def fetch_page(sitemap_entry_id: int):
    sitemap_entry = SitemapEntry.objects.get(id=sitemap_entry_id)
    with LinuxFrClient() as client:
        Page.objects.update_or_create(
            sitemap_entry=sitemap_entry,
            defaults={
                "content": client.get_page(sitemap_entry.location),
                "fetched_at": datetime.now(timezone.utc),
            },
        )


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
            for entry_data in remote_sitemap_entries_data:
                entry, _ = SitemapEntry.objects.update_or_create(
                    location=entry_data.location,
                    defaults={
                        "kind": entry_data.kind,
                        "last_modified": entry_data.last_modified,
                        "change_frequency": entry_data.change_frequency,
                        "priority": entry_data.priority,
                    },
                )

                try:
                    page = entry.page
                except SitemapEntry.page.RelatedObjectDoesNotExist:
                    page = None

                if page is None or page.fetched_at < entry.last_modified:
                    fetch_page.delay(entry.id)


@shared_task
def import_page_from_file(html_file_path: str, base_dir: str):
    html_file_path = Path(html_file_path)
    base_dir = Path(base_dir)

    location = "/" + html_file_path.relative_to(base_dir).with_suffix("").as_posix()
    file_mod_time = datetime.fromtimestamp(
        html_file_path.stat().st_mtime, tz=timezone.utc
    )

    entry = SitemapEntry.objects.get(location=location)
    Page.objects.update_or_create(
        sitemap_entry=entry,
        defaults={
            "content": html_file_path.read_bytes(),
            "fetched_at": file_mod_time,
        },
    )


@shared_task
def import_pages_from_dir(html_dir: str):
    html_dir = Path(html_dir)

    if not html_dir.is_dir():
        logger.error("Error: %s is not a valid directory", html_dir)
        return

    for file_entry in html_dir.glob("**/*.html"):
        location = "/" + file_entry.relative_to(html_dir).with_suffix("").as_posix()
        try:
            entry = SitemapEntry.objects.select_related("page").get(location=location)
        except SitemapEntry.DoesNotExist:
            logger.warning("No sitemap entry found for location %s, skipping", location)
            continue

        try:
            page = entry.page
        except SitemapEntry.page.RelatedObjectDoesNotExist:
            page = None

        file_mod_time = datetime.fromtimestamp(
            file_entry.stat().st_mtime, tz=timezone.utc
        )

        if page is not None and page.fetched_at >= file_mod_time:
            logger.info(
                "Page for location %s is up to date, skipping import",
                location,
            )
            continue

        import_page_from_file.delay(str(file_entry), str(html_dir))


@shared_task
def import_profiles_from_page(page_id: int):
    page = Page.objects.get(id=page_id)
    soup = BeautifulSoup(page.content, "lxml")

    profiles = {}
    for profile_link in soup.select("a[rel='author']"):
        user_name = profile_link["href"].split("/")[-1]
        display_name = profile_link.text.strip()
        profiles[user_name] = display_name

    for user_name, display_name in profiles.items():
        Profile.objects.update_or_create(
            user_name=user_name,
            defaults={"display_name": display_name},
        )


@shared_task
def import_profiles_from_all_pages():
    page_ids = Page.objects.values_list("id", flat=True)
    for page_id in page_ids:
        import_profiles_from_page.delay(page_id)
