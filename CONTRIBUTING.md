# Contributing

Thanks for helping make `power-app-yaml` better. The single most valuable
contribution is a **real Power Apps Studio test result** — this skill lives or
dies by whether its control catalog matches what Studio actually accepts.

## Ways to contribute

| You have… | Do this |
|---|---|
| A control/property that Studio **accepted** or **rejected**, and the catalog is wrong or silent about it | Open a [Control test report](https://github.com/YKUNAKORN/power-app-yaml/issues/new?template=control-report.yml) issue, then (optionally) a PR editing `skills/power-app-yaml/references/confirmed-controls.md` |
| A `.pa.yaml` the skill produced that failed to paste | Open a [Bug report](https://github.com/YKUNAKORN/power-app-yaml/issues/new?template=bug_report.yml) with the file and the exact Studio error |
| An idea for the workflow, templates, or a new example screen | Open a [Feature request](https://github.com/YKUNAKORN/power-app-yaml/issues/new?template=feature_request.yml) |

## Reporting a control test result

Because Studio pins control versions, a test result is only useful with context.
Always include:

1. **Control type + version** exactly as it appeared, e.g. `Classic/DropDown@2.3.1`
2. **The property** you tested (or "the control itself")
3. **Studio outcome** — pasted cleanly / warning `PA2105` / blocked `PA1001` / etc.
4. **Studio version** — Power Apps Studio → `?` → About, e.g. `3.24102.x`
5. **The minimal YAML snippet** you pasted (full `Screens:` wrapper, one control)

Example of a good catalog entry:

```markdown
| `Classic/DropDown@2.3.1` | `ChevronBackground` | ✅ Confirmed | Studio 3.24102.x — pasted cleanly, no warning |
```

## Editing the catalog (`controls.yaml` + `confirmed-controls.md`)

The catalog lives in **two files that must be edited together**:

| File | Role |
|---|---|
| `references/controls.yaml` | machine-readable source of truth — what `scripts/pa_lint.py` reads |
| `references/confirmed-controls.md` | the human-readable view of the same facts |

`scripts/validate.py` fails if a control appears in one file but not the other, so a PR
touching only the Markdown will not pass CI.

Two other files sit alongside them:

| File | Role |
|---|---|
| `references/control-ids-candidate.yaml` | Microsoft's first-party control-id enum, mirrored. Every entry is `evidence: unverified` and CI enforces that. It only improves a linter message; nothing in it may be promoted to `controls.yaml` without a Studio test. |
| `scripts/harvest_controls.py` | Grows `controls.yaml` from a real Studio export. See [`docs/harvesting.md`](docs/harvesting.md). |

If you grew the catalog from an export rather than a paste test, say so in the PR and leave the
entry at `evidence: studio-export`. And remember the caveat that governs harvesting: Studio only
serialises properties that differ from their default, so **absence in an export is never evidence
that a control lacks a property**. Never add a "does not support" claim from a harvest.

- **Never** move an item from "unverified" to "confirmed" without a Studio test to cite.
- Keep the empirical tone: say *which Studio version* confirmed it.
- If a newer Studio changes a version number, add a row — don't overwrite history.

## YAML / skill style

- Every property value starts with `=` (`Text: ="hi"`, `X: =0`).
- Block-style `Properties:` only — never inline `{ }` (RGBA commas break flow YAML).
- Example screens under `assets/examples/` must be **real, paste-tested** files with
  generic sample content — no real customer data, no secrets.
- Run the checks locally before opening a PR:

```bash
python scripts/validate.py
python -m unittest discover tests
```

Both need `pyyaml` and `jsonschema`:

```bash
pip install pyyaml jsonschema
```

To check a `.pa.yaml` you are working on:

```bash
python scripts/pa_lint.py path/to/screen.pa.yaml
```

## Pull request checklist

- [ ] `python scripts/validate.py` passes
- [ ] `python -m unittest discover tests` passes
- [ ] Catalog changes cite a Studio version
- [ ] `CHANGELOG.md` updated under `## [Unreleased]`
- [ ] If behaviour changed, `plugin.json` `version` bumped (SemVer)

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By
participating you agree to uphold it.

## Licensing of contributions

By submitting a contribution you agree it is licensed under the repository's
[MIT License](LICENSE). Do not add third-party files without updating `NOTICE`.
