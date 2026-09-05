#!/usr/bin/env python3
import sys

from ai_news.cli import main


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # noqa: BLE001
        print(f"[error] {error}", file=sys.stderr)
        raise SystemExit(1) from error
