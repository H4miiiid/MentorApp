from __future__ import annotations

import logging
import os
from functools import lru_cache

from AppV2.backend.workflow_runtime.config import CFG

logger = logging.getLogger(__name__)

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


def _clear_langsmith_env_caches() -> None:
    """LangSmith's ``get_env_var`` / ``get_tracer_project`` use ``lru_cache`` on env reads.

    If those run *before* we set ``LANGCHAIN_TRACING_V2`` / project from :func:`setup_langsmith`,
    tracing stays off for the whole process. Clear caches after mutating ``os.environ``.
    """
    try:
        from langsmith import utils as ls_utils

        ls_utils.get_env_var.cache_clear()
        ls_utils.get_tracer_project.cache_clear()
    except Exception:
        logger.debug("[langsmith] could not clear langsmith env caches", exc_info=True)


@lru_cache(maxsize=1)
def setup_langsmith() -> bool:
    """Enable LangSmith tracing once per process when configured."""
    if not CFG.langsmith_enabled or not CFG.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        os.environ["LANGSMITH_TRACING_V2"] = "false"
        _clear_langsmith_env_caches()
        logger.info(
            "[langsmith] tracing disabled (enabled=%s api_key_present=%s)",
            CFG.langsmith_enabled,
            bool(CFG.langsmith_api_key),
        )
        return False

    # Both namespaces are checked (LANGSMITH_* first); set so ``tracing_is_enabled()`` is true.
    os.environ["LANGSMITH_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = CFG.langsmith_api_key
    os.environ["LANGSMITH_API_KEY"] = CFG.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = CFG.langsmith_project
    os.environ["LANGSMITH_PROJECT"] = CFG.langsmith_project
    os.environ["LANGCHAIN_ENDPOINT"] = CFG.langsmith_endpoint
    _clear_langsmith_env_caches()

    if Client is None:
        logger.warning("[langsmith] SDK unavailable, traceable decorators may be no-op")
        return True

    try:
        client = Client(api_key=CFG.langsmith_api_key)
        projects = [p.name for p in client.list_projects()]
        if CFG.langsmith_project not in projects:
            client.create_project(CFG.langsmith_project)
            logger.info("[langsmith] created project '%s'", CFG.langsmith_project)
        else:
            logger.info("[langsmith] using existing project '%s'", CFG.langsmith_project)
    except Exception:
        # Tracing can still work even if project management call fails.
        logger.exception("[langsmith] project bootstrap call failed")

    logger.info("[langsmith] tracing enabled project=%s", CFG.langsmith_project)
    return True
