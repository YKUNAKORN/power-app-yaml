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
- [Install](#install)
- [Use it](#use-it)
- [Repository layout](#repository-layout)
- [Keep the catalog honest](#keep-the-catalog-honest)
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
2. Claude reads the catalog, picks the closest example, writes the full `.pa.yaml`, and hands it back.
3. In Power Apps Studio, on a **blank screen**, use **Paste code** and paste the whole file.
4. If Studio reports an error or warning, paste it back. Which codes block a paste (`PA1001` /
   `PA2108`) and which are harmless version warnings (`PA2105` / `PA2106`) is covered in
   [`docs/troubleshooting.md`](docs/troubleshooting.md).

## Repository layout

```
power-app-yaml/
├── skills/power-app-yaml/            # the skill itself
│   ├── SKILL.md                      # workflow, control picker, templates, checklist
│   ├── references/
│   │   ├── confirmed-controls.md     # the catalog — control types/properties proven in Studio
│   │   └── schema-v3.pa.yaml         # Microsoft's official pa.yaml v3.0 schema (see NOTICE)
│   └── assets/examples/
│       ├── example-app-shell.yaml    # sidebar + top bar + page shell, with Navigate()
│       ├── example-form.yaml         # multi-section form: TextInput + DropDown in cards
│       └── example-card-grid.yaml    # selectable card/checklist grid with a footer
├── .claude-plugin/                   # plugin + marketplace manifests
├── docs/                             # quickstart, troubleshooting
├── scripts/validate.py              # repo sanity checks (run before a PR)
└── .github/                          # issue / PR templates, CI
```

The three example screens are **real, working** `.pa.yaml` files (generic sample content) that
double as few-shot patterns — start from the closest one when building something similar.

## Keep the catalog honest

Everything in `skills/power-app-yaml/references/confirmed-controls.md` was confirmed by pasting into a
specific version of Power Apps Studio. Studio pins control versions, so a newer Studio may emit
different version numbers (it will warn and auto-substitute). **When your own Studio confirms or
corrects something, update your copy of the catalog** — and, ideally,
[report it](https://github.com/YKUNAKORN/power-app-yaml/issues/new?template=control-report.yml) so
everyone benefits. Anything not in the catalog is treated as unverified by design.

## What it can't do (honestly)

Some CSS effects have no verified Power Fx equivalent: box shadows, `backdrop-blur`, CSS
transitions/animations, `group-hover`, and true one-sided borders. The skill will tell you plainly
and suggest the closest practical substitute (e.g. a thin `Rectangle` for a left border) rather than
faking a property or silently dropping the requirement.

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
