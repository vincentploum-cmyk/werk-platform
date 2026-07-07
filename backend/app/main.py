"""Application entrypoint for Werk Platform API.

Run with: uvicorn app.main:app --reload
"""
from app import app  # noqa: F401 — re-export for uvicorn