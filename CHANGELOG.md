# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-09-10

### Added
- `skills/power-app-yaml/references/controls.yaml` — machine-readable control catalog,
  now the single source of truth. `confirmed-controls.md` is the human-readable view of
  the same facts; `scripts/validate.py` fails if the two drift apart.
- `scripts/pa_lint.py` — an offline verification loop that proves a `.pa.yaml` before it
  reaches the user, instead of the user acting as the compiler:
  - **L0** YAML parse, with line/column and a special case for flow-style `Properties`
    containing `RGBA(...)`.
  - **L1** JSON Schema against the bundled Microsoft v3.0 schema (ERROR, maps to
    `PA1001`), with raw `jsonschema` messages translated into human sentences carrying a
    YAML path.
  - **L2** catalog lint (WARNING, maps to `PA2108`) for unverified control types and
    properties, each shipping a generated isolated paste-test snippet.
  - **L3** convention checks from SKILL.md's own rules: unreachable `Navigate()` targets,
    duplicate control names, child `X`/`Y` under a non-`ManualLayout` container, and
    untagged unverified items.
- `tests/` — 14 fixtures with `.expected.json` sidecars and a stdlib `unittest` suite
  asserting on check ids rather than message wording.
- CI now installs `jsonschema` and runs `python -m unittest discover tests`.

### Changed
- `SKILL.md`: running `scripts/pa_lint.py` is now a mandatory workflow step before
  handing a file over, and appears in the pre-send checklist.

### Known issues
- `controls.yaml` records `studio_version_tested: unknown` — `confirmed-controls.md`
  names no Studio build, so no honest value exists yet.
- Linting the bundled examples surfaces 22 pre-existing warnings (0 errors): 11
  `Navigate()` calls to screens outside their own single-screen file, 5 uses of
  `FontWeight` on `Classic/Button` that contradict the catalog's explicit "not verified
  on Button" note, and the 6 untagged-item warnings that follow from them. Left as-is
  because the example files are out of scope for this phase.

## [0.1.0] - 2026-08-27

### Added
- Initial public release of the `power-app-yaml` Claude skill.
- Workflow, control picker, fill-in templates, and pre-send checklist in
  `skills/power-app-yaml/SKILL.md`.
- Empirical control catalog `skills/power-app-yaml/references/confirmed-controls.md`,
  built from real Power Apps Studio paste tests.
- Bundled Microsoft `pa.yaml` v3.0 schema for offline reference (see `NOTICE`).
- Three real, paste-tested example screens under
  `skills/power-app-yaml/assets/examples/` (app shell, form, card grid).
- Claude Code plugin packaging: `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json`.
- Repository documentation: `README`, `docs/quickstart.md`,
  `docs/troubleshooting.md`.
- Community health files: `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`,
  `SUPPORT`, GitHub issue/PR templates.
- CI: `scripts/validate.py` and `.github/workflows/validate.yml`.

[Unreleased]: https://github.com/YKUNAKORN/power-app-yaml/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/YKUNAKORN/power-app-yaml/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/YKUNAKORN/power-app-yaml/releases/tag/v0.1.0
