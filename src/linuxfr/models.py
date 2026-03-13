import re
from typing import Self

from django.db import models


class UnknownKindError(TypeError):
    pass


# Create your models here.
class Kind(models.TextChoices):
    UNKNOWN = "unknown"
    NEWS = "news"
    DIARY = "diary"
    LINK = "link"
    FORUM_POST = "forum_post"
    POLL = "poll"
    TICKET = "ticket"
    COMMENT = "comment"

    @classmethod
    def from_url(cls, url: str) -> Self:
        for kind, pattern in KIND_RE_MAP.items():
            if pattern.match(url):
                return kind

        return cls.UNKNOWN


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

COMMENT_PATTERN = r"^/nodes/\d+/comments/\d+$"
COMMENT_RE = re.compile(COMMENT_PATTERN)

KIND_RE_MAP = {
    Kind.NEWS: NEWS_RE,
    Kind.DIARY: DIARY_RE,
    Kind.LINK: LINK_RE,
    Kind.FORUM_POST: FORUM_POST_RE,
    Kind.POLL: POLL_RE,
    Kind.TICKET: TICKET_RE,
    Kind.COMMENT: COMMENT_RE,
}


class ChangeFrequency(models.TextChoices):
    ALWAYS = "always"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    NEVER = "never"


class SitemapEntry(models.Model):
    location = models.URLField(unique=True)
    last_modified = models.DateTimeField()  # from sitemap
    change_frequency = models.CharField(max_length=20, choices=ChangeFrequency.choices)
    priority = models.FloatField()
    kind = models.CharField(max_length=20, choices=Kind.choices)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
