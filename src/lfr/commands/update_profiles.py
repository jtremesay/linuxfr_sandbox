import logging
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import polars as pl
from bs4 import BeautifulSoup
from tqdm import tqdm

from lfr.settings import HTML_DIR

logger = logging.getLogger(__name__)


def extract_profiles(path: Path) -> list[tuple[str, str]]:
    soup = BeautifulSoup(path.read_text(), "lxml")
    seen = set()
    results = []
    for profile in soup.select("a[rel='author']"):
        user_name = profile["href"].split("/")[-1]
        if user_name not in seen:
            seen.add(user_name)
            results.append((user_name, profile.text.strip()))
    return results


def main():
    logging.basicConfig(level=logging.WARNING)

    pages = list(HTML_DIR.glob("**/*.html"))

    all_profiles: list[tuple[str, str]] = []
    with ProcessPoolExecutor() as executor:
        for profiles in tqdm(
            executor.map(extract_profiles, pages),
            total=len(pages),
            desc="Extracting profiles from HTML files",
        ):
            all_profiles.extend(profiles)

    if all_profiles:
        user_names, display_names = zip(*all_profiles)
    else:
        user_names, display_names = [], []

    pl.DataFrame(
        {
            "user_name": list(user_names),
            "display_name": list(display_names),
        }
    ).unique(subset=["user_name"]).sort("user_name").write_csv("profiles.csv")
