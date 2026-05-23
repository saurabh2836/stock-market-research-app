"""
app/services/plot_service.py
-----------------------------
Single responsibility: extract year-wise numeric data from matched tables
and produce a bar-chart PNG.
"""
import json
import re
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from app.core.clients import openai_client
from app.core.config import settings
from app.models.schemas import PlotRequest
from app.services.embedding_service import embed_text
from app.services.pinecone_service import semantic_search
from app.utils.file_utils import clean_number


def _extract_point(records: list[dict], year: int, page: int, question: str) -> tuple[str, float] | None:
    prompt = f"""
You are a data extraction assistant for financial charts.

User question: {question}

This table is from the {year} annual report, page {page}:
{json.dumps(records, indent=2)}

Extract the single most relevant data point (one x label and one y value) that answers the question.
Respond ONLY with valid JSON — no markdown, no explanation:
{{
  "x": "{year}",
  "y": <numeric value only, no symbols>,
  "metric": "name of the metric",
  "unit": "Crore or % or other"
}}

If this table does not contain relevant data, respond with:
{{"x": null, "y": null, "metric": null, "unit": null}}
"""
    res   = openai_client.chat.completions.create(
        model=settings.vision_model, max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    raw   = re.sub(r"```json|```", "", res.choices[0].message.content).strip()
    point = json.loads(raw)

    if point.get("x") is None or point.get("y") is None:
        return None
    y_val = clean_number(point["y"])
    return (str(point["x"]), y_val) if y_val is not None else None


def generate_plot(req: PlotRequest) -> Path:
    embedding = embed_text(req.question)

    conds = [{"type": {"$eq": "table"}}]
    if req.year_from:
        conds.append({"year": {"$gte": req.year_from}})
    if req.year_to:
        conds.append({"year": {"$lte": req.year_to}})
    pfilter = {"$and": conds} if len(conds) > 1 else conds[0]

    matches = semantic_search(embedding, top_k=20, pinecone_filter=pfilter)
    if not matches:
        raise ValueError("No matching tables found for the given question and filters.")

    all_x: list[str]   = []
    all_y: list[float] = []

    for match in matches:
        meta    = match.metadata
        records = json.loads(meta["records"])
        year    = meta.get("year", 0)
        page    = meta.get("page", 0)
        try:
            point = _extract_point(records, year, page, req.question)
            if point:
                all_x.append(point[0])
                all_y.append(point[1])
        except Exception:
            continue

    if not all_x:
        raise ValueError("Could not extract plottable data from any matched table.")

    pairs      = sorted(zip(all_x, all_y), key=lambda p: p[0])
    all_x, all_y = map(list, zip(*pairs))

    fig, ax = plt.subplots(figsize=(13, 6))
    x_pos   = range(len(all_x))
    bars    = ax.bar(x_pos, all_y, color="#2563eb", width=0.6)

    for bar, val in zip(bars, all_y):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(all_y) * 0.01,
            f"{val:,.0f}", ha="center", va="bottom", fontsize=9, color="#1e3a5f", fontweight="bold",
        )

    ax.set_xticks(x_pos)
    ax.set_xticklabels(all_x, rotation=45, ha="right", fontsize=10)
    ax.set_title(req.question, fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Year", fontsize=11, labelpad=10)
    ax.set_ylabel("Value", fontsize=11, labelpad=10)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()

    year_tag = f"{req.year_from}_{req.year_to}" if req.year_from else "all"
    out_path = Path(tempfile.gettempdir()) / f"chart_{year_tag}.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path