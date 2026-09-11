---
name: power-app-yaml
description: >-
  Converts an HTML/CSS mockup (Google Stitch, v0, Figma export) or a UI screenshot into
  Power Apps Canvas source code (.pa.yaml, source schema v3.0) for "Paste code" on a blank
  screen in Power Apps Studio. Use when someone shares an HTML mockup, UI screenshot,
  wireframe or design export and wants a Power Apps screen, or asks to "convert this to
  pa.yaml", "make this a Power Apps screen", or "turn this design into code I can paste
  into Power Apps" — even without the term ".pa.yaml". Also to fix or debug a .pa.yaml
  that failed to paste in Studio (PA1001 / PA2108), to add a new screen to an existing
  app, or to extend a screen made this way.
---

# HTML / Image → Power Apps Canvas YAML

Turn a mockup into a `.pa.yaml` that pastes cleanly into Studio ("Paste code" on a blank
screen). Work the steps in order, use only catalogued controls, never improvise schema.
Rationale: [`README.md`](../../README.md).

## The workflow (in order)

1. **Read [`references/controls.yaml`](references/controls.yaml)** — the catalog of what
   works. Fresh each time; the user may have added entries since.
   [`confirmed-controls.md`](references/confirmed-controls.md) is the same facts in prose,
   plus gotchas and the paste-error table.
2. **Pick pattern(s) from [`assets/patterns/`](assets/patterns/)** — 13 lint-clean 30–85
   line snippets extracted from the examples, each citing its source and evidence level.
   Read only what you need: `screen-shell`, `sidebar-nav-item`, `top-bar`,
   `card-container`, `section-header`, `form-field-text`, `form-field-dropdown`,
   `tile-grid-cell`, `badge`, `divider`, `avatar-row`, `footer-nav`,
   `two-column-split`.
3. **Apply [`references/layout-mapping.md`](references/layout-mapping.md)** for absolute
   `X`/`Y`/`Width`/`Height`: canvas size and scale, Tailwind→px, flex/grid arithmetic,
   nesting, screen `Height`. This is the step usually guessed.
4. **Only if the patterns don't cover it, read a *slice*** of an example, via the line
   ranges in [`assets/examples/INDEX.md`](assets/examples/INDEX.md). All 3,234 example
   lines cost more context than the rest of the skill combined.
5. **Write the full `.pa.yaml`** from the templates below. Tag anything unconfirmed.
6. **Lint: `python scripts/pa_lint.py <file>`.** Never hand over a file with an L0/L1
   error. Report every L2/L3 warning verbatim as the UNVERIFIED list, with the snippets
   the linter generates. `L2.unverified-control-type` and `L2.candidate-control-type` get
   identical treatment — Microsoft's control-id enum is not evidence.
7. **Hand over the whole file** plus those snippets, **read back the Studio result**, fix
   only what broke.
8. **If Studio confirms something new**, record it in `controls.yaml` *and*
   `confirmed-controls.md`. With a real export, harvest instead of guessing —
   [`docs/harvesting.md`](../../docs/harvesting.md).

## Control picker

Only these are confirmed. Anything else: rule 8.

| Mockup element | Control | Notes |
|---|---|---|
| Text / heading / label | `Label@2.5.1` | No prefix. |
| Button, **and every nav item** | `Classic/Button@2.2.0` | Nav must be Button (clickable), never Label. |
| Card / panel / box with children | `GroupContainer@1.5.0` + `Variant: ManualLayout` | Nested `Children:`. Only control with confirmed `Radius*` + border + fill. |
| Bar / divider / badge / indicator | `Rectangle@2.3.0` | Universal properties only; `Radius*` NOT verified. |
| Image / avatar / logo | `Image@2.2.3` | Only `Image` + geometry verified. |
| Icon needing a color | `Classic/Icon@2.5.0` | Not plain `Icon` — that can't take `Color`. |
| Single-line text field | `Classic/TextInput@2.3.2` | `Default`, `HintText`, `Size`, border, `Radius*`. |
| Dropdown / select | `Classic/DropDown@2.3.1` | `Items: =["a","b"]`, `Items.Value: =Value`. No `Radius*`. |
| Radio group | `Classic/Radio@2.3.0` | Only `Items` confirmed; no bundled example. |

Everything in `controls.yaml`'s `unattempted_controls` (Slider, DatePicker, Toggle,
ComboBox, Gallery, DataTable, Camera, Barcode…) is **unverified** — snippet-test first.

## Templates

Per-pattern templates are in `assets/patterns/`. These two you always need.

```yaml
# 1. Screen wrapper — the outer shell, never a bare control
Screens:
  MyScreen:                          # letters/digits/_ only
    Properties:
      Fill: =RGBA(244, 244, 246, 1)
      # Height: =2232                # ONLY if content runs past the viewport
    Children:
      - # ... controls ...
```

```yaml
# 2. Container (card / panel) — the only control that nests children
- grpCard:
    Control: GroupContainer@1.5.0
    Variant: ManualLayout            # required, or child X/Y are ignored
    Properties:
      Fill: =RGBA(255, 255, 255, 1)
      BorderColor: =RGBA(193, 198, 215, 1)
      BorderThickness: =1
      X: =304                        # plus Y / Width / Height
      RadiusTopLeft: =0              # plus the other three
    Children:                        # child X/Y are relative to the container
      - # ... nested controls ...
```

## Rules while writing

1. **Full wrapper always.** `Screens: -> <name> -> Properties/Children`. Never a bare control.
2. **Every value starts with `=`.** `Text: ="hi"`, `X: =0`, `Fill: =RGBA(...)`.
3. **Block-style `Properties` only.** `{X: =0, Fill: =RGBA(...)}` breaks on the RGBA commas.
4. **Real nesting = a real nested `Children:` key.** Visual overlap in Studio does NOT nest.
5. **Nav items are `Classic/Button@2.2.0`**, never `Label`, however plain the mockup looks.
6. **Only catalogued controls/properties in the main file.** Anything else gets tagged and tested.
7. **`Navigate('Target', ...)` only if `Target` exists** here — else keep the placeholder and comment on the same line that it isn't wired up. Never invent a screen name.
8. **Tag anything you're unsure of** inline: `# UNVERIFIED — <why you guessed>`, and
   **separately** hand over the isolated snippet `pa_lint.py` generates for it, labeled
   "paste-test this one first." If it has no confirmed Power Fx equivalent at all —
   shadows, blur, CSS transitions, `group-hover`, one-sided borders, `rounded-full`; see
   `impossible_css` in `controls.yaml` — say so plainly and offer the closest real
   substitute (a thin `Rectangle` for a left border). Never drop it silently or fake a
   property.

Example-file defaults, to override with the mockup's real values: font
`=Font.'Segoe UI'`; bold `=FontWeight.Bold` (confirmed on `Label` only); screen bg
`=RGBA(244, 244, 246, 1)`; cards `=RGBA(255, 255, 255, 1)`; body text
`=RGBA(65, 71, 84, 1)`; headings `=RGBA(24, 28, 35, 1)`; borders
`=RGBA(193, 198, 215, 1)`. Read hover/pressed colors from the CSS, never a screenshot.

## Hand off + read back

- **Send the entire file**; isolated snippets go in separate, labeled blocks.
- **Classify the report first.** `PA1001`/`PA2108` block the whole paste (must fix);
  `PA2105`/`PA2106` are version warnings Studio auto-substitutes — don't panic-fix.
- **On a screenshot,** compare point-by-point (position, color, size, font, border,
  radius) and name the differences; never say "looks close." Fix only what's broken.
- **Never read a property's absence from an export as "does not support."**

## Pre-send checklist

- [ ] `pa_lint.py` run; **zero L0/L1 errors** remain
- [ ] Full `Screens: -> name -> Children` wrapper present
- [ ] Every value starts with `=`; `Properties` block-style, no `{ }`
- [ ] Every control type/version catalogued, or tagged `# UNVERIFIED` + given a snippet
- [ ] Nested controls sit in a real `Children:` key; containers are `ManualLayout`
- [ ] Nav items are `Classic/Button`, not `Label`
- [ ] Every `Navigate()` target exists, or is a commented placeholder
- [ ] Rows close, nothing exceeds the canvas width, screen `Height` set if content runs
      past the viewport
- [ ] Unconfirmed items flagged; impossible ones called out with a substitute
