---
name: power-app-yaml
description: >-
  Converts an HTML/CSS mockup (e.g. from Google Stitch, v0, Figma exports) or a screenshot of a UI
  into Power Apps Canvas source code (.pa.yaml, source schema v3.0) that pastes directly into a
  blank screen in Power Apps Studio via "Paste code". Use whenever someone shares an HTML mockup,
  a UI screenshot, or a design export and wants it turned into a Power Apps screen, or asks to
  "convert this to pa.yaml", "make this a Power Apps screen", "turn this design into code I can
  paste into Power Apps", or similar — even without the exact term ".pa.yaml". Also use to
  fix/debug a .pa.yaml that failed to paste in Studio (PA1001 / PA2108-style errors), to add a new
  screen to an existing app, or to extend a screen made this way before. The skill carries a
  catalog of control types and properties that are confirmed to work versus merely guessed — the
  #1 cause of paste failures — so consult it before writing any .pa.yaml.
---

# HTML / Image → Power Apps Canvas YAML

Turn a mockup into a `.pa.yaml` file that pastes cleanly into Power Apps Studio ("Paste code" on a
blank screen). This skill is built to work even on a small/low-effort model: follow the workflow in
order, fill in the templates, and only use controls listed in the catalog. Don't improvise schema.

## Why a whole skill for "just YAML"

`.pa.yaml` looks like ordinary YAML but the schema is narrow, version-pinned, and full of naming
quirks that you cannot derive from web/HTML intuition:

- `Label` has **no** prefix, but `Classic/Button` has a `Classic/` prefix.
- `Icon` and `Classic/Icon` are **different controls** with different capabilities.
- Every property value must start with `=`, and commas inside `RGBA(...)` break flow-style YAML.

Guessing an unconfirmed control type or property is what makes a paste fail. The whole method is:
**use only what's confirmed, label every guess honestly, and let the user paste-test small pieces
before trusting them.** Cleverness is not required; discipline is.

---

## The workflow (do these in order)

1. **Read `references/confirmed-controls.md` in full.** It is the source of truth for which controls
   and properties actually work. Re-read it fresh each time — the user may have added confirmed
   entries after a Studio test.
2. **Open the closest example** in `assets/examples/` and copy its structure (see the picker below).
3. **Decompose the mockup** into controls, pulling real values (text, hex colors, sizes, X/Y).
4. **Write the full `.pa.yaml`** using the templates in this file. Tag anything unconfirmed.
5. **Verify it offline before anyone sees it.** Run `python scripts/pa_lint.py <file>`. Do not hand
   the file over while any L0/L1 error remains. Report every remaining L2/L3 warning to the user
   verbatim as the UNVERIFIED list, together with the generated isolated test snippets.
6. **Hand the whole file to the user to paste**, plus any isolated test snippet for unconfirmed bits.
7. **Read back the Studio result** (error, warning, or screenshot) and fix only what broke.
8. **If a Studio test confirms something new**, record it in `confirmed-controls.md` — and in
   `references/controls.yaml`, which is the machine-readable source of truth the linter reads.

---

## Pick the closest example (do this before writing)

| The mockup is mostly… | Start from | It shows the pattern for |
|---|---|---|
| A left nav / sidebar + top bar + page shell | `assets/examples/example-app-shell.yaml` | Sidebar buttons, active indicator, icons, `Navigate()`, top bar |
| A multi-section form (inputs + dropdowns in cards) | `assets/examples/example-form.yaml` | Card containers, label+input pairs, `TextInput`, `DropDown`, tall scrolling screen |
| A grid/list of selectable cards (checklist, tiles) | `assets/examples/example-card-grid.yaml` | Repeated cards, badges, selectable tiles, footer nav buttons |

Follow the example's real naming, grouping, and coordinate math instead of inventing a new pattern.
If the mockup combines archetypes (e.g. sidebar **and** a form), take the shell from one example and
the inner content from another.

---

## Control picker (mockup element → what to write)

Only these are confirmed. If the mockup needs something **not** in this table, see "Handling
anything unconfirmed" below — don't just pick a plausible-sounding control.

| Mockup element | Control to use | Notes |
|---|---|---|
| Text / heading / label | `Label@2.5.1` | No prefix. |
| Button, **and every sidebar/nav item** | `Classic/Button@2.2.0` | Nav items must be Button (clickable), never Label. |
| Card / panel / any box that holds children | `GroupContainer@1.5.0` + `Variant: ManualLayout` | Real children go in a nested `Children:` key. |
| Colored bar / divider / badge block / active-indicator | `Rectangle@2.3.0` | Rounded corners not verified — don't assume `Radius*`. |
| Image / avatar / logo image | `Image@2.2.3` | Only `Image/X/Y/Width/Height` verified. |
| Icon (that needs a color) | `Classic/Icon@2.5.0` | Use this, not plain `Icon` (plain `Icon` can't take `Color`). |
| Single-line text field | `Classic/TextInput@2.3.2` | See confirmed props in the catalog. |
| Dropdown / select | `Classic/DropDown@2.3.1` | `Items: =["a","b"]` (array literal). |
| Radio group | `Classic/Radio@2.3.0` | `Items: =["a","b"]`. |

Slider, DatePicker, Toggle, ComboBox, Gallery, DataTable, Camera, Barcode, etc. are **not verified** —
propose an isolated test snippet first.

---

## Templates (fill in the blanks)

### 1. Screen wrapper — always the outer shell, never a bare control

```yaml
Screens:
  MyScreen:                          # any non-empty name; keep it simple (letters/digits/_)
    Properties:
      Fill: =RGBA(244, 244, 246, 1)
      # Height: =2232                # ONLY if the content scrolls below the viewport
    Children:
      - # ... controls go here ...
```

### 2. Label

```yaml
- lblTitle:
    Control: Label@2.5.1
    Properties:
      Text: ="Page title"
      Color: =RGBA(24, 28, 35, 1)
      Font: =Font.'Segoe UI'
      FontWeight: =FontWeight.Bold   # optional
      Size: =26
      X: =304
      Y: =104
      Width: =1000
      Height: =40
```

### 3. Container (card / panel) with nested children

```yaml
- grpCard:
    Control: GroupContainer@1.5.0
    Variant: ManualLayout
    Properties:
      Fill: =RGBA(255, 255, 255, 1)
      BorderColor: =RGBA(193, 198, 215, 1)
      BorderThickness: =1
      X: =304
      Y: =168
      Width: =1038
      Height: =288
      RadiusBottomLeft: =0
      RadiusBottomRight: =0
      RadiusTopLeft: =0
      RadiusTopRight: =0
    Children:                        # child X/Y are relative to the container
      - # ... nested controls ...
```

### 4. Form field = Label + TextInput pair

```yaml
- fldNameLabel:
    Control: Label@2.5.1
    Properties:
      Text: ="Full name"
      Color: =RGBA(65, 71, 84, 1)
      Font: =Font.'Segoe UI'
      Size: =12
      X: =32
      Y: =96
      Width: =479
      Height: =20
- fldNameInput:
    Control: Classic/TextInput@2.3.2
    Properties:
      Default: =""
      HintText: ="Enter your name"
      BorderColor: =RGBA(193, 198, 215, 1)
      BorderThickness: =1
      Color: =RGBA(65, 71, 84, 1)
      Size: =10
      X: =32
      Y: =120
      Width: =479
      Height: =48
      RadiusBottomLeft: =0
      RadiusBottomRight: =0
      RadiusTopLeft: =0
      RadiusTopRight: =0
```

### 5. Dropdown

```yaml
- ddCountry:
    Control: Classic/DropDown@2.3.1
    Properties:
      Items: =["Option A", "Option B", "Option C"]
      Items.Value: =Value
      BorderColor: =RGBA(193, 198, 215, 1)
      BorderThickness: =1
      ChevronBackground: =ColorValue("#007FFA")
      Color: =RGBA(65, 71, 84, 1)
      Size: =10
      X: =32
      Y: =208
      Width: =479
      Height: =48
```

### 6. Sidebar nav item = Button + Icon (+ Rectangle indicator for the active one)

```yaml
- btnNavHome:
    Control: Classic/Button@2.2.0
    Properties:
      Text: ="Home"
      BorderStyle: =BorderStyle.None
      Color: =RGBA(65, 71, 84, 1)
      Fill: =RGBA(255, 255, 255, 1)
      Font: =Font.'Segoe UI'
      HoverColor: =ColorValue("#414754")
      HoverFill: =RGBA(230, 232, 243, 1)
      PressedColor: =ColorValue("#414754")
      PressedFill: =ColorValue("#e6e8f3")
      OnSelect: =Navigate('MyRequests', ScreenTransition.Fade)  # target screen must exist
      Size: =16
      Width: =280
      Height: =48
      Y: =104
      RadiusBottomLeft: =0
      RadiusBottomRight: =0
      RadiusTopLeft: =0
      RadiusTopRight: =0
- icoNavHome:
    Control: Classic/Icon@2.5.0
    Properties:
      Icon: =Icon.Home
      Color: =RGBA(65, 71, 84, 1)
      X: =16
      Y: =116
      Width: =24
      Height: =24
```

---

## Rules while writing (each is one line for a reason)

1. **Full wrapper always.** `Screens: -> <name> -> Properties/Children`. Never paste a bare control.
2. **Every value starts with `=`.** `Text: ="hi"`, `X: =0`, `Fill: =RGBA(...)`.
3. **Block-style Properties only.** Never `{X: =0, Fill: =RGBA(...)}` — the RGBA commas break it.
4. **Real nesting = a real nested `Children:` key.** Visual overlap in Studio does NOT nest controls.
5. **Sidebar/nav items are `Classic/Button@2.2.0`,** never `Label`, even if the mockup looks like plain text — nav needs to be clickable.
6. **Only confirmed controls/properties in the main file.** Anything else gets tagged and tested (below).
7. **`OnSelect: =Navigate('Target', ...)` only if `Target` exists.** If not, use a placeholder and comment that it isn't wired up — don't invent a screen name.
8. **Tag every control/property you're not sure of** with an inline comment: `# CONFIRMED` (backed by the catalog or an example) or `# UNVERIFIED — <why you guessed>`. Never present a guess as confirmed.

### Sensible defaults (so you don't have to re-derive them)

- Font: `=Font.'Segoe UI'` · Bold: `=FontWeight.Bold`
- Screen bg: `=RGBA(244, 244, 246, 1)` · Card bg: `=RGBA(255, 255, 255, 1)`
- Body text: `=RGBA(65, 71, 84, 1)` · Heading text: `=RGBA(24, 28, 35, 1)` · Border: `=RGBA(193, 198, 215, 1)`
- Square corners: set all four `Radius*: =0`.
- Pull hover/pressed colors from the mockup's CSS/Tailwind config, not by eyeballing a screenshot.

These are starting values from the example files — override them with the mockup's real values.

---

## Handling anything unconfirmed

If the mockup needs a control or property not in the catalog (a Slider, a DatePicker, rounded
`Rectangle` corners, a one-sided border, a shadow, etc.):

1. In the main file, mark it `# UNVERIFIED — <reasoning>`.
2. **Separately** give the user a tiny isolated snippet (just that one control, in a full wrapper)
   labeled **"paste-test this one first."** Only trust it after Studio accepts it.
3. If it has **no** confirmed Power Fx equivalent (shadows, blur, CSS transitions, `group-hover`,
   one-sided borders — see the catalog), say so plainly and offer the closest real substitute (e.g.
   a thin `Rectangle` for a left border). Don't silently drop it or fake a property.

---

## Hand off + read back results

- **Send the entire file** (Studio needs a full-file paste), plus any isolated test snippets as
  clearly labeled separate blocks.
- When the user reports back, **classify the message first** using the Error-vs-warning table in the
  catalog: `PA1001` / `PA2108` = blocks the whole paste (must fix); `PA2105` / `PA2106` = non-blocking
  version warning (Studio auto-substitutes — don't panic-fix it).
- **If they send a screenshot,** compare it point-by-point to the mockup — position, color, size,
  font, border, radius — and name the specific remaining differences instead of saying "looks close."
- **Fix only what's broken.** A one-property fix doesn't justify rewriting the file.

## Keep the catalog honest

This skill is only as good as `references/confirmed-controls.md`. When a Studio test in a
conversation confirms or disconfirms something, update that file (add a row, move an item from
unverified to confirmed, or fix a wrong assumption) so the next conversion benefits. Don't let
hard-won test results live only in chat history.

## Pre-send checklist (run through this before replying)

- [ ] `python scripts/pa_lint.py <file>` run, and **zero L0/L1 errors** remain
- [ ] Full `Screens: -> name -> Children` wrapper present
- [ ] Every property value starts with `=`
- [ ] Properties are block-style (no `{ }` with commas)
- [ ] Every control type/version is from the catalog (or tagged `# UNVERIFIED` + given a test snippet)
- [ ] Nested controls sit inside a real `Children:` key
- [ ] Sidebar/nav items are `Classic/Button`, not `Label`
- [ ] Every `Navigate()` target is a screen that exists (or a commented placeholder)
- [ ] Unconfirmed items are flagged and, where impossible, called out with a substitute
