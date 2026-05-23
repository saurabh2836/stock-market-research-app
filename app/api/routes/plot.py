"""
app/api/routes/plot.py
-----------------------
Chart generation endpoint — returns a PNG bar chart as a file response.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models.schemas import PlotRequest
from app.services.plot_service import generate_plot

router = APIRouter()


@router.post(
    "/",
    response_class=FileResponse,
    summary="Extract year-wise data from tables and return a PNG bar chart",
)
async def plot_route(req: PlotRequest) -> FileResponse:
    try:
        chart_path = generate_plot(req)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return FileResponse(
        path=str(chart_path),
        media_type="image/png",
        filename=chart_path.name,
    )