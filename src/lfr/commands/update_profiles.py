import logging
from pathlib import Path

import polars as pl
from bs4 import BeautifulSoup
from tqdm import tqdm

from lfr.settings import HTML_DIR

logger = logging.getLogger(__name__)


def extract_profiles(path: Path) -> pl.DataFrame:
    soup = BeautifulSoup(path.read_text(), "lxml")

    user_names = []
    display_names = []
    for profile in soup.select("a[rel='author']"):
        user_names.append(profile["href"].split("/")[-1])
        display_names.append(profile.text.strip())

    return pl.DataFrame(
        {
            "user_name": user_names,
            "display_name": display_names,
        }
    ).unique(subset=["user_name"])


def main():
    logging.basicConfig(level=logging.WARNING)

    pages = pl.Series(HTML_DIR.glob("**/*.html"))

    pl.concat(
        profiles_df
        for profiles_df in tqdm(
            (extract_profiles(file) for file in pages),
            total=pages.len(),
            desc="Extracting profiles from HTML files",
        )
    ).unique(subset=["user_name"]).sort("user_name").write_csv("profiles.csv")
