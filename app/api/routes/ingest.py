"""
app/api/routes/ingest.py
-------------------------
Routes for PDF ingestion. Each route does one thing:
receive the HTTP request, delegate to the service, return a response.
"""
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.schemas   import IngestAllResult, IngestAllYearsResult, IngestPDFResult, IngestTableResult
from app.services.ingest_service import ingest_pdf, ingest_tables

router = APIRouter()


async def _save_upload(file: UploadFile) -> str:
    """Write the uploaded file to a temp path and return it."""
    contents = await file.read()
    tmp      = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(contents)
    tmp.close()
    return tmp.name


@router.post(
    "/pdf",
    response_model=IngestPDFResult,
    summary="Ingest a single PDF — text and visual pages",
)
async def ingest_pdf_route(file: UploadFile = File(..., description="Annual-report PDF")):
    tmp_path = await _save_upload(file)
    try:
        return ingest_pdf(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post(
    "/tables",
    response_model=IngestTableResult,
    summary="Ingest tables only from a single PDF",
)
async def ingest_tables_route(file: UploadFile = File(..., description="Annual-report PDF")):
    tmp_path = await _save_upload(file)
    try:
        return ingest_tables(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post(
    "/all",
    response_model=IngestAllResult,
    summary="Ingest everything (text + visual + tables) from a single PDF",
)
async def ingest_all_route(file: UploadFile = File(..., description="Annual-report PDF")):
    tmp_path = await _save_upload(file)
    try:
        pdf_result   = ingest_pdf(tmp_path)
        table_result = ingest_tables(tmp_path)
        return IngestAllResult(pdf=pdf_result, tables=table_result)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post(
    "/all-years",
    response_model=IngestAllYearsResult,
    summary="Ingest every PDF in a server-side folder",
)
async def ingest_all_years_route(folder: str):
    pdf_folder = Path(folder)
    pdf_files  = sorted(pdf_folder.glob("*.pdf"))

    if not pdf_files:
        raise HTTPException(status_code=404, detail=f"No PDFs found in: {pdf_folder.resolve()}")

    results = []
    for pdf_path in pdf_files:
        pdf_r   = ingest_pdf(str(pdf_path))
        table_r = ingest_tables(str(pdf_path))
        results.append(IngestAllResult(pdf=pdf_r, tables=table_r))

    return IngestAllYearsResult(status="ok", files_processed=len(results), results=results)