# Confirmed Control Catalog (Power Apps Canvas .pa.yaml)

This is accumulated ground truth, built from actual Power Apps Studio "View code" exports and real
paste tests — **not** from guessing what "should" work by analogy with web/HTML controls. Treat
everything here as the baseline. **Anything not listed here is UNVERIFIED by definition**, even if
it looks like an obvious counterpart to something that is listed.

Every entry is tagged with its evidence source:

- **[Studio-tested]** — confirmed by pasting into Studio and reading back the errors/exports.
- **[Example file]** — observed working in the bundled `assets/examples/` files. Strong, but slightly
  weaker than a fresh isolated test, since a working screen can still carry an unnoticed cosmetic
  error.

Control versions below are what these Studio tests produced. Studio pins control versions, and a
newer Studio may emit different version numbers (it will warn and auto-substitute — see the
Error-vs-warning section). If your Studio reports a different version for a control, trust your
Studio and update your copy of this file.

## Control types

| Control | Type string | Evidence | Notes |
|---|---|---|---|
| Label | `Label@2.5.1` | Studio-tested | No prefix. |
| Button | `Classic/Button@2.2.0` | Studio-tested | Has `Classic/` prefix. **All sidebar/nav items must use this**, never Label, even if the mockup shows plain text — nav items need to be clickable/navigable. |
| Free-position container | `GroupContainer@1.5.0` with `Variant: ManualLayout` | Studio-tested | Holds children via a nested `Children:` key. |
| Rectangle / color bar | `Rectangle@2.3.0` | Studio-tested (pastes clean) | Rounded corners (`Radius*`) NOT verified — don't assume it supports them. |
| Image | `Image@2.2.3` | Studio-tested (pastes clean) | Only `Image/X/Y/Width/Height` verified. Other properties unverified. |
| Icon (recolorable) | `Classic/Icon@2.5.0` | Studio-tested | Must use this, not plain `Icon` (plain `Icon` at its current version does NOT support `Color`). |
| Text input | `Classic/TextInput@2.3.2` | Example file (`example-form.yaml`) | Seen with `BorderColor`, `BorderThickness`, `Color`, `Default`, `HintText`, `Radius*`, `Size`, plus the universal X/Y/Width/Height. |
| Dropdown | `Classic/DropDown@2.3.1` | Example file (`example-form.yaml`) | Seen with `BorderColor`, `BorderThickness`, `ChevronBackground`, `Color`, `Items` (array literal, e.g. `=["a","b"]`), `Items.Value`, `Size`. |
| Radio button | `Classic/Radio@2.3.0` | Studio-tested (earlier session) | `Items` accepts array-literal syntax: `=["a", "b"]`. |

**Not yet attempted / no evidence either way:** Timer, Slider, DatePicker, Toggle, ComboBox, Gallery,
DataTable, PDF viewer, Camera, Barcode. Do not assume property names carry over — propose a small
isolated test snippet before using any of these in a full file.

## Properties confirmed per control

- **Every control tried so far**: `X`, `Y`, `Width`, `Height`, `Fill`, `Visible`
- **Label**: `Text`, `Color`, `Font` (e.g. `=Font.'Segoe UI'`), `Size`, `Align` (e.g. `=Align.Center`), `FontWeight` (e.g. `=FontWeight.Bold`). `FontWeight` confirmed on Label only, not verified on Button.
- **Classic/Button**: `Text`, `Color`, `Fill`, `BorderColor`, `BorderStyle` (enum, e.g. `=BorderStyle.None`), `BorderThickness`, `FocusedBorderThickness`, `Disabled(Color|BorderColor|Fill)`, `Hover(Color|BorderColor|Fill)`, `Pressed(Color|BorderColor|Fill)`, `Radius(TopLeft|TopRight|BottomLeft|BottomRight)`, `OnSelect`
- **GroupContainer**: `Fill`, `Width`, `Height`, `Visible`, `BorderColor`, `BorderThickness`, `Radius(TopLeft|TopRight|BottomLeft|BottomRight)`
- **Classic/Icon**: `Icon` (enum, e.g. `=Icon.CheckBadge`), `Color`, `BorderColor`, `Disabled(Color|BorderColor|Fill)`, `Hover(Color|BorderColor|Fill)`, `Pressed(Color|BorderColor|Fill)`, `FocusedBorderThickness`
- **Classic/TextInput**: `BorderColor`, `BorderThickness`, `Color`, `Default`, `HintText`, `Radius(TopLeft|TopRight|BottomLeft|BottomRight)`, `Size`
- **Classic/DropDown**: `BorderColor`, `BorderThickness`, `ChevronBackground`, `Color`, `Items` (array literal), `Items.Value`, `Size`
- **Classic/Radio**: `Items` (array literal)

**Important caveat:** Studio's "View code" only exports properties that differ from their default. If
a property isn't in an export, that does NOT prove the control lacks it — it may just never have been
changed. Don't over-conclude from absence.

## Confirmed patterns and gotchas

- **Formulas always start with `=`**, e.g. `=RGBA(0,0,0,1)`, `="some text"`. (The schema enforces this:
  property values must match `^=.*`.)
- **Use block-style YAML for Properties, never flow-style** (`{X: =0, Fill: =RGBA(...)}`). Flow-style
  breaks because the commas inside `RGBA(...)` get parsed as YAML separators. Always write:
  ```yaml
  Properties:
    X: =0
    Fill: =RGBA(10, 20, 30, 1)
  ```
- **Full-file paste only.** You must paste the entire `Screens: -> <screen name> -> Children:`
  structure. Pasting a single bare control snippet is not supported.
- **True nesting requires literal nested `Children:` keys.** Dragging one control on top of another in
  the Studio canvas or Tree view does NOT create real parent-child nesting — it only looks that way.
  If a control belongs inside a container, write it nested in the YAML. Child `X`/`Y` are relative to
  the container.
- **Name collisions auto-rename silently.** If a screen or control name in your paste already exists in
  the target file, Studio appends `_1`, `_2`, etc. without erroring — so a changed name doesn't mean
  the paste failed.
- **Non-ASCII text works** in `Text`, `HintText`, and `Default` (Thai, Japanese, CJK, emoji, etc.) —
  just quote it normally, e.g. `Text: ="<your localized string>"`. Whether a specific non-`Segoe UI`
  font actually renders on the target machine is a separate, unverified question (see below).
- **Screen scrolling** works in Responsive layout mode when the screen's `Height` (in its Properties
  block) is larger than the visible viewport, e.g. `Height: =2232`.
- **Reusable theme colors**: prefer setting them once in `App.OnStart`
  (e.g. `Set(varThemeHover, ColorValue("#007FFA"))`) rather than repeating hex/RGBA literals across
  many controls.

## Example palette (illustrative — extract your own from the mockup)

These are sample values from the bundled examples to show the **shape** of a Power Fx color, not a
palette you should reuse blindly. For a real conversion, pull the actual hex from the mockup's CSS /
Tailwind config (screenshots don't show hover states, so read the config for those).

| Element | Example hex | Power Fx form |
|---|---|---|
| Accent / primary | `#007FFA` | `=ColorValue("#007FFA")` or `=RGBA(0, 127, 250, 1)` |
| Inactive nav button, hover fill | `#e6e8f3` | `HoverFill: =RGBA(230, 232, 243, 1)` |
| Card hover background (5% tint) | primary @ 5% | `HoverFill: =RGBA(0, 90, 182, 0.05)` |
| Card hover border | `#005ab6` | `HoverBorderColor: =RGBA(0, 90, 182, 1)` |

## Confirmed unachievable — say so plainly, don't fake it

There is no verified Power Fx equivalent for these CSS behaviors. When a mockup relies on one, tell
the user pixel-perfect parity isn't possible and suggest the closest practical alternative (e.g. a
thin `Rectangle` for a one-sided border) rather than quietly dropping it or inventing a fake property.

- `group-hover` (a child `Label` changing color when a parent Button/container is hovered) — Label and
  Button are separate controls that don't share hover state directly. A workaround via
  `Button.Value` / mouse-position formulas exists but is substantially more complex; flag it as
  "possible but not yet confirmed" rather than doing it silently.
- `shadow-*` / box shadow (on hover or otherwise)
- `backdrop-blur`
- CSS transitions / animations
- One-sided borders (e.g. `border-left` only) — approximate with a thin `Rectangle`.
- Whether non-`Font.'Segoe UI'` fonts actually render on the target machine — unverified either way.

## Linter warnings about a control type

`scripts/pa_lint.py` raises one of two L2 warnings when it meets a control type it cannot
vouch for. They differ only in wording, never in what you must do about it.

| Check | Means | What to do |
|---|---|---|
| `L2.unverified-control-type` | Not in the catalog, and not in Microsoft's control-id enum either. | Treat as a guess. Tag `# UNVERIFIED`, hand over the isolated snippet. |
| `L2.candidate-control-type` | The id appears in Microsoft's first-party control-id enum (`control-ids-candidate.yaml`) but has never been paste-tested here. | Identical treatment. It is still a guess about *this* Studio build, and it says nothing at all about the control's properties. Never present it as confirmed. |

Neither is evidence. `control-ids-candidate.yaml` is a wording aid: every entry in it is
marked `evidence: unverified`, and none may be promoted without a Studio test.

## Error vs warning behavior when pasting

- **Errors** (e.g. `PA2108` unknown property, `PA1001` invalid schema) — **block the entire paste**.
  Nothing from that paste is applied.
- **Warnings** (e.g. `PA2105` / `PA2106`, usually about an out-of-date or newer-than-current control
  version) — **do not block**. Studio silently substitutes the current version instead.

When the user reports an error/warning, sort it into one of these two buckets before deciding what to
fix — don't treat a warning as fatal, and don't wave away a real error.
