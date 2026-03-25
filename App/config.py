from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DB_PATH = str((Path(__file__).resolve().parent / "mentorapp.db"))
DEFAULT_VECTOR_DB_PATH = str((Path(__file__).resolve().parent.parent / "VectorDB" / "chroma_library_docs"))


@dataclass(frozen=True)
class Settings:
    """Application configuration loaded from environment variables."""

    host: str = os.getenv("MENTOR_APP_HOST", "127.0.0.1")
    port: int = int(os.getenv("MENTOR_APP_PORT", "8000"))
    backend_mode: str = os.getenv("REPAIR_BACKEND_MODE", "mock").strip().lower()
    workflow_module: str = os.getenv("REPAIR_WORKFLOW_MODULE", "App.workflow_entrypoint")
    workflow_function: str = os.getenv("REPAIR_WORKFLOW_FUNCTION", "run_workflow")
    workflow_source: str = os.getenv("REPAIR_WORKFLOW_SOURCE", "pyfile").strip().lower()
    workflow_py_path: str = os.getenv("REPAIR_WORKFLOW_PY_PATH", "App/langgraph_repair_workflow.py").strip()
    workflow_notebook_path: str = os.getenv(
        "REPAIR_WORKFLOW_NOTEBOOK_PATH",
        "Graph Workflow/LangGraph_SFT_Repair_Workflow.ipynb",
    ).strip()
    database_path: str = os.getenv("MENTOR_APP_DB_PATH", DEFAULT_DB_PATH)
    vector_db_path: str = os.getenv("MENTOR_APP_VECTOR_DB_PATH", DEFAULT_VECTOR_DB_PATH)
    vector_collection_name: str = os.getenv("MENTOR_APP_VECTOR_COLLECTION", "library_docs")


settings = Settings()
