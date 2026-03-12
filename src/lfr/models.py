import re

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
