from django.core.management.base import BaseCommand

from linuxfr.tasks import import_profiles_from_all_pages


class Command(BaseCommand):
    help = "Import profiles from all pages"

    def handle(self, *args, **options):
        import_profiles_from_all_pages.delay()
