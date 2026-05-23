"""
Entry point — run with:
    uvicorn main:app --reload
"""
from app.core.app_factory import create_app

app = create_app()
