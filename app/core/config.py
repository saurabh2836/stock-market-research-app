"""
app/core/config.py
------------------
All environment-driven configuration lives here.
Access anywhere via:  from app.core.config import settings
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API keys
    openai_api_key: str
    pinecone_api_key: str

    # Pinecone
    pinecone_index_name: str = "annual-report"
    pinecone_cloud: str      = "aws"
    pinecone_region: str     = "us-east-1"

    # Models
    embed_model: str  = "text-embedding-3-large"
    embed_dim: int    = 2048
    vision_model: str = "gpt-4o"

    # Chunking
    chunk_size: int    = 800
    chunk_overlap: int = 150

    # Image
    dpi: int            = 150
    max_img_pixels: int = 1024

    # Storage
    img_dir: str    = "report_images"
    pdf_folder: str = "pdf_folder"

    # App
    app_title: str   = "Annual Report RAG API"
    app_version: str = "1.0.0"
    debug: bool      = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
