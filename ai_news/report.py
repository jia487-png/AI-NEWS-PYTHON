from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from .text import escape_markdown_link_text
from .types import NewsItem


def _pad(value: int) -> str:
    return str(value).rjust(2, "0")


def format_datetime(value: datetime) -> str:
    local = value.astimezone()
    offset = local.utcoffset() or timedelta(0)
    minutes = int(offset.total_seconds() // 60)
    sign = "+" if minutes >= 0 else "-"
    minutes = abs(minutes)
    return (
        f"{local.year}-{_pad(local.month)}-{_pad(local.day)} "
        f"{_pad(local.hour)}:{_pad(local.minute)}:{_pad(local.second)} "
        f"{sign}{_pad(minutes // 60)}:{_pad(minutes % 60)}"
    )


def format_file_date(value: datetime) -> str:
    return f"{value.year}-{_pad(value.month)}-{_pad(value.day)}"


def build_report(
    items: list[NewsItem],
    generated_at: datetime,
    hours: int,
    since: datetime,
) -> str:
    source_count = len({item.source for item in items})
    lines = [
        "# AI 新闻日报",
        "",
        f"共收录 **{len(items)}** 篇文章，来自 **{source_count}** 个源",
        "",
        f"- 生成时间：{format_datetime(generated_at)}",
        f"- 覆盖范围：最近 {hours} 小时（{format_datetime(since)} 之后）",
        "",
        "## 按时间倒序",
        "",
    ]

    for item in items:
        lines.extend(
            [
                f"### [{escape_markdown_link_text(item.title)}]({item.url})",
                "",
                f"- 来源：{item.source}",
                f"- 发布时间：{format_datetime(item.published_at)}",
                f"- 摘要：{item.summary}",
                "",
            ]
        )

    return "\n".join(lines)


def write_daily_report(
    items: list[NewsItem],
    generated_at: datetime,
    hours: int,
    since: datetime,
    output_dir: str,
) -> Path:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / f"ai-news-{format_file_date(generated_at.astimezone())}.md"
    file_path.write_text(build_report(items, generated_at, hours, since), encoding="utf-8")
    return file_path
