# Built-in route: Magtech psychology journals

## Match and status

- `magtech-psych-xlxb`: `https://journal.psych.ac.cn/xlxb/`, 心理学报.
- `magtech-psych-xlkxjz`: `https://journal.psych.ac.cn/xlkxjz/`, 心理科学进展.
- Existing built-in support from the original Skill and `scripts/scrape.py`. This update
  inspected the source; no new live download or repeatability claim is made.
- Resource: main paper PDFs and publicly linked peer-review attachments. Other journals
  and resources require their own validation.

## Working recipe

Run from the Skill directory with Python 3, `requests` and `beautifulsoup4` installed:

```bash
python3 scripts/scrape.py --journal xlxb --output /absolute/path/to/papers --latest
python3 scripts/scrape.py --journal xlkxjz --output /absolute/path/to/papers --latest
```

Use `--from YYYY-MM --to YYYY-MM` for a year range. The current filter uses only the year.
Start with `--workers 1` when checking a changed site. Latest-issue mode downloads an issue,
not just a single article; for discovery inspect a small sample before launching this run.

## Acquisition chain

1. Archive: `<base>/CN/article/showOldVolumn.do`; parse year cells and `volumn_*.shtml` links.
2. Issue: collect and deduplicate `/CN/10.<registrant>/...` article links.
3. Article: inspect `citation_pdf_url`, `citation_title`, `citation_author` and `citation_doi`.
4. Main PDF: use the observed metadata URL, normally `downloadArticleFile.do?attachType=PDF&id=...`.
5. Review: use an actual page link containing `attachType=PSFJ`; absence means no linked
   public review was observed, rather than a reason to invent an attachment URL.
6. Save under `<output>/<journal>/<year>/<issue>/<article_id>_<title>/` and write journal
   `metadata.jsonl` and `.checkpoint.json`.

## Verify and recover

- Check response bytes are a PDF, open or parse it, and confirm its title/DOI matches the
  requested article. Check review files separately; a `.pdf` filename is insufficient.
- The current downloader streams bytes without validating PDF content. Its progress and
  checkpoint messages alone are not evidence of success.
- A completed issue can contain failed downloads; existing partial files can be skipped
  on rerun. Compare the requested article list, files and metadata, preserve suspect files
  for diagnosis, then retry missing/invalid items in a separate staging directory or repair
  only the affected checkpoint entries after inspecting them. Never delete a whole library.
- `--resume` is not a CLI option; checkpoint loading is automatic. `--delay` currently has
  no effect. Use conservative workers and agent-controlled pacing for discovery.
- If archive layout, DOI patterns or download endpoints change, follow
  [site discovery](../site-discovery.md), record the observed change and verify the fix.

## History

- 2026-10-23: extracted the existing two built-in journal mappings and the source-defined
  acquisition chain into this shared recipe; documented current validation and checkpoint
  limits. No new external site was explored during this documentation change.
