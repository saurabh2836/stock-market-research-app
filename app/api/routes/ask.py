"""
app/api/routes/ask.py
----------------------
Full RAG answer endpoint.
"""
from fastapi import APIRouter

from app.models.schemas import AskRequest, AskResponse
from app.services.ask_service import run_ask

router = APIRouter()


@router.post(
    "/",
    response_model=AskResponse,
    summary="Ask a question — full RAG answer (GPT-4o multimodal)",
)
async def ask_route(req: AskRequest) -> AskResponse:
    answer = run_ask(req)
    return AskResponse(question=req.question, answer=answer)