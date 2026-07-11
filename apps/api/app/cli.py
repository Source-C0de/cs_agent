"""Tiny CLI helper used by `pyproject.toml` script entry."""
from __future__ import annotations

import sys

from app.main import app


def main() -> int:
    print("Green Lab Support API. Run with: uv run uvicorn app.main:app --reload")
    return 0


if __name__ == "__main__":
    sys.exit(main())