#!/usr/bin/env python3
"""Optional smoke checks for HF inference endpoint (read-only).

Usage (from repo root, PYTHONPATH set):

  PYTHONPATH=. python AppV2/backend/scripts/smoke_endpoints.py

Requires HF_INFERENCE_BASE_URL in the environment (e.g. from AppV2/.env).
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    base = os.getenv("HF_INFERENCE_BASE_URL", "").strip().rstrip("/")
    if not base:
        print("HF_INFERENCE_BASE_URL is not set", file=sys.stderr)
        return 2

    health = base.replace("/v1", "") + "/health"
    try:
        urllib.request.urlopen(health, timeout=10)
    except urllib.error.HTTPError as e:
        print(f"health HTTP {e.code}: {health}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"health failed: {e}", file=sys.stderr)
        return 1

    print(f"OK: {health}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
