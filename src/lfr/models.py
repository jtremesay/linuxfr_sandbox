import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Optional


class UnknownKindError(Exception):
    pass


class Kind(StrEnum):
    NEWS = "news"
    DIARY = "diary"
    LINK = "link"
    FORUM_POST = "forum_post"
    POLL = "poll"
    TICKET = "ticket"

    @classmethod
    def from_url(cls, url: str) -> "Kind":
        for kind, pattern in KIND_RE_MAP.items():
            if pattern.match(url):
                return kind

        raise UnknownKindError(f"Unknown kind for URL: {url}")


NEWS_PATTERN = r"^/news/.*$"
NEWS_RE = re.compile(NEWS_PATTERN)

DIARY_PATTERN = r"^/users/[^/]+/journaux/.*$"
DIARY_RE = re.compile(DIARY_PATTERN)

LINK_PATTERN = r"^/users/[^/]+/liens/.*$"
LINK_RE = re.compile(LINK_PATTERN)

FORUM_POST_PATTERN = r"^/forums/[^/]+/posts/.*$"
FORUM_POST_RE = re.compile(FORUM_POST_PATTERN)

POLL_PATTERN = r"^/sondages/.*$"
POLL_RE = re.compile(POLL_PATTERN)

TICKET_PATTERN = r"^/suivi/.*$"
TICKET_RE = re.compile(TICKET_PATTERN)

KIND_RE_MAP = {
    Kind.NEWS: NEWS_RE,
    Kind.DIARY: DIARY_RE,
    Kind.LINK: LINK_RE,
    Kind.FORUM_POST: FORUM_POST_RE,
    Kind.POLL: POLL_RE,
    Kind.TICKET: TICKET_RE,
}


@dataclass
class SitemapEntry:
    url: str
    lastmod: datetime
    kind: Kind


@dataclass
class Content:
    url: str
    title: str
    body: str
    score: int
    user_name: Optional[str] = None
    parent_url: Optional[str] = None
