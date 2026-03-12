import logging
from datetime import datetime

import polars as pl
from tqdm import tqdm

from lfr.client import get_client
from lfr.settings import HTML_DIR

logger = logging.getLogger(__name__)


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
    html_files = pl.Series(HTML_DIR.glob("**/*.html"))
    html_df = pl.DataFrame(
        {
            "path": html_files,
            "url": [
                "/" + str(f.relative_to(HTML_DIR).parent / f.stem) for f in html_files
            ],
            "lastmod": [datetime.fromtimestamp(f.stat().st_mtime) for f in html_files],
        }
    )
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
    pages_to_update = sitemap_df.join(html_df, on="url", how="left").filter(
        (pl.col("lastmod") > pl.col("lastmod_right"))
        | pl.col("lastmod_right").is_null()
    )["url"]

    logger.info("Found %d pages to update", len(pages_to_update))

    with get_client() as client:
        for url in tqdm(pages_to_update, desc="Updating pages"):
            tqdm.write(f"Updating page: {url}")

            try:
                r = client.get(url)
                r.raise_for_status()
            except Exception as e:
                logger.error(f"Failed to fetch page {url}", exc_info=e)
                continue

            path = HTML_DIR / (url[1:] + ".html")
            try:
                with path.open("w", encoding="utf-8") as f:
                    f.write(r.text)
            except Exception as e:
                logger.error(f"Failed to write page {url}", exc_info=e)

                # Remove the file if it was partially written
                path.unlink(missing_ok=True)
