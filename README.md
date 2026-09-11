# power-app-yaml

[![validate](https://github.com/YKUNAKORN/power-app-yaml/actions/workflows/validate.yml/badge.svg)](https://github.com/YKUNAKORN/power-app-yaml/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude skill](https://img.shields.io/badge/Claude-skill-8A2BE2)](skills/power-app-yaml/SKILL.md)

A Claude **skill** that turns an HTML/CSS mockup or a UI screenshot into **Power Apps Canvas
source code** (`.pa.yaml`, source schema v3.0) that pastes straight into Power Apps Studio via
**"Paste code"** on a blank screen.

It exists because `.pa.yaml` looks like ordinary YAML but isn't: the schema is narrow and
version-pinned, and the control names don't follow web/HTML intuition (`Label` has no prefix but
`Classic/Button` does; `Icon` and `Classic/Icon` are different controls). Guessing an unconfirmed
control or property is the number-one cause of paste failures. This skill ships a catalog of what is
**confirmed to work** — built from real Studio paste tests, not analogy — and a set of copy-paste
templates so the model fills in blanks instead of inventing schema.

## Who it's for

- Makers turning a **Figma, v0, or Google Stitch export** into a Power Apps Canvas screen
- Anyone with a **screenshot or wireframe** who wants paste-ready `.pa.yaml` instead of rebuilding by hand
- Devs migrating an **HTML/CSS mockup to Power Fx** and hitting the `.pa.yaml` schema's quirks
- People stuck on a **Power Apps "Paste code" error** (`PA1001` / `PA2108`) who need to know what actually broke

## Table of contents

- [Who it's for](#who-its-for)
- [Why a skill for "just YAML"](#why-a-skill-for-just-yaml)
- [Designed to run on a small model](#designed-to-run-on-a-small-model)
- [How the skill spends its context](#how-the-skill-spends-its-context)
- [Install](#install)
- [Use it](#use-it)
- [Repository layout](#repository-layout)
- [Verify before you paste](#verify-before-you-paste)
- [Working with an app that already exists](#working-with-an-app-that-already-exists)
- [The paste-test kit](#the-paste-test-kit)
- [Keep the catalog honest](#keep-the-catalog-honest)
- [Telling better output from worse](#telling-better-output-from-worse)
- [What it can't do (honestly)](#what-it-cant-do-honestly)
- [Contributing](#contributing)
- [Attribution](#attribution)
- [License](#license)

## Why a skill for "just YAML"

`.pa.yaml` is narrow, version-pinned, and full of naming quirks you cannot derive from web intuition:

- `Label` has **no** prefix, but `Classic/Button` has a `Classic/` prefix.
- `Icon` and `Classic/Icon` are **different controls** with different capabilities.
- Every property value must start with `=`, and commas inside `RGBA(...)` break flow-style YAML.

The method is: **use only what's confirmed, label every guess honestly, and let the user paste-test
small pieces before trusting them.**

## Designed to run on a small model

The instructions are an ordered workflow, lookup tables, fill-in templates, and a pre-send checklist
rather than prose you have to reason through. You can run it on a lightweight/low-effort model and
still get output that pastes cleanly, because the hard-won specifics (which control, which version,
which properties) are looked up, not derived.

## How the skill spends its context

`SKILL.md` is procedure only — workflow, control picker, templates, rules, checklist —
and it is kept under 8 KB on purpose. Everything else is loaded on demand, cheapest
first:

| Read | Size | When |
|---|---|---|
| `references/controls.yaml` | ~10 KB | Always. The catalog of what works. |
| `assets/patterns/*.pa.yaml` | 30–85 lines each | Always. Pick only the patterns the mockup needs. |
| `references/layout-mapping.md` | ~26 KB | Whenever geometry has to be derived from HTML/CSS. |
| `assets/examples/INDEX.md` | ~7 KB | To find a line range before opening an example. |
| `assets/examples/*.yaml` | 3,234 lines total | Last resort, and as a slice, never whole. |

The reason for the pattern library: `example-card-grid.yaml` is 1,732 lines, and the
pattern actually worth learning from it lives in about 85 of them — the other 95% is the
same card repeated 16 more times. Reading the catalog *and* the nearest example in full
used to cost roughly 20k tokens before the first line of output. The patterns are
extracted from those same example files (each one cites its source file, line range and
evidence level), so they are not a second source of truth — they are the same evidence,
addressable in 40 lines instead of 1,700.

`layout-mapping.md` exists because turning flex/grid/Tailwind into absolute
`X`/`Y`/`Width`/`Height` is the step a model is most likely to fake. There is no
confirmed flex, grid, gap or padding property in Power Apps canvas YAML, so the geometry
has to be resolved into numbers by arithmetic, once, at authoring time.

## Install

### As a Claude Code plugin (recommended)

```bash
/plugin marketplace add YKUNAKORN/power-app-yaml
/plugin install power-app-yaml@power-app-yaml
```

### As a plain skill folder

Copy **`skills/power-app-yaml/`** (the folder containing `SKILL.md`) into wherever your Claude setup
loads skills from.

Full walkthrough: [`docs/quickstart.md`](docs/quickstart.md).

## Use it

1. Give Claude an HTML mockup (Google Stitch / v0 / Figma export) or a screenshot and ask it to
   "convert this to pa.yaml".
2. Claude reads the catalog, picks the matching patterns, derives the coordinates, writes
   the full `.pa.yaml`, **lints it offline** (`scripts/pa_lint.py`), and hands it back with
   the verdict and any unverified items spelled out.
3. In Power Apps Studio, on a **blank screen**, use **Paste code** and paste the whole file.
   If the hand-off came with isolated paste-test snippets, paste those on a scratch screen
   first — a one-control file fails in a way you can attribute.
4. If Studio reports an error or warning, paste it back. Which codes block a paste (`PA1001` /
   `PA2108`), which are harmless version warnings (`PA2105` / `PA2106`), and what each of the
   linter's four verdict lines means are covered in
   [`docs/troubleshooting.md`](docs/troubleshooting.md).

Full walkthrough with the lint step: [`docs/quickstart.md`](docs/quickstart.md).

## Repository layout

```
power-app-yaml/
├── skills/power-app-yaml/            # the skill itself
│   ├── SKILL.md                      # workflow, control picker, templates, checklist
│   ├── references/
│   │   ├── controls.yaml             # the catalog, machine-readable — source of truth
│   │   ├── confirmed-controls.md     # the same catalog, human-readable
│   │   ├── layout-mapping.md         # HTML/CSS geometry → absolute X/Y/Width/Height
│   │   ├── extend-existing-app.md    # the branch for adding a screen to an app that exists
│   │   ├── data-binding.md           # SharePoint / Gallery / Patch / forms — all UNVERIFIED
│   │   ├── control-ids-candidate.yaml  # Microsoft's control-id enum, mirrored — all unverified
│   │   └── schema-v3.pa.yaml         # Microsoft's official pa.yaml v3.0 schema (see NOTICE)
│   └── assets/
│       ├── patterns/                 # 13 small extracted snippets, all lint-clean
│       ├── test-snippets/            # 12 one-control paste tests for UNVERIFIED controls
│       └── examples/
│           ├── INDEX.md              # per-example description, control counts, line ranges
│           ├── example-app-shell.yaml    # sidebar + top bar + page shell, with Navigate()
│           ├── example-form.yaml         # multi-section form: TextInput + DropDown in cards
│           └── example-card-grid.yaml    # selectable card/checklist grid with a footer
├── .claude-plugin/                   # plugin + marketplace manifests
├── docs/                             # quickstart, troubleshooting, harvesting, test plan, evals
├── scripts/
│   ├── pa_lint.py                    # offline .pa.yaml verifier (L0-L3) — run before handing a file over
│   ├── run_eval.py                   # score a produced .pa.yaml against an eval case
│   ├── app_inventory.py              # one-page summary of an existing app (.pa.yaml folder / .msapp)
│   ├── harvest_controls.py           # grow the catalog from real Studio exports (.pa.yaml / .msapp)
│   └── validate.py                   # repo sanity checks (run before a PR)
├── tests/
│   ├── fixtures/                     # linter fixtures with .expected.json sidecars
│   ├── apps/ten-screen-app/          # synthetic 171-control app, for app_inventory.py
│   ├── evals/                        # 5 eval cases: mockup.html + expectations.yaml + notes.md
│   └── test_*.py                     # the unittest suite
└── .github/                          # issue / PR templates, CI
```

The three example screens are **real, working** `.pa.yaml` files (generic sample content).
`assets/patterns/` holds the reusable pieces extracted from them — start there, and drop
to an example slice only when a pattern doesn't cover the case.

## Verify before you paste

`scripts/pa_lint.py` is the step that stops the user acting as the compiler. It runs
offline, in four layers, and ends in a verdict:

```bash
python scripts/pa_lint.py myscreen.pa.yaml
```

| Layer | Severity | Checks | Studio equivalent |
|---|---|---|---|
| **L0** | error | the file parses as YAML | a paste that silently does nothing |
| **L1** | error | Microsoft's bundled v3.0 schema | `PA1001` — blocks the whole paste |
| **L2** | warning | this repo's control catalog | `PA2108` — unknown control or property |
| **L3** | warning | SKILL.md's own conventions | **nothing** |

L3 is the layer with no Studio counterpart, and it is where the expensive failures
live: a duplicate control name is silently renamed to `_1` on paste, so the names you
wrote and the names in the app quietly diverge. Nothing errors. The app is just wrong.

Four verdicts are possible — `SAFE TO PASTE`, `PASTES, BUT n UNVERIFIED ITEM(S)`,
`WILL FAIL`, and `UNPROVEN` (which is what you get when `jsonschema` is not installed
and the layer that catches `PA1001` never ran; reporting "safe" there would be a claim
the run cannot back up). Each one, and what to do about it, is in
[`docs/troubleshooting.md`](docs/troubleshooting.md#the-linters-verdict-lines).

The linter is an approximation of Studio, built from the bundled schema and a catalog
of paste-tested controls. Where the two disagree, Studio is right — and that
disagreement is worth reporting, because it is how the catalog grows.

## Working with an app that already exists

Adding a screen to a real app fails in ways a blank canvas cannot: a control name that
collides is silently renamed to `_1`, a `Navigate()` goes to a screen that was never
there, and the palette gets hard-coded a second time next to the theme variables
`App.OnStart` already defines. All three are silent — the paste succeeds and the app is
subtly wrong.

```bash
python scripts/app_inventory.py <Src-folder-or-.msapp>
```

About a page: screens in editor order, controls per screen with nesting depth, the
control types **with the versions that app uses**, the `App.OnStart` variables with
their literal values, the `DataSources:` entries, the components, and every name already
taken. The export itself is tens of thousands of tokens of property values nobody is
going to read, so the tool has a hard byte budget and drops to coarser detail rather
than overflowing it; `--json` and `--names` are the unbudgeted escape hatches. The
procedure that uses it is
[`references/extend-existing-app.md`](skills/power-app-yaml/references/extend-existing-app.md).

## The paste-test kit

Gallery, Form, DataTable, Toggle, DatePicker, ComboBox, Slider, Timer, CheckBox,
HtmlText and the modern layout containers are **not** in the catalog, and this repo has
no evidence about any of them. Guessing is what the project exists to avoid, so instead
[`assets/test-snippets/`](skills/power-app-yaml/assets/test-snippets/) holds one
single-control file per control, each a complete `Screens:` wrapper with one property per
line so a failure can be bisected by deleting lines. Results go in
[`docs/test-plan.md`](docs/test-plan.md), and only a real Studio result puts a control in
the catalog.

The layout containers are the honest gap: Microsoft's own control-id enum lists
`GroupContainer` and no `Container` / `HorizontalContainer` / `VerticalContainer`, while
community guides use a bare `Container`. Rather than pick one, the kit ships both
hypotheses with the unknown part marked as a placeholder, and says the cheapest test is
to insert a container in Studio and read its own code back.

## Keep the catalog honest

Everything in `skills/power-app-yaml/references/confirmed-controls.md` was confirmed by pasting into a
specific version of Power Apps Studio. Studio pins control versions, so a newer Studio may emit
different version numbers (it will warn and auto-substitute). **When your own Studio confirms or
corrects something, update your copy of the catalog** — and, ideally,
[report it](https://github.com/YKUNAKORN/power-app-yaml/issues/new?template=control-report.yml) so
everyone benefits. Anything not in the catalog is treated as unverified by design.

**Grow the catalog from a real export.** If you can download your app's source — `pac canvas
download -d <dir>`, or just unzip the `.msapp` — the `.pa.yaml` files under `src/` are Studio's own
output, and `scripts/harvest_controls.py` turns them into catalog entries:

```bash
python scripts/harvest_controls.py ./myapp/src --report   # what's new, what's untested
python scripts/harvest_controls.py ./myapp/src --merge    # fold it in, then review the diff
```

One caveat governs all of it, and Microsoft documents it: *only properties that differ from the
default values are serialized.* **A property missing from an export is not evidence that the
control lacks it** — so the harvester only ever makes positive claims, and never writes a "does not
support" list. Full walkthrough, both extraction routes, and the review checklist:
[`docs/harvesting.md`](docs/harvesting.md).

## Telling better output from worse

The linter proves a file will paste. It cannot tell you whether the screen is the one
the mockup showed, and it cannot tell you whether an edit to `SKILL.md` helped or hurt.
[`tests/evals/`](tests/evals/) and `scripts/run_eval.py` are the part that can.

Five cases, each a small self-contained `mockup.html`, an `expectations.yaml` of
mechanically checkable assertions, and a `notes.md` saying what the case is meant to
stress: **app shell**, **multi-section form**, **card grid**, **mixed shell + form**,
and a deliberately hard one built entirely from effects listed under `impossible_css`
— which has no right conversion, only a right disclosure.

```bash
python scripts/run_eval.py out.pa.yaml --case tests/evals/app-shell
```

**The boundary is the important part.** This scores a `.pa.yaml` that already exists.
Producing that file means running a model, and CI does not run a model — there is
deliberately no API-key step in the scorer and none in the workflow, because a harness
that quietly depended on a key would be green on every run where the key was missing.
So the loop is manual and has three steps: ask Claude for a case's mockup, save the
answer, run the scorer. The whole procedure, including what the harness *cannot* see,
is in [`docs/evals.md`](docs/evals.md).

What CI does run is the half that needs no model: `python scripts/run_eval.py` with no
arguments scores the three bundled example screens against their matching cases. That
proves the scorer works. It proves nothing about the skill — the examples were written
by hand, not generated — and the tool says so on every run.

## What it can't do (honestly)

Some CSS effects have no verified Power Fx equivalent: box shadows, `backdrop-blur`, CSS
transitions/animations, `group-hover`, true one-sided borders, and any non-`Segoe UI` font. The
full list is `impossible_css` in
[`controls.yaml`](skills/power-app-yaml/references/controls.yaml). The skill will tell you plainly
and suggest the closest practical substitute (e.g. a thin `Rectangle` for a left border) rather than
faking a property or silently dropping the requirement — and the `impossible-effects` eval case
exists to check that it actually does.

Beyond that: nothing here renders anything, so colours, fonts and visual hierarchy are
never verified automatically; and the linter is an approximation of Studio, not Studio.
Only a real paste test settles a control.

## Contributing

The most valuable contribution is a real Studio test result. See
[`CONTRIBUTING.md`](CONTRIBUTING.md), and please follow the
[Code of Conduct](CODE_OF_CONDUCT.md). Security issues: [`SECURITY.md`](SECURITY.md).

## Attribution

`skills/power-app-yaml/references/schema-v3.pa.yaml` is a copy of Microsoft's official Power Apps
`pa.yaml` **v3.0** schema, from
[`microsoft/PowerApps-Tooling`](https://github.com/microsoft/PowerApps-Tooling) (MIT-licensed,
© Microsoft Corporation). It is included unmodified for offline reference. See [`NOTICE`](NOTICE).

Further reading:

- Microsoft Docs — [Power Apps YAML](https://learn.microsoft.com/power-apps/maker/canvas-apps/power-apps-yaml)
- Schema source — [pa.schema.yaml](https://github.com/microsoft/PowerApps-Tooling/blob/master/schemas/pa-yaml/v3.0/pa.schema.yaml)

## License

MIT — see [`LICENSE`](LICENSE). The bundled Microsoft schema is covered separately; see
[`NOTICE`](NOTICE).
