import logging
import os
from datetime import datetime
from pathlib import Path

import polars as pl
from tqdm import tqdm

from lfr.client import get_client
from lfr.settings import HTML_DIR
from lfr.utils import path_to_url, url_to_path

logger = logging.getLogger(__name__)


def update_page(url, client):
    try:
        r = client.get(url)
        r.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch page {url}", exc_info=e)
        return

    path = url_to_path(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("wb") as f:
            f.write(r.content)
    except Exception as e:
        logger.error(f"Failed to write page {url}", exc_info=e)

        # Remove the file if it was partially written
        path.unlink(missing_ok=True)

    return url


def scan_html_dir(html_dir: Path) -> pl.DataFrame:
    """Single-pass scan: collect path, url, and mtime together."""
    paths, urls, lastmods = [], [], []
    for dirpath, _, filenames in os.walk(html_dir):
        for fname in filenames:
            if not fname.endswith(".html"):
                continue
            p = Path(dirpath) / fname
            paths.append(p)
            urls.append(path_to_url(p))
            lastmods.append(datetime.fromtimestamp(p.stat().st_mtime))
    return pl.DataFrame({"path": paths, "url": urls, "lastmod": lastmods})


def main():
    logging.basicConfig(level=logging.WARNING)

    HTML_DIR.mkdir(exist_ok=True)

    logger.info("Reading sitemap.csv")
    sitemap_df = pl.read_csv(
        "sitemap.csv", schema={"url": pl.Utf8, "lastmod": pl.Datetime, "kind": pl.Utf8}
    )
    logger.info("Found %d pages in sitemap.csv", len(sitemap_df))

    # Search for pages in the HTML directory, and their change dates
    logger.info("Scanning HTML directory for existing pages")
    html_df = scan_html_dir(HTML_DIR)
    logger.info("Found %d HTML files in the directory", len(html_df))

    # Search for pages to delete: pages that are in the HTML directory but not in the sitemap
    if not html_df.is_empty():
        obsolete_pages = html_df.filter(~html_df["url"].is_in(sitemap_df["url"]))

        logger.info("Found %d obsolete pages to delete", len(obsolete_pages))
        if not obsolete_pages.is_empty():
            for path in tqdm(obsolete_pages["path"], desc="Deleting obsolete pages"):
                tqdm.write(f"Deleting obsolete page: {path}")
                path.unlink(missing_ok=True)

        # Remove obsolete pages from the HTML dataframe
        html_df = html_df.filter(html_df["url"].is_in(sitemap_df["url"]))

    # Search for pages to update: pages that are in the sitemap, and either not in the HTML directory, or have a more recent lastmod date in the sitemap
    pages_to_update = (
        sitemap_df.join(html_df, on="url", how="left")
        .filter(
            (pl.col("lastmod") > pl.col("lastmod_right"))
            | pl.col("lastmod_right").is_null()
        )
        .sort("lastmod")["url"]
    )
    logger.info("Found %d pages to update", len(pages_to_update))

    with get_client() as client:
        for url in tqdm(pages_to_update, desc="Updating pages"):
            tqdm.write(f"Updating page: {url}")
            update_page(url, client)
