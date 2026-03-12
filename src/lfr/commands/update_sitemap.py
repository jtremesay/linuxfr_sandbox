import gzip
from io import BytesIO
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import polars as pl
from httpx import Client

from lfr.client import get_client
from lfr.models import Kind, UnknownKindError


def fetch_gzipped_xml(client: Client, url: str) -> ET.Element:
    response = client.get(url)
    response.raise_for_status()
    with gzip.GzipFile(fileobj=BytesIO(response.content)) as f:
        return ET.parse(f).getroot()


def main():
    with get_client() as client:
        index_root = fetch_gzipped_xml(client, "/sitemap_index.xml.gz")
        pages = []

        for sitemap_node in index_root.findall(
            "{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap"
        ):
            loc = sitemap_node.find(
                "{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
            ).text
            sitemap_root = fetch_gzipped_xml(client, loc)
            for url_node in sitemap_root.findall(
                "{http://www.sitemaps.org/schemas/sitemap/0.9}url"
            ):
                url = urlparse(
                    url_node.find(
                        "{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
                    ).text
                ).path
                try:
                    kind = Kind.from_url(url)
                except UnknownKindError:
                    continue
                lastmod = url_node.find(
                    "{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod"
                ).text

                pages.append({"url": url, "lastmod": lastmod, "kind": kind})

        df_sitemap = pl.DataFrame(pages)
        df_sitemap.write_csv("sitemap.csv")
