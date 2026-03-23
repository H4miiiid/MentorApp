from __future__ import annotations

import argparse

import uvicorn

from .config import settings


def run_api() -> None:
    uvicorn.run("App.api:app", host=settings.host, port=settings.port, reload=False)


def run_ui() -> None:
    # Deprecated mode kept for backward compatibility.
    run_api()


def run_all() -> None:
    # One-process mode: FastAPI serving HTML/CSS/JS frontend and backend API.
    run_api()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MentorApp launcher")
    parser.add_argument(
        "--mode",
        choices=["api", "ui", "all"],
        default="api",
        help="Select which component to run",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.mode == "api":
        run_api()
    elif args.mode == "ui":
        run_ui()
    else:
        run_all()


if __name__ == "__main__":
    main()
