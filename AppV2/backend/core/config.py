from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


def _load_env_fallback() -> None:
    # Repo root: .../AppV2/backend/core/config.py -> four levels up
    env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        os.environ.setdefault(key, value)


if load_dotenv is not None:
    load_dotenv()
else:
    _load_env_fallback()


# Backend package root (AppV2/backend): DB + local file storage live here by default
_APPV2_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB_PATH = str(_APPV2_ROOT / "mentorapp_v2.db")
_DEFAULT_STORAGE_DIR = str(_APPV2_ROOT / "storage")


@dataclass(frozen=True)
class Settings:
    """V2 application configuration from environment variables."""

    host: str = os.getenv("APPV2_HOST", "127.0.0.1")
    port: int = int(os.getenv("APPV2_PORT", "8001"))
    database_path: str = os.getenv("APPV2_DB_PATH", _DEFAULT_DB_PATH)
    storage_dir: str = os.getenv("APPV2_STORAGE_DIR", _DEFAULT_STORAGE_DIR)
    # HS256 signing secret for JWT access tokens (set in Docker / .env)
    jwt_secret: str = os.getenv("APPV2_JWT_SECRET", "")
    jwt_algorithm: str = os.getenv("APPV2_JWT_ALGORITHM", "HS256")
    jwt_expire_minutes: int = int(os.getenv("APPV2_JWT_EXPIRE_MINUTES", "1440"))
    # Background grading worker (pluggable pipeline; see `grading/` package)
    grading_worker_enabled: bool = os.getenv("APPV2_GRADING_WORKER_ENABLED", "true").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    grading_poll_interval_seconds: float = float(os.getenv("APPV2_GRADING_POLL_INTERVAL_SECONDS", "2"))
    grading_backend: str = os.getenv("APPV2_GRADING_BACKEND", "mock").strip()
    grading_mock_sleep_seconds: float = float(os.getenv("APPV2_GRADING_MOCK_SLEEP_SECONDS", "10"))
    grading_max_attempts: int = int(os.getenv("APPV2_GRADING_MAX_ATTEMPTS", "6"))
    # If true (default), ensure default admin exists once per process startup (idempotent).
    bootstrap_admin_enabled: bool = os.getenv("APPV2_BOOTSTRAP_ADMIN", "true").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    bootstrap_admin_email: str = os.getenv("APPV2_ADMIN_EMAIL", "admin@gmail.com").strip().lower()
    bootstrap_admin_password: str = os.getenv("APPV2_ADMIN_PASSWORD", "123456")

    @property
    def database_url(self) -> str:
        """SQLite URL for SQLAlchemy / SQLModel."""
        return f"sqlite:///{self.database_path}"


settings = Settings()
