# Boat CN Paper Downloader

Codex/Claude skill for downloading PDFs and peer review attachments (审稿意见) from Magtech-based Chinese academic journals, including 心理学报 (`xlxb`) and 心理科学进展 (`xlkxjz`).

## What it does

- Scrapes issue lists from Magtech journal archives.
- Downloads article PDFs and available peer review attachments.
- Supports latest-issue and year-range runs.
- Writes structured folders, `metadata.jsonl`, and `.checkpoint.json` for resume support.

## Quick start

```bash
python3 -m pip install requests beautifulsoup4
python3 scripts/scrape.py --journal xlxb --output /absolute/path/to/papers --latest
```

See [`SKILL.md`](SKILL.md) for usage workflow and [`references/install.md`](references/install.md) for installation notes.
