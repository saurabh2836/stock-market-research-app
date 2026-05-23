"""
app/services/embedding_service.py
----------------------------------
Single responsibility: produce vector embeddings via OpenAI.
"""
from app.core.clients import openai_client
from app.core.config import settings


def embed_text(text: str) -> list[float]:
    """Return a float vector for the given text using the configured embedding model."""
    response = openai_client.embeddings.create(
        model=settings.embed_model,
        input=text,
        dimensions=settings.embed_dim,
    )
    return response.data[0].embedding