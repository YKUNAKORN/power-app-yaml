# power-app-yaml

A Claude **skill** that turns an HTML/CSS mockup or a UI screenshot into **Power Apps Canvas source
code** (`.pa.yaml`, source schema v3.0) that pastes straight into Power Apps Studio via
**"Paste code"** on a blank screen.

It exists because `.pa.yaml` looks like ordinary YAML but isn't: the schema is narrow and
version-pinned, and the control names don't follow web/HTML intuition (`Label` has no prefix but
`Classic/Button` does; `Icon` and `Classic/Icon` are different controls). Guessing an unconfirmed
control or property is the number-one cause of paste failures. This skill ships a catalog of what is
**confirmed to work** — built from real Studio paste tests, not analogy — and a set of copy-paste
templates so the model fills in blanks instead of inventing schema.

## Designed to run on a small / low-effort model

The instructions are written as an ordered workflow, lookup tables, fill-in templates, and a
pre-send checklist rather than prose you have to reason through. That means you can run it on a
lightweight/low-effort model and still get output that pastes cleanly, because the hard-won
specifics (which control, which version, which properties) are looked up, not derived.

## What's in here

```
power-app-yaml/
├── SKILL.md                          # the skill: workflow, control picker, templates, checklist
├── references/
│   ├── confirmed-controls.md         # the catalog — control types/properties proven in Studio
│   └── schema-v3.pa.yaml             # Microsoft's official pa.yaml v3.0 schema (see NOTICE)
└── assets/examples/
    ├── example-app-shell.yaml        # sidebar + top bar + page shell, with Navigate()
    ├── example-form.yaml             # multi-section form: TextInput + DropDown in cards
    └── example-card-grid.yaml        # selectable card/checklist grid with a footer
```

The three example screens are **real, working** `.pa.yaml` files (generic sample content) that
double as few-shot patterns — start from the closest one when building something similar.

## How to use it

1. Put the `power-app-yaml/` folder wherever your Claude setup loads skills from.
2. Give Claude an HTML mockup (e.g. a Google Stitch / v0 / Figma export) or a screenshot and ask it
   to "convert this to pa.yaml" / "make this a Power Apps screen".
3. Claude reads the catalog, picks the closest example, writes the full `.pa.yaml`, and hands it back.
4. In Power Apps Studio, on a **blank screen**, use **Paste code** and paste the whole file.
5. If Studio reports an error or warning, paste it back — the skill knows which codes block a paste
   (`PA1001` / `PA2108`) and which are harmless version warnings (`PA2105` / `PA2106`).

## Important: the catalog is empirical, so keep it honest

Everything in `references/confirmed-controls.md` was confirmed by pasting into a specific version of
Power Apps Studio. Studio pins control versions, so a newer Studio may emit different version numbers
(it will warn and auto-substitute). **When your own Studio confirms or corrects something, update your
copy of the catalog** — that's how the skill stays accurate for your environment. Anything not in the
catalog is treated as unverified by design; the skill will flag it and give you a small snippet to
paste-test on its own before trusting it.

## What it can't do (honestly)

Some CSS effects have no verified Power Fx equivalent: box shadows, `backdrop-blur`, CSS
transitions/animations, `group-hover`, and true one-sided borders. The skill will tell you plainly
and suggest the closest practical substitute (e.g. a thin `Rectangle` standing in for a left border)
rather than faking a property or silently dropping the requirement.

## Attribution

`references/schema-v3.pa.yaml` is a copy of Microsoft's official Power Apps `pa.yaml` **v3.0** schema,
from [`microsoft/PowerApps-Tooling`](https://github.com/microsoft/PowerApps-Tooling) (MIT-licensed,
© Microsoft Corporation). It is included unmodified for offline reference. See [`NOTICE`](NOTICE).

Further reading:
- Microsoft Docs — [Power Apps YAML](https://learn.microsoft.com/power-apps/maker/canvas-apps/power-apps-yaml)
- Schema source — [pa.schema.yaml](https://github.com/microsoft/PowerApps-Tooling/blob/master/schemas/pa-yaml/v3.0/pa.schema.yaml)

## License

MIT — see [`LICENSE`](LICENSE). (Fill in your name and the year in the license file before publishing.)

## Contributing

Found a control or property that Studio accepts (or rejects) that the catalog gets wrong? Open a PR
that updates `references/confirmed-controls.md`, and say which Studio version you tested on. Real test
results are the whole point.
