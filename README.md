# Annual Report RAG API

A FastAPI application that ingests company annual report PDFs into Pinecone and answers questions about them using GPT-4o. Supports text, visual (charts/graphs), and table content — including multimodal retrieval and auto-generated bar charts.

---

## Features

- **PDF Ingestion** — classifies each page as text or visual, chunks and embeds text, describes charts via GPT-4o Vision
- **Table Extraction** — pulls tables with pdfplumber, describes them with GPT-4o, stores full JSON in Pinecone metadata
- **Multi-year Support** — ingest an entire folder of annual reports; filter queries by year range
- **Semantic Search** — cosine similarity search over text, visual, and table vectors
- **RAG Answer** — retrieves top-k context chunks and produces a cited GPT-4o answer with inline images
- **Auto Chart** — extracts year-wise data points from matched tables and returns a PNG bar chart

---

## Tech Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI |
| Vector store | Pinecone (serverless) |
| Embeddings | OpenAI `text-embedding-3-large` |
| Vision / LLM | OpenAI `gpt-4o` |
| PDF parsing | pdfplumber + PyMuPDF |
| Charting | Matplotlib |
| Config | pydantic-settings |

---

## Project Structure

```
annual_report_api/
├── main.py                        # Entry point
├── requirements.txt
├── .env                           # API keys (never commit)
├── .gitignore
└── app/
    ├── core/
    │   ├── config.py              # All env config via pydantic-settings
    │   ├── clients.py             # OpenAI + Pinecone singletons
    │   └── app_factory.py         # Registers routers + middleware
    ├── middleware/
    │   ├── logging_middleware.py  # Logs method / path / status / ms
    │   └── error_handler.py       # Maps exceptions → JSON responses
    ├── models/
    │   └── schemas.py             # All Pydantic request + response models
    ├── services/
    │   ├── embedding_service.py   # embed_text()
    │   ├── pinecone_service.py    # get_index(), semantic_search(), build_filter()
    │   ├── ingest_service.py      # ingest_pdf(), ingest_tables()
    │   ├── query_service.py       # run_query()
    │   ├── ask_service.py         # run_ask()
    │   └── plot_service.py        # generate_plot()
    ├── utils/
    │   └── file_utils.py          # year_from_filename(), chunk_text(), clean_number()
    └── api/
        └── routes/
            ├── ingest.py          # POST /ingest/*
            ├── query.py           # POST /query/
            ├── ask.py             # POST /ask/
            └── plot.py            # POST /plot/
```

---

## Setup

### 1. Clone and enter the project

```bash
git clone <your-repo-url>
cd annual_report_api
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=annual-report
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
```

Get your Pinecone API key from [app.pinecone.io](https://app.pinecone.io).

### 5. Run the server

```bash
uvicorn main:app --reload
```

Server starts at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

## API Endpoints

### Ingest

| Method | Endpoint | Description |
|---|---|---|
| POST | `/ingest/pdf` | Ingest text + visual pages from a single PDF |
| POST | `/ingest/tables` | Ingest tables only from a single PDF |
| POST | `/ingest/all` | Ingest everything from a single PDF |
| POST | `/ingest/all-years` | Ingest all PDFs in a server-side folder |

**Ingest a PDF:**
```bash
curl -X POST http://localhost:8000/ingest/all \
  -F "file=@/path/to/2024.pdf"
```

**Ingest all PDFs in a folder:**
```bash
curl -X POST "http://localhost:8000/ingest/all-years?folder=/path/to/pdfs"
```

---

### Query

**Semantic search** — returns matching chunks with scores:

```bash
curl -X POST http://localhost:8000/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "EBITDA margin trend",
    "top_k": 5,
    "filter_type": "table",
    "year_from": 2020,
    "year_to": 2024
  }'
```

| Field | Type | Description |
|---|---|---|
| `question` | string | Natural language search query |
| `top_k` | int | Number of results (1–50, default 10) |
| `filter_type` | string | `"text"` \| `"visual"` \| `"table"` (optional) |
| `year_from` | int | Inclusive lower year bound (optional) |
| `year_to` | int | Inclusive upper year bound (optional) |

---

### Ask

**RAG answer** — retrieves context and returns a GPT-4o cited answer:

```bash
curl -X POST http://localhost:8000/ask/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What was the revenue growth in 2024?",
    "top_k": 10,
    "year_from": 2020,
    "year_to": 2024
  }'
```

---

### Plot

**Auto chart** — extracts year-wise data from tables and returns a PNG:

```bash
curl -X POST http://localhost:8000/plot/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Revenue growth year over year",
    "year_from": 2020,
    "year_to": 2024
  }' \
  --output chart.png
```

---

## How Ingestion Works

```
PDF
 ├── Visual pages (image-heavy, <600 chars text)
 │    └── Render to JPEG → GPT-4o Vision description → embed → Pinecone
 │         metadata: description, image_path, page, year, source
 │
 ├── Text pages
 │    └── Extract text → chunk (800 chars, 150 overlap) → embed → Pinecone
 │         metadata: chunk text, page, year, source
 │
 └── Tables (all pages)
      └── pdfplumber extract → GPT-4o description → embed → Pinecone
           metadata: description, full JSON records, headers, page, year, source
```

Year is automatically inferred from the PDF filename (e.g. `2024.pdf` → `year=2024`).

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | required | OpenAI API key |
| `PINECONE_API_KEY` | required | Pinecone API key |
| `PINECONE_INDEX_NAME` | `annual-report` | Pinecone index name |
| `PINECONE_CLOUD` | `aws` | Pinecone cloud provider |
| `PINECONE_REGION` | `us-east-1` | Pinecone region |
| `EMBED_MODEL` | `text-embedding-3-large` | OpenAI embedding model |
| `EMBED_DIM` | `2048` | Embedding dimensions |
| `VISION_MODEL` | `gpt-4o` | OpenAI vision/chat model |
| `CHUNK_SIZE` | `800` | Text chunk size in characters |
| `CHUNK_OVERLAP` | `150` | Overlap between chunks |
| `DPI` | `150` | DPI for page rendering |
| `IMG_DIR` | `report_images` | Directory to store rendered images |

---

## Running Tests

```bash
pytest app/tests/ -v
```

---

## .gitignore

```
.env
.venv
__pycache__/
*.pyc
report_images/
*.png
```