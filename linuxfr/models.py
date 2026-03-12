import re

from bs4 import BeautifulSoup
from django.db import models


class UnknownKindError(Exception):
    pass


class Kind(models.TextChoices):
    NEWS = "news", "News"
    DIARY = "diary", "Diary"
    LINK = "link", "Link"
    FORUM_POST = "forum_post", "Forum Post"
    POLL = "poll", "Poll"
    TICKET = "ticket", "Ticket"

    @classmethod
    def from_url(cls, url: str) -> "Kind":
        for kind, pattern in KIND_RE_MAP.items():
            if pattern.match(url):
                return kind

        raise UnknownKindError(f"Unknown kind for URL: {url}")


NEWS_PATTERN = r"^https://linuxfr.org/news/.*$"
NEWS_RE = re.compile(NEWS_PATTERN)

DIARY_PATTERN = r"^https://linuxfr.org/users/[^/]+/journaux/.*$"
DIARY_RE = re.compile(DIARY_PATTERN)

LINK_PATTERN = r"^https://linuxfr.org/users/[^/]+/liens/.*$"
LINK_RE = re.compile(LINK_PATTERN)

FORUM_POST_PATTERN = r"^https://linuxfr.org/forums/[^/]+/posts/.*$"
FORUM_POST_RE = re.compile(FORUM_POST_PATTERN)

POLL_PATTERN = r"^https://linuxfr.org/sondages/.*$"
POLL_RE = re.compile(POLL_PATTERN)

TICKET_PATTERN = r"^https://linuxfr.org/suivi/.*$"
TICKET_RE = re.compile(TICKET_PATTERN)


KIND_RE_MAP = {
    Kind.NEWS: NEWS_RE,
    Kind.DIARY: DIARY_RE,
    Kind.LINK: LINK_RE,
    Kind.FORUM_POST: FORUM_POST_RE,
    Kind.POLL: POLL_RE,
    Kind.TICKET: TICKET_RE,
}


class Page(models.Model):
    url = models.URLField(unique=True)
    last_modified = models.DateTimeField()  # From sitemap lastmod
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
    )

    def __str__(self) -> str:
        return self.url


class PageContent(models.Model):
    page = models.OneToOneField(
        Page,
        on_delete=models.CASCADE,
        related_name="content",
        related_query_name="content",
        unique=True,
    )
    html = models.TextField()
    fetched_at = models.DateTimeField(auto_now_add=True)

    @property
    def soup(self) -> BeautifulSoup:
        return BeautifulSoup(self.html, "lxml")

    def __str__(self) -> str:
        return f"Content for {self.page.url} fetched at {self.fetched_at}"
