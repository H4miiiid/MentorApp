from __future__ import annotations

from AppV2.backend.workflow_runtime.config import CFG


def test_cfg_exposes_sft_and_rag_warmup_fields() -> None:
    assert CFG.sft_http_timeout_seconds >= 1
    assert CFG.sft_max_retries >= 0
    assert isinstance(CFG.rag_warmup_on_startup, bool)
