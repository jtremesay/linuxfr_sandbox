import gzip
from datetime import datetime
from io import BytesIO
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import polars as pl
from httpx import Client

from lfr.client import get_client
from lfr.models import Kind, SitemapEntry, UnknownKindError

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def fetch_gzipped_xml(client: Client, url: str) -> ET.Element:
    response = client.get(url)
    response.raise_for_status()
    with gzip.GzipFile(fileobj=BytesIO(response.content)) as f:
        return ET.parse(f).getroot()


def parse_sitemap(client: Client, loc: str) -> list[SitemapEntry]:
    sitemap_root = fetch_gzipped_xml(client, loc)
    results = []
    for url_node in sitemap_root.findall(f"{NS}url"):
        url = urlparse(url_node.find(f"{NS}loc").text).path
        try:
            kind = Kind.from_url(url)
        except UnknownKindError:
            continue
        lastmod = datetime.fromisoformat(url_node.find(f"{NS}lastmod").text)
        results.append(SitemapEntry(url, lastmod, kind))
    return results


def main():
    with get_client() as client:
        index_root = fetch_gzipped_xml(client, "/sitemap_index.xml.gz")
        locs = [
            node.find(f"{NS}loc").text for node in index_root.findall(f"{NS}sitemap")
        ]

        pages = []
        for loc in locs:
            pages.extend(parse_sitemap(client, loc))

    pl.DataFrame(pages).write_csv("sitemap.csv")
