from __future__ import annotations

import os
from functools import lru_cache

from App.workflow_runtime.config import CFG

try:
    from langsmith import Client
    from langsmith import traceable as _traceable
except Exception:  # pragma: no cover
    Client = None
    _traceable = None


def traceable(*args, **kwargs):
    if _traceable is None:
        def _noop_decorator(func):
            return func

        return _noop_decorator
    return _traceable(*args, **kwargs)


@lru_cache(maxsize=1)
def setup_langsmith() -> bool:
    """Enable LangSmith tracing once per process when configured."""
    if not CFG.langsmith_enabled or not CFG.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        return False

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = CFG.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = CFG.langsmith_project
    os.environ["LANGCHAIN_ENDPOINT"] = CFG.langsmith_endpoint

    if Client is None:
        return True

    try:
        client = Client(api_key=CFG.langsmith_api_key)
        projects = [p.name for p in client.list_projects()]
        if CFG.langsmith_project not in projects:
            client.create_project(CFG.langsmith_project)
    except Exception:
        # Tracing can still work even if project management call fails.
        pass

    return True
