"""
app/core/clients.py
--------------------
Initialises OpenAI and Pinecone clients once at startup.
Import these singletons anywhere — never re-create them per request.
"""
from openai import OpenAI
from pinecone import Pinecone
from app.core.config import settings


openai_client: OpenAI     = OpenAI(api_key=settings.openai_api_key)
pinecone_client: Pinecone = Pinecone(api_key=settings.pinecone_api_key)
