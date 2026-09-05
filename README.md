# AI News

Python 版 AI 新闻日报聚合 CLI：抓取 TechCrunch、The Verge 与 Hacker News 近 24 小时的 AI 内容，生成带统计、摘要并按时间倒序排列的 Markdown 日报。

Hacker News 没有官方 AI 标签，工具会从最新 story 流中按标题/正文里的 AI、LLM、OpenAI、Claude、Gemini 等关键词过滤。

## 运行

```bash
python main.py                      # 默认最近 24 小时，输出到 output/
python main.py --hours 48           # 调整覆盖窗口
python main.py --output reports     # 自定义输出目录
```

仅使用 Python 标准库，无需安装第三方依赖；要求 Python 3.10+。
