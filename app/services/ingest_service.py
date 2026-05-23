"""
app/services/ingest_service.py
-------------------------------
Orchestrates PDF ingestion:
  - classify pages (visual vs text)
  - render visual pages → GPT-4o description → embed → upsert
  - chunk text pages → embed → upsert
  - extract tables → GPT-4o description → embed → upsert
"""
import base64
import hashlib
import json
from io import BytesIO
from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber
from PIL import Image
from tqdm import tqdm

from app.core.clients import openai_client
from app.core.config import settings
from app.models.schemas import IngestPDFResult, IngestTableResult
from app.services.embedding_service import embed_text
from app.services.pinecone_service import get_index
from app.utils.file_utils import year_from_filename, chunk_text, clean_number

IMG_DIR = Path(settings.img_dir)
IMG_DIR.mkdir(exist_ok=True)


# ── Page classification ───────────────────────────────────────────────────────

def classify_pages(pdf_path: str) -> dict[int, str]:
    page_types: dict[int, str] = {}
    doc = fitz.open(pdf_path)
    with pdfplumber.open(pdf_path) as plumber_pdf:
        for i, page in enumerate(doc):
            images     = page.get_images(full=True)
            image_area = sum(abs((img[2] or 0) * (img[3] or 0)) for img in images)
            text       = plumber_pdf.pages[i].extract_text() or ""
            page_types[i + 1] = (
                "visual" if image_area > 20_000 and len(text.strip()) < 600 else "text"
            )
    doc.close()
    return page_types


# ── Image helpers ─────────────────────────────────────────────────────────────

def render_page_to_image(pdf_path: str, page_num: int) -> bytes:
    doc  = fitz.open(pdf_path)
    page = doc[page_num - 1]
    mat  = fitz.Matrix(settings.dpi / 72, settings.dpi / 72)
    pix  = page.get_pixmap(matrix=mat, alpha=False)
    img  = Image.open(BytesIO(pix.tobytes("png")))
    img.thumbnail((800, 800), Image.LANCZOS)
    buf  = BytesIO()
    img.save(buf, format="JPEG", quality=60)
    doc.close()
    return buf.getvalue()


def resize_image(img_bytes: bytes) -> bytes:
    img = Image.open(BytesIO(img_bytes))
    img.thumbnail((settings.max_img_pixels, settings.max_img_pixels), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Vision helpers ────────────────────────────────────────────────────────────

def describe_visual_page(img_bytes: bytes, page_num: int) -> str:
    b64 = base64.b64encode(resize_image(img_bytes)).decode()
    res = openai_client.chat.completions.create(
        model=settings.vision_model,
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"},
                },
                {
                    "type": "text",
                    "text": (
                        f"This is page {page_num} of a company annual report. "
                        "Describe everything on this page in detail: all chart titles, axis labels, "
                        "data values, time periods, trends, percentages, financial figures, and key takeaways. "
                        "Be specific so a search engine can match queries like '5-year revenue growth', "
                        "'EBITDA trend', 'profit chart', etc."
                    ),
                },
            ],
        }],
    )
    return res.choices[0].message.content


def describe_table(table: dict, year: int) -> str:
    sample = table["records"][:3]
    prompt = (
        f"This is a financial table from page {table['page']} of a {year} annual report.\n"
        f"Column headers: {', '.join(table['headers'])}\n"
        f"Sample rows: {json.dumps(sample, indent=2)}\n\n"
        "Describe what this table contains: metric names, time periods, units (crore, %, etc.), "
        "and key figures. Use terms like 'revenue', 'profit', 'EBITDA', 'year-wise', 'growth', 'segment'."
    )
    res = openai_client.chat.completions.create(
        model=settings.vision_model,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return res.choices[0].message.content


# ── Table extraction ──────────────────────────────────────────────────────────

def extract_tables(pdf_path: str) -> list[dict]:
    all_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            for t_idx, table in enumerate(page.extract_tables()):
                if not table or len(table) < 2:
                    continue
                headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(table[0])]
                records = [
                    {
                        headers[i]: (cell.strip() if cell else "")
                        for i, cell in enumerate(row)
                        if i < len(headers)
                    }
                    for row in table[1:]
                ]
                records = [r for r in records if any(r.values())]
                if records:
                    all_tables.append({
                        "page":      page_num,
                        "table_idx": t_idx,
                        "headers":   headers,
                        "records":   records,
                        "table_id":  f"table_{Path(pdf_path).name}_p{page_num}_t{t_idx}",
                    })
    return all_tables


# ── Public ingest functions ───────────────────────────────────────────────────

def ingest_pdf(pdf_path: str) -> IngestPDFResult:
    source_name = Path(pdf_path).name
    year        = year_from_filename(source_name)
    index       = get_index()
    page_types  = classify_pages(pdf_path)

    visual_count = text_count = error_count = 0
    batch: list[dict] = []

    with pdfplumber.open(pdf_path) as plumber_pdf:
        for page_num, page_type in tqdm(page_types.items(), desc=f"Ingesting pages [{source_name}]"):
            plumber_page = plumber_pdf.pages[page_num - 1]

            if page_type == "visual":
                try:
                    img_bytes   = render_page_to_image(pdf_path, page_num)
                    description = describe_visual_page(img_bytes, page_num)
                    embedding   = embed_text(description)
                except Exception:
                    error_count += 1
                    continue

                img_path = IMG_DIR / f"{year}_page_{page_num}.jpg"
                img_path.write_bytes(img_bytes)
                index.upsert(vectors=[{
                    "id": f"visual_{source_name}_p{page_num}",
                    "values": embedding,
                    "metadata": {
                        "type": "visual", "page": page_num, "text": description,
                        "image_path": str(img_path), "source": source_name, "year": year,
                    },
                }])
                visual_count += 1

            else:
                raw_text = plumber_page.extract_text() or ""
                if not raw_text.strip():
                    continue
                for chunk_idx, chunk in enumerate(chunk_text(raw_text)):
                    chunk_hash = hashlib.md5(chunk.encode()).hexdigest()[:8]
                    batch.append({
                        "id": f"text_{source_name}_p{page_num}_c{chunk_idx}_{chunk_hash}",
                        "values": embed_text(chunk),
                        "metadata": {
                            "type": "text", "page": page_num, "text": chunk,
                            "source": source_name, "year": year,
                        },
                    })
                    text_count += 1

                if len(batch) >= 50:
                    index.upsert(vectors=batch)
                    batch = []

    if batch:
        index.upsert(vectors=batch)

    return IngestPDFResult(
        source=source_name, year=year,
        visual_pages=visual_count, text_chunks=text_count, errors=error_count,
    )


def ingest_tables(pdf_path: str) -> IngestTableResult:
    source_name = Path(pdf_path).name
    year        = year_from_filename(source_name)
    index       = get_index()
    tables      = extract_tables(pdf_path)

    ingested = errors = 0
    for table in tqdm(tables, desc=f"Ingesting tables [{source_name}]"):
        try:
            description = describe_table(table, year)
            embedding   = embed_text(description)
        except Exception:
            errors += 1
            continue

        records_json = json.dumps(table["records"])
        if len(records_json) > 30_000:
            records_json = json.dumps(table["records"][:50])

        index.upsert(vectors=[{
            "id": table["table_id"],
            "values": embedding,
            "metadata": {
                "type": "table", "page": table["page"], "text": description,
                "headers": json.dumps(table["headers"]), "records": records_json,
                "source": source_name, "year": year,
            },
        }])
        ingested += 1

    return IngestTableResult(
        source=source_name, year=year,
        tables_ingested=ingested, errors=errors,
    )