from django.core.management.base import BaseCommand

from linuxfr.tasks import import_content_nodes_from_all_pages


class Command(BaseCommand):
    help = "Import content from pages"

    def handle(self, *args, **options):
        import_content_nodes_from_all_pages.delay()
