---
name: CN Paper Downloader
description: >
  Scrape PDFs and peer review attachments (审稿意见) from Magtech-based Chinese academic journals
  (e.g. journal.psych.ac.cn). Supports year-range filtering, resume/checkpoint, and structured
  output directories. Use when user wants to download papers from 心理学报 (xlxb), 心理科学进展 (xlkxjz),
  or another journal that needs a new download route. Reuse recorded routes first; for an
  unmatched or broken route, investigate and iterate until acquisition succeeds, validate
  repeatability, and save the successful method for future runs. Triggers on: "爬取期刊",
  "下载论文PDF", "批量下载", "抓取审稿意见", "下载最新一期".
---

# CN Paper Downloader

Resolve scripts and references relative to this Skill directory; run the examples from it.

Scrapes PDFs + peer review attachments from Magtech CMS journals. The two built-in journal
routes use `journal.psych.ac.cn`. Other sites require agent-led discovery; the Python CLI
does not automatically support arbitrary URLs.

## Route selection and learning

1. Read [the route index](references/routes/README.md). Match the actual host and journal
   path, the requested resource and the recorded prerequisites. Reuse an applicable route
   before exploring again.
2. Use the built-in route for `xlxb` or `xlkxjz`. For another recorded route, follow its
   exact procedure and verify a small sample before a full run.
3. If no route matches, or a previously working route fails, follow
   [site discovery](references/site-discovery.md). Keep inspecting evidence and adjusting
   the approach until the requested acquisition succeeds; a first failed request or a
   fixed attempt count is not a stopping rule.
4. Verify the downloaded content, rerun the successful method, then save the reproducible
   procedure and the exploration history in a site-specific route. Only mark it stable
   within the scope actually tested. Add it to the route index so the next task finds it.
5. If success requires missing user access, CAPTCHA/OTP, a server recovery, or an unavailable
   source file and no accessible alternative remains, record the exact blocker and resume
   condition. Never label a blocked task successful or keep retrying identical requests.

This is an instruction workflow executed by the agent, not a background crawler that
modifies its own code or pushes to GitHub automatically. Save local experience as part of
the task; publish sanitized route changes only within the user's repository authorization.

## Script

`scripts/scrape.py` — run directly with Python 3 (requires `requests`, `beautifulsoup4`).

```bash
# Latest issue only
python3 scripts/scrape.py --journal xlxb --output /absolute/path/to/papers --latest

# Year range (the current implementation compares years, not months)
python3 scripts/scrape.py --journal xlkxjz --output /absolute/path/to/papers --from 2024-01 --to 2025-12

# Resume interrupted run (checkpoint is always used automatically)
python3 scripts/scrape.py --journal xlxb --output /absolute/path/to/papers --from 2024-01
```

## Supported Journals

| Code | Name |
|------|------|
| `xlxb` | 心理学报 (Acta Psychologica Sinica) |
| `xlkxjz` | 心理科学进展 (Advances in Psychological Science) |

For a new Magtech journal, first verify that its archive, article metadata and download
endpoints match [the built-in recipe](references/routes/magtech-psych.md). Only then append
to the `JOURNALS` dict in the script and save a site-specific route:
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
- **Rate limiting**: page requests use `DEFAULT_DELAY` (1.0s), reduced by worker count for article pages; downloads use `--workers` (default 3). The current `--delay` flag is parsed but not applied; use one worker during discovery.
- **Checkpoint limits**: checkpoints record progress, not verified completeness. Failed articles or review downloads can coexist with a completed issue; audit actual files and metadata before claiming completion or resuming a failed issue.
- **Windows encoding**: stdout forced to UTF-8 to handle Chinese characters

## When User Specifies Output Path

Pass the user's path directly to `--output`. The script creates subdirectories automatically.
Example: user says "保存到 E:/journals" → `--output E:/journals`
