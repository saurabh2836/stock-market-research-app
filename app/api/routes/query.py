"""
app/api/routes/query.py
------------------------
Semantic search endpoint.
"""
from fastapi import APIRouter

from app.models.schemas import QueryRequest, QueryResponse
from app.services.query_service import run_query

router = APIRouter()


@router.post(
    "/",
    response_model=QueryResponse,
    summary="Semantic search over ingested annual-report data",
)
async def query_route(req: QueryRequest) -> QueryResponse:
    hits = run_query(req)
    return QueryResponse(question=req.question, hits=hits)