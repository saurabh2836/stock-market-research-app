"""
app/services/query_service.py
------------------------------
Single responsibility: retrieve matching chunks from Pinecone
and shape them into QueryHit objects.
"""
from app.models.schemas import QueryHit, QueryRequest
from app.services.embedding_service import embed_text
from app.services.pinecone_service import build_filter, semantic_search


def run_query(req: QueryRequest) -> list[QueryHit]:
    embedding = embed_text(req.question)
    pfilter   = build_filter(req.filter_type, req.year_from, req.year_to)
    matches   = semantic_search(embedding, top_k=req.top_k, pinecone_filter=pfilter)

    hits: list[QueryHit] = []
    for match in matches:
        meta = match.metadata
        hit  = QueryHit(
            score=match.score,
            page=meta.get("page"),
            type=meta.get("type", ""),
            text=meta.get("text", ""),
            source=meta.get("source", ""),
            year=meta.get("year", 0),
        )
        if meta.get("type") == "visual":
            hit.image_path = meta.get("image_path")
        if meta.get("type") == "table":
            hit.headers = meta.get("headers")
            hit.records = meta.get("records")
        hits.append(hit)

    return hits