import gzip
import logging
from io import BytesIO
from xml.etree import ElementTree as ET

from hishel.httpx import SyncCacheClient as Client

from .models import Kind, Page, UnknownKindError

logger = logging.getLogger(__name__)


class SkipPage(Exception):
    pass


def fetch_gzipped_xml(client: Client, url: str) -> ET.Element:
    logger.info("Fetching gzipped XML from %s", url)
    response = client.get(url)
    response.raise_for_status()
    with gzip.GzipFile(fileobj=BytesIO(response.content)) as f:
        xml_content = f.read()

    return ET.fromstring(xml_content)


def page_from_node(url_node: ET.Element) -> Page:
    url = url_node.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text
    try:
        kind = Kind.from_url(url)
    except UnknownKindError as e:
        logger.warning("Skipping URL %s: %s", url, e)
        raise SkipPage

    return Page(
        url=url,
        last_modified=url_node.find(
            "{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod"
        ).text,
        kind=kind,
    )


def pages_from_sitemap_node(sitemap_root: ET.Element) -> list[Page]:
    pages = []
    for url_node in sitemap_root.findall(
        "{http://www.sitemaps.org/schemas/sitemap/0.9}url"
    ):
        try:
            page = page_from_node(url_node)
        except SkipPage:
            continue
        pages.append(page)

    return pages


def pages_from_sitemaps_nodes(sitemap_roots: list[ET.Element]) -> list[Page]:
    pages = []
    for sitemap_root in sitemap_roots:
        pages.extend(pages_from_sitemap_node(sitemap_root))

    return pages


def sitemap_urls_from_sitemap_index_node(sitemap_index_root: ET.Element) -> list[str]:
    sitemap_urls = []
    for sitemap_node in sitemap_index_root.findall(
        "{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap"
    ):
        loc = sitemap_node.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text
        sitemap_urls.append(loc)

    return sitemap_urls


def get_pages_from_sitemaps(client: Client) -> list[Page]:
    sitemap_index_root = fetch_gzipped_xml(
        client, "https://linuxfr.org/sitemap_index.xml.gz"
    )
    sitemap_urls = sitemap_urls_from_sitemap_index_node(sitemap_index_root)

    sitemap_roots = []
    for sitemap_url in sitemap_urls:
        sitemap_root = fetch_gzipped_xml(client, sitemap_url)
        sitemap_roots.append(sitemap_root)

    pages = pages_from_sitemaps_nodes(sitemap_roots)
    return pages
