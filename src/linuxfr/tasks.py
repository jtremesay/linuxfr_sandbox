import logging
from datetime import datetime, timezone
from itertools import batched
from pathlib import Path

from bs4 import BeautifulSoup, ResultSet, Tag
from celery import shared_task
from django.db.transaction import atomic

from linuxfr.ai import EMBEDDER
from linuxfr.client import LinuxFrClient
from linuxfr.models import (
    ContentNode,
    ContentNodeEmbedding,
    Kind,
    Page,
    Profile,
    SitemapEntry,
)

logger = logging.getLogger(__name__)


@shared_task
def fetch_sitemap():
    with LinuxFrClient() as client:
        remote_sitemap_entries_data = list(client.get_sitemap_entries())

        remote_locations = {entry.location for entry in remote_sitemap_entries_data}
        local_locations = set(SitemapEntry.objects.values_list("location", flat=True))
        logger.info(
            "Fetched %d entries from remote sitemap, %d entries in local database",
            len(remote_locations),
            len(local_locations),
        )

        locations_to_delete = local_locations - remote_locations
        logger.info(
            "%d entries to delete, %d entries to upsert",
            len(locations_to_delete),
            len(remote_locations - locations_to_delete),
        )

        with atomic():
            # Delete local entries that are not in the remote sitemap
            for ids in batched(locations_to_delete, 10_000):
                SitemapEntry.objects.filter(location__in=ids).delete()

            for entry_data in remote_sitemap_entries_data:
                entry, _ = SitemapEntry.objects.update_or_create(
                    location=entry_data.location,
                    defaults={
                        "last_modified": entry_data.last_modified,
                        "change_frequency": entry_data.change_frequency,
                        "priority": entry_data.priority,
                        "kind": entry_data.kind,
                    },
                )
                fetch_page.delay(entry.id)


@shared_task
def import_page_from_file(html_file_path: str, base_dir: str):
    html_file_path = Path(html_file_path)
    base_dir = Path(base_dir)

    location = "/" + html_file_path.relative_to(base_dir).with_suffix("").as_posix()
    file_mod_time = datetime.fromtimestamp(
        html_file_path.stat().st_mtime, tz=timezone.utc
    )

    entry = SitemapEntry.objects.get(location=location)
    Page.objects.update_or_create(
        sitemap_entry=entry,
        defaults={
            "content": html_file_path.read_bytes(),
            "fetched_at": file_mod_time,
        },
    )


@shared_task
def import_pages_from_dir(html_dir: str):
    html_dir = Path(html_dir)

    if not html_dir.is_dir():
        logger.error("Error: %s is not a valid directory", html_dir)
        return

    for file_entry in html_dir.glob("**/*.html"):
        location = "/" + file_entry.relative_to(html_dir).with_suffix("").as_posix()
        try:
            entry = SitemapEntry.objects.select_related("page").get(location=location)
        except SitemapEntry.DoesNotExist:
            logger.warning("No sitemap entry found for location %s, skipping", location)
            continue

        try:
            page = entry.page
        except SitemapEntry.page.RelatedObjectDoesNotExist:
            page = None

        file_mod_time = datetime.fromtimestamp(
            file_entry.stat().st_mtime, tz=timezone.utc
        )

        if page is not None and page.fetched_at >= file_mod_time:
            logger.info(
                "Page for location %s is up to date, skipping import",
                location,
            )
            continue

        import_page_from_file.delay(str(file_entry), str(html_dir))


@shared_task
def fetch_page(sitemap_entry_id: int):
    sitemap_entry = SitemapEntry.objects.get(id=sitemap_entry_id)
    try:
        page = sitemap_entry.page
    except SitemapEntry.page.RelatedObjectDoesNotExist:
        page = None

    if page is None or page.fetched_at < sitemap_entry.last_modified:
        with LinuxFrClient() as client:
            content = client.get_page(sitemap_entry.location)
            if page is None:
                page = Page.objects.create(
                    sitemap_entry=sitemap_entry,
                    content=content,
                    fetched_at=datetime.now(timezone.utc),
                )
            else:
                page.content = content
                page.fetched_at = datetime.now(timezone.utc)
                page.save(update_fields=["content", "fetched_at"])

    # TODO: create import_content_nodes_from_page task
    import_page.delay(page.id)


@shared_task
def import_page(page_id: int):
    import_profiles_from_page.delay(page_id)
    import_content_nodes_from_page.delay(page_id)


@shared_task
def import_profiles_from_page(page_id: int):
    page = Page.objects.get(id=page_id)
    soup = BeautifulSoup(page.content, "lxml")

    profiles = {}
    for profile_link in soup.select("a[rel='author']"):
        user_name = profile_link["href"].split("/")[-1]
        display_name = profile_link.text.strip()
        profiles[user_name] = display_name

    for user_name, display_name in profiles.items():
        Profile.objects.update_or_create(
            user_name=user_name,
            defaults={"display_name": display_name},
        )


@shared_task
def import_content_nodes_from_page(page_id: int):
    page = Page.objects.get(id=page_id)

    soup = BeautifulSoup(page.content, "lxml")
    root = soup.select_one("#contents")

    article_node = root.select_one("article")
    if node := article_node.select_one("a[rel='author']"):
        user_name = node["href"].split("/")[-1]
        profile = Profile.objects.get(user_name=user_name)
    else:
        profile = None

    title = article_node.select_one("h1").text.strip()
    content = article_node.select_one(".content").text.strip()
    score = int(article_node.select_one(".score").text.strip())

    content_node, _ = ContentNode.objects.update_or_create(
        url=page.sitemap_entry.location,
        defaults={
            "page": page,
            "kind": page.sitemap_entry.kind,
            "title": title,
            "author": profile,
            "parent": None,
            "score": score,
            "content": content,
            "published_at": article_node.select_one("time")["datetime"],
        },
    )
    generate_embedding_for_content_node.delay(content_node.id)

    threads_node = soup.select_one("#comments .threads")
    if threads_node:
        import_comments_from_node_set(
            threads_node.select(":scope > .comment"), parent=content_node
        )


def import_comments_from_node_set(comments_node_set: ResultSet, parent: ContentNode):
    for comment_node in comments_node_set:
        import_comment_from_node(comment_node, parent)


def import_comment_from_node(comment_node: Tag, parent: ContentNode):
    link_title = comment_node.select_one("h2 a.title")
    link_title = comment_node.select_one("h2 a.title")
    content_node, _ = ContentNode.objects.update_or_create(
        url=link_title["href"],
        defaults={
            "page": parent.page,
            "kind": Kind.COMMENT,
            "title": link_title.text.strip(),
            "author": Profile.objects.get(
                user_name=comment_node.select_one("a[rel='author']")["href"].split("/")[
                    -1
                ]
            ),
            "parent": parent,
            "score": int(comment_node.select_one(".score").text.strip().split()[0]),
            "content": comment_node.select_one(".content").text.strip(),
            "published_at": comment_node.select_one("time")["datetime"],
        },
    )
    generate_embedding_for_content_node.delay(content_node.id)

    import_comments_from_node_set(
        comment_node.select(":scope > ul > .comment"), parent=content_node
    )


@shared_task
def generate_embedding_for_content_node(content_node_id: int):
    content_node = ContentNode.objects.get(id=content_node_id)

    try:
        embedding = ContentNodeEmbedding.objects.get(content_node=content_node)
    except ContentNodeEmbedding.DoesNotExist:
        embedding = None

    if embedding is None or embedding.generated_at < content_node.published_at:
        ContentNodeEmbedding.objects.update_or_create(
            content_node=content_node,
            defaults={
                "vector": EMBEDDER.embed_documents_sync([content_node.content])[0],
                "generated_at": datetime.now(timezone.utc),
            },
        )
