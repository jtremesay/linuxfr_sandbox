from pathlib import Path

from django.core.management.base import BaseCommand

from linuxfr.tasks import import_pages_from_dir


class Command(BaseCommand):
    help = "Import pages from HTML directory"

    def add_arguments(self, parser):
        parser.add_argument(
            "-d",
            "--html-dir",
            type=Path,
            default=Path("html"),
            help="Path to the directory containing HTML files to import",
        )

    def handle(self, *args, html_dir: Path, **options):
        import_pages_from_dir.delay(str(html_dir))
