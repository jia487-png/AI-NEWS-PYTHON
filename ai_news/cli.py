from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta

from .aggregate import aggregate_articles
from .feeds import fetch_all_sources
from .report import write_daily_report


def _enable_utf8_streams() -> None:
    """Keep console output readable regardless of the active code page."""
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (AttributeError, ValueError, OSError):
                pass


_enable_utf8_streams()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="抓取最近 24 小时 AI 新闻并生成 Markdown 日报。",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="只保留最近 N 小时的文章，默认 24",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="日报输出目录，默认 output",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.hours <= 0:
        print("[error] --hours 必须是大于 0 的数字", file=sys.stderr)
        raise SystemExit(2)

    generated_at = datetime.now().astimezone()
    since = generated_at - timedelta(hours=args.hours)
    result = fetch_all_sources(since)

    for failure in result.failures:
        print(f"[warning] 抓取失败: {failure}", file=sys.stderr)

    articles = aggregate_articles(result.items, since)
    if not articles:
        print("[error] 最近 24 小时内没有抓到文章，不生成日报。", file=sys.stderr)
        raise SystemExit(1)

    file_path = write_daily_report(
        items=articles,
        generated_at=generated_at,
        hours=args.hours,
        since=since,
        output_dir=args.output,
    )
    source_count = len({article.source for article in articles})
    print(f"[ok] 共收录 {len(articles)} 篇文章，来自 {source_count} 个源")
    print(f"[ok] 日报已生成: {file_path}")
