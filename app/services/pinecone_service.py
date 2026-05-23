"""
app/services/pinecone_service.py
---------------------------------
Single responsibility: manage the Pinecone index (create, upsert, query).
"""
from pinecone import ServerlessSpec

from app.core.clients import pinecone_client
from app.core.config import settings


def get_index():
    """Return the Pinecone Index, creating it if it does not exist yet."""
    existing = [idx.name for idx in pinecone_client.list_indexes()]
    if settings.pinecone_index_name not in existing:
        pinecone_client.create_index(
            name=settings.pinecone_index_name,
            dimension=settings.embed_dim,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=settings.pinecone_cloud,
                region=settings.pinecone_region,
            ),
        )
    return pinecone_client.Index(settings.pinecone_index_name)


def build_filter(
    filter_type: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict | None:
    """Build a Pinecone metadata filter dict from optional constraints."""
    conds: list[dict] = []
    if filter_type:
        conds.append({"type": {"$eq": filter_type}})
    if year_from:
        conds.append({"year": {"$gte": year_from}})
    if year_to:
        conds.append({"year": {"$lte": year_to}})

    if not conds:
        return None
    return conds[0] if len(conds) == 1 else {"$and": conds}


def upsert_vectors(vectors: list[dict]) -> None:
    """Batch-upsert vectors into the Pinecone index."""
    index = get_index()
    index.upsert(vectors=vectors)


def semantic_search(
    embedding: list[float],
    top_k: int = 10,
    pinecone_filter: dict | None = None,
) -> list:
    """Run a semantic search and return raw Pinecone match objects."""
    index = get_index()
    results = index.query(
        vector=embedding,
        top_k=top_k,
        include_metadata=True,
        filter=pinecone_filter,
    )
    return results.matches