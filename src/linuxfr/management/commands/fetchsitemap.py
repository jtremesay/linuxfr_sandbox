from django.core.management.base import BaseCommand

from linuxfr.tasks import fetch_sitemap


class Command(BaseCommand):
    help = "Fetch the sitemap and store the URLs in the database"

    def handle(self, *args, **options) -> None:
        fetch_sitemap.delay()
