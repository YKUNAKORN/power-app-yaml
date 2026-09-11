# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-09-10

### Added
- `scripts/harvest_controls.py` — grows the control catalog from real Power Apps Studio
  exports instead of one hand-fed paste test at a time.
  - Reads a `.pa.yaml` file, a folder of them, or an `.msapp` (unzipped in memory,
    `src/**/*.pa.yaml` only). Walks `Screens:` and `ComponentDefinitions:` recursively
    through nested `Children:`.
  - Records per control type: version, `Variant`, whether `Children` was seen, every
    property name observed, occurrence count, and the source files.
  - Emits a `controls.yaml` fragment with `evidence: studio-export` and
    `source: "<file> (harvested <date>)"`.
  - `--merge` folds the fragment into `controls.yaml` **as text**, so every comment in
    the file survives: it adds new controls, unions new property names into
    `properties_confirmed` (keeping the hand-written order, with a `# harvested <date>`
    provenance comment), and never overwrites a hand-written `notes`, never downgrades a
    `studio-tested` entry, and never removes anything. Conflicts — same control at a
    different version, a mismatched `Variant`, `Children` the catalog says cannot exist,
    a control id with no `@version` — are reported and left alone; the run exits 2.
    A merge with nothing to change does not write the file at all.
  - `--report` prints a coverage diff in both directions, `--out` writes the fragment,
    `--dry-run` reports a merge without performing it.
- `docs/harvesting.md` — both extraction routes (Power Platform CLI and manual `.msapp`
  unzip) with exact flags, where `src/` lives, how to run the harvester, a checklist for
  reviewing a merge diff before committing, and how to report a result upstream through
  the `control-report.yml` issue template.
- `skills/power-app-yaml/references/control-ids-candidate.yaml` — Microsoft's 62-entry
  first-party control-id enum, mirrored from `microsoft/PowerApps-Tooling`
  (`src/schemas/pa-yaml/v3.0/ControlLibraryVDev/ControlTypeId-1P-controls-enum.schema.yaml`
  @ `aed72a3`, 2026-08-24). **Every entry is marked `evidence: unverified`** and
  `scripts/validate.py` fails if one is not.
- `scripts/pa_lint.py`: new L2 check `L2.candidate-control-type`. A control type absent
  from the catalog but present in that enum now reads "known to Microsoft's tooling but
  not yet paste-tested here" instead of "unknown control". Same WARNING severity, same
  `# UNVERIFIED` tagging requirement, same generated paste-test snippet — the enum is a
  wording aid, never evidence. New `--candidates PATH` flag; a missing file degrades to
  the old wording rather than failing.
- `scripts/validate.py`: checks for the harvester, `docs/harvesting.md`, the candidate
  file's provenance keys and its all-`unverified` invariant, and a new catalog rule that
  a control cannot be both catalogued and listed in `unattempted_controls`.
- `tests/test_harvest_controls.py` — 21 tests covering the acceptance criteria directly
  (the bundled examples reproduce the 8 catalogued control types with zero conflicts; a
  merge against an unchanged catalog is byte-identical; comments, `notes` and evidence
  levels survive a real merge; conflicts exit 2 and change nothing), plus `.msapp`
  reading and the absence-caveat invariants.
- `tests/fixtures/invalid/candidate-control-type.*` — fixture for the new L2 check.

### Changed
- `controls.yaml` now opens with **THE ABSENCE CAVEAT** as a prominent top-level comment:
  Studio only serialises properties whose value differs from the default (Microsoft's own
  wording), so a property missing from an export — or from this catalog — is not evidence
  that the control lacks it. The harvester enforces the same rule mechanically: it never
  writes `properties_unverified`, never emits a "does not support" list, and labels its
  "never exercised by this export" report section as untested, not unsupported.
- `SKILL.md`, `README.md` and `CONTRIBUTING.md` document the harvesting route and the
  two control-type warnings the linter can now raise.
- `plugin.json` version 0.2.0 → 0.3.0.

### Known issues
- The Power Platform CLI route (`pac canvas list` / `pac canvas download -d`) is
  **documented from Microsoft's reference but not verified against a real tenant** by
  this repo. `docs/harvesting.md` says so at the top of that section, and the manual
  `.msapp` unzip route is a complete substitute that needs no CLI.
- The mirrored control-id enum disagrees with this repo's own Studio tests about the
  `Classic/` prefix: it lists bare `Button`, `TextInput`, `DropDown` and `Radio`, while
  `controls.yaml` records `Classic/Button@2.2.0`, `Classic/TextInput@2.3.2`,
  `Classic/DropDown@2.3.1` and `Classic/Radio@2.3.0` from paste tests. Unresolved, and
  recorded in `docs/harvesting.md`; it is one of the reasons nothing in that file is
  treated as evidence.
- Harvesting `assets/examples/` surfaces `FontWeight` on `Classic/Button` as *held back*:
  the examples use it, but `controls.yaml` explicitly flags it unverified there. The
  merge will not promote it. Still needs the Studio paste test noted in 0.2.0.

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
- Linting the bundled examples surfaces 22 pre-existing warnings and 0 errors: 12
  `Navigate()` calls to screens outside their own single-screen file, 5 uses of
  `FontWeight` on `Classic/Button` that contradict the catalog's explicit "not verified
  on Button" note, and the 5 untagged-item warnings that follow from those. Left as-is
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
