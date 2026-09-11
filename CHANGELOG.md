# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-09-11

Phase 4: make the skill useful on an app that already exists, and prepare -- without
assuming -- data binding and the modern layout controls.

### Added
- `scripts/app_inventory.py` -- a one-page summary of an app that already exists, so
  the export never has to be pasted into the conversation.
  - `python scripts/app_inventory.py SRC [--json] [--names] [--max-bytes N]`. SRC is a
    folder of `.pa.yaml`, a single file, or an `.msapp` (read in memory, `src/**/*.pa.yaml`
    only -- everything outside `src/` is build output and is ignored).
  - Reports: screens in `EditorState.ScreensOrder` order when the export has one and
    says so when it does not; per screen the controls and their nesting depth, never
    property values; the control types **with the `@version` that app uses**, which is
    what a new screen has to match; `Set`/`Collect`/`ClearCollect` targets from
    `App.OnStart` with the value when the value is a literal and `~expr` when it is not;
    `DataSources:` entries with their `Type:`; `ComponentDefinitions:` names; and a
    collision list of every screen and control name already taken.
  - **The byte budget is the feature.** The text summary is capped at 2048 bytes. Rather
    than overflow, the tool steps down a ladder of detail -- every control, then controls
    grouped by type, then bare names, then counts, then name prefixes -- and its last
    line states which level it used. The 10-screen, 171-control fixture in
    `tests/apps/ten-screen-app/` (96 KB of source) summarises in 1,807 bytes; the three
    bundled examples (270 controls) in 1,023. `--json` and `--names` are unbudgeted.
  - It never evaluates Power Fx. `Set(varUserEmail, User().Email)` is reported as
    `varUserEmail=~expr`, not as a guessed value -- a half-evaluated formula would be
    worse than no value.
- `skills/power-app-yaml/references/extend-existing-app.md` -- the procedure branch for
  a host app: get an export, run the inventory first, read the naming convention off it
  and match it, check every new name against the collision list, `Navigate()` only to
  screens the inventory lists, reuse the `App.OnStart` theme variables instead of
  re-hardcoding hex, and paste onto a **new blank** screen. Each step names the silent
  failure it prevents -- all six fail by succeeding, which is worse than `PA1001`.
- `skills/power-app-yaml/assets/test-snippets/` -- **the paste-test kit**: twelve
  single-control files covering Gallery, Form, DataTable, Toggle, DatePicker, ComboBox,
  Slider, Timer, CheckBox, HtmlText and the modern layout containers. Each is a complete
  `Screens:` wrapper with exactly one control, geometry above a bisect marker and the
  unverified properties below it, **one property per line** so a failure is bisected by
  deleting lines. Every file states where its property names came from, what the paste
  test is, and where to record the answer.
  - Property names are taken from Microsoft's published per-control reference (mirrored
    in `MicrosoftDocs/powerapps-docs`, retrieved 2026-09-11), so they are real Power Fx
    property names -- which is **not** the same as confirmed for a `.pa.yaml` paste, and
    each header says so.
  - No `@version` is written on the bare ids: this repo has no evidence for one, and an
    invented version number is the exact failure mode the project exists to prevent. The
    schema makes the version optional, so the bare id is legal to write.
  - Enum-valued properties are mostly left out on purpose -- `Format:
    =DateTimeFormat.ShortDate` stacks a guess about the enum member on a guess about the
    property name, so a failure would not say which half was wrong. Where an enum was
    unavoidable the header says so and suggests trying a plain number first.
- `docs/test-plan.md` -- the results worksheet: a row per snippet with Studio version,
  result, failing properties and date; a result-code table (`OK`, `OK/ver X`,
  `PA2108 <Prop>`, `PA1001`, `UNKNOWN-ID`, `OTHER`) chosen so each code implies a
  different next step; a suggested test order; and a paragraph on exactly what to write
  into `controls.yaml` and `confirmed-controls.md` for each outcome -- including that a
  property which failed goes to `properties_unverified` with the Studio version that
  rejected it, never to a "does not support" list.
- `skills/power-app-yaml/references/data-binding.md` -- SharePoint lists, `Gallery.Items`,
  `User().Email` filtering, two sites, `SubmitForm`, `Patch` and calling a Power Automate
  flow, every expression marked **UNVERIFIED** and every section naming the paste test it
  is blocked on. Three confidence markers are kept apart: SCHEMA-VERIFIED (checked here
  against the bundled schema, with the command to re-check), DOCUMENTED (in Microsoft's
  reference, never pasted here) and UNVERIFIED.
- `tests/apps/ten-screen-app/` -- a synthetic 10-screen, 171-control app with a
  deliberately non-alphabetical `EditorState.ScreensOrder`, literal and non-literal
  `App.OnStart` variables, three `DataSources:` entries and two components.
- `tests/test_app_inventory.py` -- 33 tests, including the acceptance criterion as an
  assertion (10-screen app under 2 KB), that the tier really is chosen by fit, that
  `ScreensOrder` is honoured and its absence admitted, that non-literal values are never
  guessed, that `--names` reaches controls three levels deep, and that an `.msapp`
  produces the same inventory as the unpacked folder.

### Changed
- **`SKILL.md` gains two branches and stays under its 8 KB budget** (8,169 bytes): "the
  app already exists" points at `app_inventory.py` + `extend-existing-app.md`, and
  "anything data-bound" at `data-binding.md` plus the matching test snippet. Paid for by
  trimming rationale prose that `README.md` already carries, not by dropping procedure.
  `scripts/validate.py` now also checks that these two pointers survive future shrinking.
- `scripts/validate.py` -- new checks, each one negative-tested: every test snippet
  carries the full header, parses, and contains **exactly one control** (two would make a
  failure unattributable); every snippet has no L0/L1 error **and raises at least one L2
  warning** (a snippet that lints clean is either catalogued already or the catalog moved
  under it); every snippet has a row in `docs/test-plan.md`; every `yaml`/`text` example
  in `data-binding.md` is marked UNVERIFIED, every snippet it names exists, and its YAML
  blocks are extracted and linted; and `app_inventory.py` is run against the 10-screen
  fixture with its output size asserted under 2 KB and its sections asserted present.
- `README.md` gains "Working with an app that already exists" and "The paste-test kit",
  and the repository layout covers the new files.
- `CONTRIBUTING.md` points a control test report at the ready-made snippet and at
  `docs/test-plan.md`.
- `plugin.json` version 0.4.0 -> 0.5.0.

### Not changed, on purpose
- **`controls.yaml` is byte-identical.** Not one of the twelve controls entered the
  catalog in this phase. They enter it when a real Studio result exists and not before,
  which is the entire point of shipping the kit instead of the entries.

### Known issues
- **The modern layout containers' type ids are unknown and are not guessed.** Microsoft's
  own first-party control-id enum (mirrored in `control-ids-candidate.yaml`) contains
  `GroupContainer` and contains no `Container`, `HorizontalContainer` or
  `VerticalContainer`; community-written Power Apps YAML material uses a bare
  `Container`. The two cannot both be right, so the kit ships both hypotheses with the
  unknown part as a clearly marked placeholder -- the `Variant:` string in
  `container-auto-layout-a-variant.pa.yaml`, the `Control:` id in
  `container-auto-layout-b-typeid.pa.yaml` -- and says plainly that the cheapest test is
  to insert a container in Studio and read its own code back, which settles the id, the
  version and the variant at once.
- The layout-property names in that snippet come from three sources of different
  strength, and the file says which is which: `LayoutDirection` and `LayoutAlignItems`
  are named verbatim in the prose of Microsoft's published Horizontal container
  reference; `LayoutMinWidth` and `FillPortions` appear in `microsoft/PowerApps-Tooling`
  issue #224, which describes an **older** source format; `LayoutGap`,
  `LayoutJustifyContent`, `LayoutWrap` and `LayoutOverflowY` are in common community use
  with no first-party citation found.
- **The bundled v3.0 schema's `DataSources` block has no SharePoint-shaped entry.**
  `Type` is an enum of exactly `Table` and `Actions`; the `Table` branch allows only
  `Parameters.TableLogicalName`, which is Dataverse vocabulary. `ConnectorId` is declared
  under `properties` and then rejected by both `oneOf` branches, which reads like an
  upstream bug. How Studio actually serialises a SharePoint list is unverified, and
  `data-binding.md` says to read it off a real export rather than infer it.
- Whether "Paste code" accepts a file carrying a top-level `DataSources:` block at all --
  as opposed to ignoring it or refusing the paste -- is untested. `data-binding.md` takes
  the conservative reading that connections are a manual Studio step.
- Every expression in `data-binding.md` remains UNVERIFIED, and all twelve rows of
  `docs/test-plan.md` are empty. Nothing in this phase was confirmed against Studio,
  because nothing in this phase could be.

## [0.4.0] - 2026-09-11

Phase 3: cut what the skill costs to run, and give it a real algorithm for the
hardest part of the job — turning HTML/CSS into absolute X/Y.

### Added
- `skills/power-app-yaml/assets/patterns/` — 13 pattern snippets, each a standalone
  `.pa.yaml` that lints **SAFE TO PASTE**, each opening with a header naming what it
  is, which controls it uses, the example file and **line range** it was extracted
  from, and its evidence level: `screen-shell`, `sidebar-nav-item`, `top-bar`,
  `card-container`, `section-header`, `form-field-text`, `form-field-dropdown`,
  `tile-grid-cell`, `badge`, `divider`, `avatar-row`, `footer-nav`,
  `two-column-split`. Every one is **extracted** from the three bundled examples, not
  invented; the headers cite the source lines so any claim is re-checkable.
  - `radio-group` was requested and is **not included**: no bundled example contains a
    `Classic/Radio`, so there was nothing to extract. `empty-state` likewise — no
    example has an empty/zero-results region.
  - `divider` carries an explicit HONEST SCOPE note: the thin-`Rectangle` *mechanism*
    is extracted verbatim (`recDot1`, 48 × 4; `recNavActiveIndicator`, 4 × 48) but the
    *role* of a full-width section rule has no precedent in any example.
- `skills/power-app-yaml/assets/examples/INDEX.md` — per example: a one-paragraph
  description, a control inventory with counts, and the line ranges of every notable
  region, mapped to the pattern that covers it. Lets a 40-line slice be read instead of
  a 1,732-line file. Plus a cross-file table for the sidebar / top bar / progress
  regions that repeat in all three.
- `skills/power-app-yaml/references/layout-mapping.md` — the geometry reference.
  Canvas sizing and the scale factor (with the rounding rule and the row-closing
  check); Tailwind→px tables for spacing, text sizes and line heights, font weights,
  `rounded-*` and border widths, each under a standing warning that they are Tailwind
  **defaults** and the mockup's own config wins; flex row/column → cumulative
  coordinates covering every `justify-*` and `items-*` and `flex-1`; grid → column
  width math with gutters, residue handling and `col-span`; the nesting arithmetic
  (not just the rule); vertical overflow → how to compute the screen's `Height`; and a
  fully worked 3-column `gap-6` `p-8` card grid from a 1440px mockup down to the exact
  `X`/`Y`/`Width`/`Height` of every control, with the arithmetic shown at each step.
  - **The 1366 × 768 canvas assumption is labelled.** It is *sourced* from the bundled
    examples' own geometry (top bar `X: =280` + `Width: =1086` = 1366; sidebar
    `Height: =768`). The separate claim that this is Power Apps' *documented default*
    for a tablet-format app is marked **UNVERIFIED** — no citation exists in this repo
    — with an instruction to confirm it from Studio → Settings → Display.
  - Nothing in the file recommends a property absent from `controls.yaml`, and
    `scripts/validate.py` now enforces that mechanically.
- `confirmed-controls.md` gains a "Linter warnings about a control type" section: the
  `L2.unverified-control-type` / `L2.candidate-control-type` table moved out of
  SKILL.md, where it was costing context on every invocation.
- `README.md` gains "How the skill spends its context" — the per-file read budget, why
  the pattern library exists, and why `layout-mapping.md` exists. This is the rationale
  prose moved out of SKILL.md.

### Changed
- **`SKILL.md` rewritten: 14,371 → 7,987 bytes, under the 8 KB budget.** It is now
  procedure only — workflow, control picker, templates, rules, defaults, hand-off,
  checklist. The new step order is: read the catalog → pick the pattern(s) → apply
  `layout-mapping.md` → open a full example *only* if the patterns don't cover it, and
  then only a slice via `INDEX.md` → write → **lint** → hand off. "Why a whole skill
  for just YAML" and the design philosophy moved to `README.md`.
- **Frontmatter `description` tightened 917 → 642 characters with every trigger phrase
  kept** (HTML/CSS mockup, Google Stitch, v0, Figma export, UI screenshot, design
  export, `.pa.yaml`, source schema v3.0, "Paste code", blank screen, Power Apps Studio,
  "convert this to pa.yaml", "make this a Power Apps screen", "turn this design into
  code I can paste into Power Apps", "even without the term .pa.yaml", fix, debug, failed
  to paste, `PA1001`, `PA2108`, add a new screen to an existing app, extend a screen made
  this way). The only thing cut is the closing justification sentence — "carries a catalog
  of control types and properties that are confirmed to work versus merely guessed — the
  #1 cause of paste failures" — which sells the skill rather than triggering it; the rest
  of the saving is wording. "wireframe" was added: it appears in README's audience list
  and was the one plausible trigger the description lacked.
- `scripts/validate.py` — new checks: every `assets/patterns/*.pa.yaml` lints with
  verdict SAFE TO PASTE (not merely exit 0); every pattern header carries
  PATTERN/What/Controls/Source/Evidence **and cites a real bundled example**; pattern
  line counts stay in budget (`tile-grid-cell` is a declared exception at 90, being a
  six-control composite); SKILL.md stays under `SKILL_MD_MAX_BYTES` **and** still
  contains the workflow, picker, templates, rules and checklist plus its pointers; the
  frontmatter description stays under `DESCRIPTION_MAX_CHARS`; `layout-mapping.md` and
  `SKILL.md` name no property absent from `controls.yaml`; and the worked example's
  YAML block is extracted and linted on every run, so it cannot drift.
- `plugin.json` version 0.3.0 → 0.4.0.

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

[Unreleased]: https://github.com/YKUNAKORN/power-app-yaml/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/YKUNAKORN/power-app-yaml/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/YKUNAKORN/power-app-yaml/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/YKUNAKORN/power-app-yaml/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/YKUNAKORN/power-app-yaml/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/YKUNAKORN/power-app-yaml/releases/tag/v0.1.0
