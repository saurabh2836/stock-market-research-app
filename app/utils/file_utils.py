"""
app/utils/file_utils.py
------------------------
Pure utility functions — no FastAPI, no OpenAI, no Pinecone.
"""
import re
from app.core.config import settings


def year_from_filename(name: str) -> int:
    """Extract a 4-digit year from a filename, e.g. '2024.pdf' -> 2024."""
    m = re.search(r"\d{4}", name)
    return int(m.group()) if m else 0


def chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks for embedding."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + settings.chunk_size])
        start += settings.chunk_size - settings.chunk_overlap
    return [c.strip() for c in chunks if c.strip()]


def clean_number(val) -> float | None:
    """Strip currency symbols, commas, % signs and convert to float."""
    if isinstance(val, (int, float)):
        return float(val)
    val = str(val).replace("₹", "").replace(",", "").replace("%", "").replace("cr", "").strip()
    try:
        return float(val)
    except ValueError:
        return None