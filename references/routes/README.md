# Journal download routes

Read this index before each task. Match host **and journal path**; a similar CMS or shared
domain alone does not establish compatibility. Read the linked recipe, check its prerequisites,
and verify a small sample before bulk downloading.

| Route | Match | Status and evidence | Procedure |
| --- | --- | --- | --- |
| `magtech-psych-xlxb` | `journal.psych.ac.cn/xlxb/` · 心理学报 | Existing built-in route; inherited support, not freshly tested online in this update | [Magtech psychology journals](magtech-psych.md), `--journal xlxb` |
| `magtech-psych-xlkxjz` | `journal.psych.ac.cn/xlkxjz/` · 心理科学进展 | Existing built-in route; inherited support, not freshly tested online in this update | [Magtech psychology journals](magtech-psych.md), `--journal xlkxjz` |

For an unmatched site or a broken recipe, follow [site discovery](../site-discovery.md).
Continue toward a verified success, then record the successful method and its history here.
Do not register a guessed endpoint as a stable route.

## Adding learned routes

- Save one document as `references/routes/<host>-<journal>.md`; use a scope suffix only if
  genuinely different resources need different methods. A new journal on a known host
  still needs explicit matching and validation.
- Use the [route record format](../site-discovery.md#route-record-format). Include failed
  approaches and what fixed them, the working command or script, exact prerequisites,
  sample evidence, verification dates, limits and recovery instructions.
- Add a row linking to it with status `candidate`, `stable` or `blocked`. Failed attempts
  can be recorded as `blocked` to prevent blind repetition; they are not learned successes.
- On later runs, append meaningful changes to the same route's history. Retain the last
  working recipe; demote it if it stops working and promote the replacement after validation.
- Keep raw pages, downloads and detailed run logs in the user's output directory; route
  documents contain sanitized evidence and reproducible steps, never cookies or credentials.
