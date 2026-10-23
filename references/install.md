# Install

## 1. Place the skill

Copy the `cn-paper-downloader` folder to one of these locations:

- Codex personal skills: `$CODEX_HOME/skills/cn-paper-downloader`
- Claude personal skills: `$HOME/.claude/skills/cn-paper-downloader`
- Shared local skills: `$HOME/.agents/skills/cn-paper-downloader`

If you keep a shared canonical copy, point app-specific skill folders at it with symlinks.

## 2. Required runtimes and tools

Install and verify:

```bash
python3 --version
python3 -m pip install requests beautifulsoup4
```

The downloader only uses public journal pages and does not require API credentials.

## 3. Environment variables

No environment variables are required.

## 4. Local path mapping

The skill uses project-relative paths for its own scripts. Choose any writable output folder when running the scraper, for example:

```bash
python3 scripts/scrape.py --journal xlxb --output /absolute/path/to/papers --latest
```

Replace `/absolute/path/to/papers` with a folder on the target machine.

## 5. Minimal verification

From the skill folder, run:

```bash
python3 scripts/scrape.py --help
```

Optional live smoke test for the latest issue:

```bash
python3 scripts/scrape.py --journal xlxb --output /absolute/path/to/papers --latest
```

## 6. Notes

- Supported built-in journals: `xlxb` (心理学报) and `xlkxjz` (心理科学进展).
- Read [the route index](routes/README.md) first. For an unmatched site or a failing route,
  follow [site discovery](site-discovery.md), keep adapting until acquisition succeeds, then
  verify repeatability and record the working experience. Only add another Magtech journal
  to `JOURNALS` after checking that its real structure matches the existing parser.
- The scraper creates `metadata.jsonl` and `.checkpoint.json` under the selected output folder for resume support.
- There is no `--resume` flag. Checkpoints can contain completed issues with failed files;
  inspect actual outputs before claiming completeness. See [the built-in route](routes/magtech-psych.md).
- Be polite to journal servers: keep worker counts modest and avoid unnecessary repeated runs.
