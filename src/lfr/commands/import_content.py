from pathlib import Path

import polars as pl
from bs4 import BeautifulSoup, ResultSet, Tag
from tqdm import tqdm

from lfr.models import Content
from lfr.settings import BASE_URL, HTML_DIR
from lfr.utils import path_to_url


def extract_comment(comment_tag: Tag, parent_url: str) -> Content:
    link_title = comment_tag.select_one("h2 a.title")
    return Content(
        url=link_title["href"],
        parent_url=parent_url,
        user_name=comment_tag.select_one("a[rel='author']")["href"].split("/")[-1],
        title=link_title.text.strip(),
        body=comment_tag.select_one(".content").text.strip(),
        score=int(comment_tag.select_one(".score").text.strip().split()[0]),
    )


def import_comment(comment_tag: Tag, parent_url: str) -> list[Content]:
    comment = extract_comment(comment_tag, parent_url)
    return [comment] + import_comments(
        comment_tag.select(":scope > ul > .comment"), comment.url
    )


def import_comments(comments_tags: ResultSet, parent_url: str) -> list[Content]:
    comments = []
    for comment_tag in comments_tags:
        comments += import_comment(comment_tag, parent_url)

    return comments


def extract_article_content(url: str, article: Tag) -> Content:
    if node := article.select_one("a[rel='author']"):
        user_name = node["href"].split("/")[-1]
    else:
        user_name = None
    title = article.select_one("h1").text.strip()
    content = article.select_one(".content").text.strip()
    score = int(article.select_one(".score").text.strip())

    return Content(url=url, user_name=user_name, title=title, body=content, score=score)


def import_content(path: Path) -> pl.DataFrame:
    url = path_to_url(path)
    tqdm.write(f"Importing content from {path} {BASE_URL + url}")

    parquet_file = path.with_suffix(".parquet")
    if parquet_file.exists() and parquet_file.stat().st_mtime > path.stat().st_mtime:
        tqdm.write(f"Skipping {path} as {parquet_file} is up to date")
        return pl.read_parquet(parquet_file)

    soup = BeautifulSoup(path.read_text(), "lxml").select_one("#container")
    content = extract_article_content(url, soup.select_one("article"))
    threads_node = soup.select_one(".threads")
    if threads_node is None:
        comments = []
    else:
        comments = import_comments(
            threads_node.select(":scope > .comment"), content.url
        )

    df = pl.DataFrame([content] + comments)
    df.write_parquet(parquet_file)

    return df


def main():
    pl.concat(
        import_content(path) for path in tqdm(list(Path(HTML_DIR).rglob("**/*.html")))
    ).write_parquet("linuxfr_content.parquet")
