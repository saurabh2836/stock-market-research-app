"""
app/models/schemas.py
----------------------
All Pydantic request bodies and response shapes.
"""
from pydantic import BaseModel, Field


# ── Ingest ────────────────────────────────────────────────────────────────────

class IngestFolderRequest(BaseModel):
    folder: str = Field(..., description="Absolute path to folder containing PDF files on the server")


class IngestPDFResult(BaseModel):
    source: str
    year: int
    visual_pages: int
    text_chunks: int
    errors: int


class IngestTableResult(BaseModel):
    source: str
    year: int
    tables_ingested: int
    errors: int


class IngestAllResult(BaseModel):
    pdf: IngestPDFResult
    tables: IngestTableResult


class IngestAllYearsResult(BaseModel):
    status: str
    files_processed: int
    results: list[IngestAllResult]


# ── Query ─────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str  = Field(..., description="Natural-language search question")
    top_k: int     = Field(10, ge=1, le=50)
    filter_type: str | None = Field(None, description="'text' | 'visual' | 'table'")
    year_from: int | None   = Field(None, description="Inclusive lower year bound")
    year_to: int | None     = Field(None, description="Inclusive upper year bound")


class QueryHit(BaseModel):
    score: float
    page: int | None
    type: str
    text: str
    source: str
    year: int
    image_path: str | None = None
    headers: str | None    = None
    records: str | None    = None


class QueryResponse(BaseModel):
    question: str
    hits: list[QueryHit]


# ── Ask ───────────────────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str
    top_k: int = Field(10, ge=1, le=50)
    year_from: int | None = None
    year_to: int | None   = None


class AskResponse(BaseModel):
    question: str
    answer: str


# ── Plot ──────────────────────────────────────────────────────────────────────

class PlotRequest(BaseModel):
    question: str
    year_from: int | None = None
    year_to: int | None   = None