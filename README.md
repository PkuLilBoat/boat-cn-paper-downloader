<img src="assets/community-banner.png" alt="Learning and creating in the AI era" width="680">

<table><tr><td width="180"><img src="assets/wechat.jpg" alt="WeChat community QR code" width="156"></td><td>Scan the QR code to join our lifelong learning community and discussion groups.<br>Let's exchange ideas about AI, knowledge management, and productivity tools.</td></tr></table>

---

# BOAT CN Paper Downloader

English | [简体中文](README.zh-CN.md)

A Codex / Claude Skill for downloading Chinese journal papers and publicly available peer-review attachments. The Python scraper has two built-in journal mappings: 心理学报 (`xlxb`) and 心理科学进展 (`xlkxjz`) on `journal.psych.ac.cn`.

## Capabilities and route learning

- Download main PDFs and linked public review attachments from the two built-in Magtech journals.
- Select the latest issue or a year range; save structured folders, `metadata.jsonl` and `.checkpoint.json`.
- An agent reads the [route index](references/routes/README.md) before each task. It reuses a matching method first.
- For an unknown site or a broken route, the agent follows [site discovery](references/site-discovery.md), diagnoses failures and keeps changing the approach until acquisition succeeds. It then verifies repeatability and records the successful method and investigation history as a reusable route.
- First success produces a candidate; representative samples and a repeat run establish a stable route within the tested scope. Concrete external blockers retain progress and a resume condition.

Route learning is a **Skill instruction workflow**, not an autonomous crawler built into the Python CLI. The current CLI accepts only registered journal codes; other sites can require agent-written scripts or browser steps. This update adds no newly validated external site.

## Install and quick start

Use Python 3 and install the two dependencies in a virtual environment:

```bash
git clone https://github.com/PkuLilBoat/boat-cn-paper-downloader.git
cd boat-cn-paper-downloader
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install requests beautifulsoup4
python3 scripts/scrape.py --journal xlxb --output /absolute/path/to/papers --latest
```

On Windows, activate with `.venv\Scripts\activate` and replace the output path with your own folder. See [installation notes](references/install.md) for Skill placement. Agents start with [SKILL.md](SKILL.md).

## Settings and limits

- No API key is required for built-in public journal pages. Supply your own output directory.
- `--from YYYY-MM --to YYYY-MM` currently filters **years only**. `--workers` defaults to 3; use 1 while investigating a site.
- Checkpoint loading is automatic; there is no `--resume` flag. The parsed `--delay` option currently has no effect.
- Checkpoints and progress do not prove completeness: failed or partial downloads can remain behind a completed issue. Verify file content, identity and expected counts separately. See the [built-in route](references/routes/magtech-psych.md) for recovery limits.
- Reviews exist only where the journal publishes them. Website changes, login requirements and unavailable files can require further investigation or user interaction.
- The scripts use Python, Requests and Beautiful Soup. Browser discovery additionally requires tools available to the executing agent; no built-in AI model, MCP server or general-site API is provided.

## Privacy and repository updates

Downloads, raw discovery logs, browser sessions and credentials stay local. Published route records contain sanitized procedures and validation evidence, not cookies, signed download tokens or private page dumps. Future GitHub pushes require repository authorization; the Skill does not publish itself automatically.

## Verification

```bash
python3 scripts/scrape.py --help
```

This checks the CLI entry point only. A real-site result requires inspecting actual downloaded files; route documentation is not a live availability guarantee.

## License

No license is currently specified for this repository. Dependency licenses remain with their respective projects.

## Community and feedback

You can also report problems or suggest improvements through this repository's [GitHub Issues](https://github.com/PkuLilBoat/boat-cn-paper-downloader/issues). Joining the community is optional and is not required to use the tool.
