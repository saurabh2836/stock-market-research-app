"""
app/services/ask_service.py
----------------------------
Single responsibility: retrieve context chunks and produce a GPT-4o answer.
Visual chunks are passed as inline images; tables as JSON text.
"""
import base64
from pathlib import Path

from app.core.clients import openai_client
from app.core.config import settings
from app.models.schemas import AskRequest
from app.services.embedding_service import embed_text
from app.services.pinecone_service import build_filter, semantic_search


def run_ask(req: AskRequest) -> str:
    embedding = embed_text(req.question)
    pfilter   = build_filter(year_from=req.year_from, year_to=req.year_to)
    matches   = semantic_search(embedding, top_k=req.top_k, pinecone_filter=pfilter)

    content_blocks: list[dict] = [{
        "type": "text",
        "text": (
            "You are an analyst answering questions about company annual reports spanning multiple years. "
            "Use ONLY the retrieved context below. Always cite the source file and page number.\n\n"
            f"Question: {req.question}"
        ),
    }]

    for match in matches:
        meta   = match.metadata
        mtype  = meta.get("type")
        source = meta.get("source", "unknown")
        page   = meta.get("page", "?")

        if mtype == "visual":
            img_path = Path(meta.get("image_path", ""))
            if img_path.exists():
                b64 = base64.b64encode(img_path.read_bytes()).decode()
                content_blocks.append({"type": "text", "text": f"[{source} — Page {page} — visual chart/graph]:"})
                content_blocks.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"},
                })
        elif mtype == "table":
            content_blocks.append({"type": "text", "text": (
                f"[{source} — Page {page} — table]:\n"
                f"Description: {meta.get('text', '')}\n"
                f"Data: {meta.get('records', '[]')}"
            )})
        else:
            content_blocks.append({"type": "text", "text": f"[{source} — Page {page} — text]:\n{meta.get('text', '')}"})

    response = openai_client.chat.completions.create(
        model=settings.vision_model,
        max_tokens=1500,
        messages=[{"role": "user", "content": content_blocks}],
    )
    return response.choices[0].message.content