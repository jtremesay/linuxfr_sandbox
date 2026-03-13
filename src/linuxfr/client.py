from collections.abc import Generator
from gzip import GzipFile
from io import BytesIO
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

from django.conf import settings
from hishel.httpx import SyncCacheClient as Client

from linuxfr.models import Kind
from linuxfr.schemas import SitemapEntry

SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def xml_from_gzip(content: bytes) -> ET.Element:
    with GzipFile(fileobj=BytesIO(content)) as f:
        return ET.parse(f).getroot()


class LinuxFrClient(Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, base_url=settings.LINUXFR_BASE_URL, **kwargs)

    def get_sitemap_index(self) -> Generator[str, None, None]:
        sitemap_index = self.get_sitemap(settings.LINUXFR_SITEMAP_INDEX_URL)
        for node in sitemap_index.findall(f"{SITEMAP_NS}sitemap"):
            yield node.find(f"{SITEMAP_NS}loc").text

    def get_sitemap(self, url: str) -> ET.Element:
        response = self.get(url)
        response.raise_for_status()

        return xml_from_gzip(response.content)

    def get_sitemap_entries(self) -> Generator[SitemapEntry, None, None]:
        sitemap_index = self.get_sitemap_index()
        for sitemap_url in sitemap_index:
            sitemap = self.get_sitemap(sitemap_url)
            for node in sitemap.findall(f"{SITEMAP_NS}url"):
                location = node.find(f"{SITEMAP_NS}loc").text
                if not location.startswith(settings.LINUXFR_BASE_URL):
                    continue

                location = urlparse(location).path
                kind = Kind.from_url(location)
                if kind == Kind.UNKNOWN:
                    continue

                yield SitemapEntry(
                    location=location,
                    kind=kind,
                    last_modified=node.find(f"{SITEMAP_NS}lastmod").text,
                    change_frequency=node.find(f"{SITEMAP_NS}changefreq").text,
                    priority=float(node.find(f"{SITEMAP_NS}priority").text),
                )
