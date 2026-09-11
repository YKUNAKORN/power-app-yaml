# Paste-test snippets

Twelve single-control files, each a complete `Screens:` wrapper you can paste onto a
blank screen in Power Apps Studio. **Nothing here is confirmed.** The whole point of
the kit is that only the person with Studio open can confirm it, and these files exist
to make that as cheap as possible.

Results go in [`docs/test-plan.md`](../../../../docs/test-plan.md). Only after a real
result does a control enter [`controls.yaml`](../../references/controls.yaml).

## How to use one

1. Open Power Apps Studio, add a **blank** screen.
2. Copy the whole file, right-click the screen → **Paste code**.
3. Read what Studio says.
   - Pasted with no message → **everything in that file works**, including every
     property. Record it.
   - `PA2108` naming a property → that property does not exist on that control at that
     version. Everything else may still be fine: delete that one line and paste again.
   - `PA1001` or "unknown control" → the control **type id** is wrong. Stop bisecting
     properties; the id is the problem.
   - `PA2105` / `PA2106` → a version warning, not an error. Studio substitutes the
     current version and the paste still applies. Record the version it chose.
4. If it failed, delete **one line** below the `# -- UNVERIFIED below here --` marker
   and paste again. Repeat. The last line you deleted is the culprit.

Every property sits on its own line specifically so step 4 is a line delete.

## The layout containers: I do not know their type ids

`Container`, `Horizontal container` and `Vertical container` are the one gap this kit
cannot even guess at honestly, so it does not:

- Microsoft's own first-party control-id enum — 62 ids, mirrored in
  [`control-ids-candidate.yaml`](../../references/control-ids-candidate.yaml) — contains
  `GroupContainer` and contains **no** `Container`, `HorizontalContainer` or
  `VerticalContainer`.
- Community-written Power Apps YAML guides use a bare `Container`.
- This repo's own Studio test recorded `GroupContainer@1.5.0` with
  `Variant: ManualLayout`, which suggests the auto-layout containers are the same type
  with a different `Variant` — but "suggests" is not "is".

So the kit ships both hypotheses, each with the unknown part marked as a placeholder:

| File | Hypothesis | Placeholder |
|---|---|---|
| `container-auto-layout-a-variant.pa.yaml` | `GroupContainer@1.5.0` + a non-`ManualLayout` `Variant` | the `Variant:` string |
| `container-auto-layout-b-typeid.pa.yaml` | its own control type id | the `Control:` id |

**The cheapest test is not a paste at all.** Insert a Vertical container from the
Studio toolbar, select it, and read its own code back (`+ Insert → Layout → Vertical
container`, then copy the control's code). That settles the type id, the `@version`
and the `Variant` in one go, and answers both hypotheses at once. Do that first.

## Why no `@version` on most of these

This repo has no evidence for the version of any of these controls, and an invented
version number is exactly the guess the project exists to prevent. The pa.yaml v3.0
schema makes `@major.minor.patch` optional, so the bare id is legal to write. If Studio
rejects a bare id, the read-back trick above supplies the real one.

## Where the property names came from

Property names are taken from Microsoft's published control reference, mirrored in
`MicrosoftDocs/powerapps-docs` (retrieved 2026-09-11) — one page per control. That
makes them real property names for the control **in Power Fx**. It does **not** make
them confirmed for a `.pa.yaml` paste: the docs describe the Studio property panel, the
casing in YAML is a separate question, and the version this repo would write is
unknown. Each file's header says which of its names came from where.

Enum-valued properties are mostly left out on purpose. `Format: =DateTimeFormat.ShortDate`
stacks a guess about the enum member on a guess about the property name, so a failure
does not tell you which half was wrong. Where an enum was unavoidable (`FormMode.New`,
`LayoutDirection.Vertical`) the header says so and suggests trying a plain number first.

## The files

| File | Control id under test | In Microsoft's 1P enum? |
|---|---|---|
| `gallery.pa.yaml` | `Gallery` | yes |
| `form.pa.yaml` | `Form` | yes |
| `datatable.pa.yaml` | `DataTable` | **no** |
| `toggle.pa.yaml` | `Toggle` | yes |
| `datepicker.pa.yaml` | `DatePicker` | yes |
| `combobox.pa.yaml` | `ComboBox` | yes |
| `slider.pa.yaml` | `Slider` | yes |
| `timer.pa.yaml` | `Timer` | yes |
| `checkbox.pa.yaml` | `CheckBox` | yes |
| `htmltext.pa.yaml` | `HtmlText` | **no** |
| `container-auto-layout-a-variant.pa.yaml` | `GroupContainer@1.5.0` + placeholder `Variant` | type: yes |
| `container-auto-layout-b-typeid.pa.yaml` | placeholder id | n/a |

"In Microsoft's 1P enum" is a wording aid and nothing more — every entry in that mirror
is marked `evidence: unverified`, and a `no` is not evidence the control is unusable.
`Classic/`-prefixed spellings are a live unknown too: this repo's Studio tests produced
`Classic/Button`, `Classic/TextInput`, `Classic/DropDown` and `Classic/Radio` while the
enum lists them bare. If a bare id here fails, `Classic/<Id>` is the next thing to try.

## Linting

Every file passes L0 (YAML) and L1 (schema) of `scripts/pa_lint.py` and raises L2
warnings. The L2 warnings are the point — they are the linter agreeing that nothing
here is verified. `scripts/validate.py` enforces exactly that on every CI run, plus
one control per file.
