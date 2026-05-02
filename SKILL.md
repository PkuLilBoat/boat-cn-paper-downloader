---
name: CN Paper Downloader
description: >
  Scrape PDFs and peer review attachments (审稿意见) from Magtech-based Chinese academic journals
  (e.g. journal.psych.ac.cn). Supports date-range filtering, resume/checkpoint, and structured
  output directories. Use when user wants to download papers from 心理学报 (xlxb), 心理科学进展 (xlkxjz),
  or any other Magtech journal. Triggers on: "爬取期刊", "下载论文PDF", "批量下载", "抓取审稿意见", "下载最新一期".
---

# CN Paper Downloader

Scrapes PDFs + peer review attachments from Magtech CMS journals. Tested on journal.psych.ac.cn.

## Script

`scripts/scrape.py` — run directly with Python 3 (requires `requests`, `beautifulsoup4`).

```bash
# Latest issue only
python scrape.py --journal xlxb --output D:/papers --latest

# Date range
python scrape.py --journal xlkxjz --output D:/papers --from 2024-01 --to 2025-12

# Resume interrupted run (checkpoint is always used automatically)
python scrape.py --journal xlxb --output D:/papers --from 2024-01 --resume
```

## Supported Journals

| Code | Name |
|------|------|
| `xlxb` | 心理学报 (Acta Psychologica Sinica) |
| `xlkxjz` | 心理科学进展 (Advances in Psychological Science) |

To add a new Magtech journal, append to the `JOURNALS` dict in the script:
```python
"code": {"name": "期刊名", "base_url": "https://journal.example.cn/code"}
```

## Output Structure

```
<output>/<journal>/<year>/<issue>/
  <article_id>_<title>/
    <article_id>.pdf          ← main paper
    <article_id>_review.pdf   ← peer review attachment (if available)
<output>/<journal>/metadata.jsonl  ← one JSON record per article
<output>/<journal>/.checkpoint.json ← resume state
```

## Key Implementation Notes

- **PDF download**: GET `downloadArticleFile.do?attachType=PDF&id=<article_id>` — no auth needed
- **Review attachment**: same endpoint with `attachType=PSFJ` — only present on some articles
- **Article ID**: extracted from `<meta name="citation_pdf_url">` on each article page
- **Issue list**: parsed from `showOldVolumn.do` — `../volumn/volumn_NNN.shtml` links
- **Deduplication**: issue page lists each article multiple times; deduplicated by URL
- **Rate limiting**: 1.5s delay between requests (configurable via `DELAY` constant)
- **Windows encoding**: stdout forced to UTF-8 to handle Chinese characters

## When User Specifies Output Path

Pass the user's path directly to `--output`. The script creates subdirectories automatically.
Example: user says "保存到 E:/journals" → `--output E:/journals`
