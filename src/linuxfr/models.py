import re
from typing import Self

from django.db import models
from pgvector.django import VectorField


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

    def __str__(self) -> str:
        return self.location


class Page(models.Model):
    sitemap_entry = models.OneToOneField(
        SitemapEntry,
        on_delete=models.CASCADE,
        related_name="page",
        related_query_name="page",
    )
    fetched_at = models.DateTimeField()
    content = models.BinaryField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Page for {self.sitemap_entry.location}"


class Profile(models.Model):
    user_name = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.user_name


class ContentNode(models.Model):
    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name="content_nodes",
        related_query_name="content_nodes",
    )
    url = models.URLField(unique=True)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=255)
    author = models.ForeignKey(
        Profile, on_delete=models.SET_NULL, null=True, blank=True
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        related_query_name="child",
        null=True,
        blank=True,
    )
    score = models.IntegerField()
    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.url


class ContentNodeEmbedding(models.Model):
    content_node = models.OneToOneField(
        ContentNode,
        on_delete=models.CASCADE,
        related_name="embedding",
        related_query_name="embedding",
    )
    vector = VectorField(dimensions=1024)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Embedding for {self.content_node.url}"
