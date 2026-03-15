from django.conf import settings
from pydantic_ai import Embedder

EMBEDDER = Embedder(model=settings.EMBEDDING_MODEL)
