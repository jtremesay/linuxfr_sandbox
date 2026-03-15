from itertools import batched

from django.core.management.base import BaseCommand
from django.db.models import F, Q
from tqdm import tqdm

from linuxfr.ai import EMBEDDER
from linuxfr.models import ContentNode, ContentNodeEmbedding


class Command(BaseCommand):
    help = "Update embeddings for all content nodes that don't have one yet"

    def handle(self, *args, **options):
        for content_node in batched(
            tqdm(
                ContentNode.objects.filter(
                    Q(embedding__isnull=True)
                    | Q(embedding__updated_at__lt=F("updated_at"))
                )
            ),
            100,
        ):
            r = EMBEDDER.embed_query_sync([cn.content for cn in content_node])
            for cn, embedding in zip(content_node, r.embeddings):
                ContentNodeEmbedding.objects.update_or_create(
                    content_node=cn, defaults={"vector": embedding}
                )
