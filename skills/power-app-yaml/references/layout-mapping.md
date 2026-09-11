# Layout mapping — HTML/CSS geometry → absolute `X` / `Y` / `Width` / `Height`

This is the hardest part of the conversion and the part a model most often fakes. It is
pure arithmetic: there is **no confirmed flex, grid, gap, or padding property anywhere in
`controls.yaml`**. A Power Apps control knows four numbers — `X`, `Y`, `Width`, `Height` —
and they are absolute within the parent. So every CSS layout rule has to be *resolved into
numbers once, by you, at authoring time*.

Every Power Apps property named in this file exists in
[`controls.yaml`](controls.yaml). Nothing here invents one. Where a mockup needs something
the catalog cannot do, this file says so instead of substituting a plausible name.

Nesting rule used throughout: **child `X`/`Y` are relative to the parent container**, and a
`GroupContainer` must carry `Variant: ManualLayout` or the child coordinates are ignored
entirely (`scripts/pa_lint.py` raises `L3.xy-in-non-manual-container`).

---

## 1. Canvas sizing

### The target canvas

**Assume 1366 × 768** unless the user says otherwise.

Where that number comes from, precisely:

- **Sourced (derived from this repo's own evidence).** All three bundled examples are laid
  out on 1366 × 768. The top bar sits at `X: =280` with `Width: =1086`, and 280 + 1086 =
  1366; the sidebar is `Height: =768`
  (`assets/examples/example-app-shell.yaml` L11, L166–167).
- **UNVERIFIED.** That 1366 × 768 is *Power Apps' documented default* for a new
  tablet-format canvas app is **not sourced anywhere in this repo** — no doc citation, no
  Studio screenshot, no export. Treat it as a convention inherited from the examples, not
  as Microsoft's stated default. Before relying on it for a new app, ask the user to read
  Studio → Settings → Display and record the real numbers in `confirmed-controls.md`.

If the user's app is phone-format, or the mockup is a phone mockup (≈ 390–430 CSS px
wide), **stop and ask** for the canvas size. Scaling a 390px phone mockup onto a
1366-wide tablet canvas produces a 3.5× blow-up that is never what anyone wants.

### Scale factor

```
scale = target_canvas_width / mockup_width
```

| Mockup width | `scale` to 1366 | What to do |
|---|---|---|
| 1440 (the common Figma/Stitch frame) | 0.948611 | Scale. |
| 1536 | 0.889323 | Scale. |
| 1280 | 1.067188 | Leave 1:1 and centre — see below. |
| 1366 | 1.0 | Nothing to do. |
| ≤ 430 (phone) | — | Ask; do not scale. |

**Only scale down.** If the mockup is *narrower* than the canvas, do **not** enlarge it —
keep every value 1:1 and centre the content block instead:

```
content_X = (1366 - mockup_width) / 2
```

Enlarging re-derives every font size and border upward and the result looks nothing like
the mockup. The bundled examples do exactly this: a 1038-wide content column centred-ish
at `X: =304` on a 1366 canvas.

### The rounding rule

Power Apps accepts non-integer coordinates (`example-form.yaml` uses `Width: =479.0`), but
fractions make diffs unreadable and accumulate visibly across a row. So:

1. **Scale each distinct base value once, round to the nearest integer, and write it down.**
   Not each computed coordinate — each *token* (`p-8` → 30, `gap-6` → 23, and so on).
2. **Do all subsequent arithmetic on the rounded values.** Never mix a rounded width with
   an unrounded gap; the row stops closing.
3. **Close the row explicitly.** After laying out n children, check that
   `last_X + last_Width == container_width - padding`. If it is off by 1–3 px, absorb the
   residue into the **last** child's `Width`. Do not spread it.
4. Round a font `Size` to the nearest integer too, and never below 8 — below that the text
   is unreadable at any zoom and the mockup almost certainly meant a different element.

---

## 2. Tailwind → px

> **STANDING WARNING.** Every number in this section is a **Tailwind default**. If the
> mockup ships its own `tailwind.config.js`, a v4 `@theme { ... }` block, a `:root`
> custom-property block, or an inline `<style>`, **that file wins** — read it and build
> your own table. Arbitrary values (`p-[18px]`, `text-[15px]`, `gap-[7px]`) are literal
> and need no table at all. Google Stitch and v0 exports routinely override the scale.
> These defaults are for when the config is genuinely unavailable (e.g. a screenshot).

### Spacing — `p-*`, `m-*`, `gap-*`, `w-*`, `h-*`, `space-*`, `inset-*`

The rule is `n × 4px`, with 2px half-steps:

| Token | px | Token | px | Token | px |
|---|---|---|---|---|---|
| `0` | 0 | `4` | 16 | `16` | 64 |
| `px` | 1 | `5` | 20 | `20` | 80 |
| `0.5` | 2 | `6` | 24 | `24` | 96 |
| `1` | 4 | `7` | 28 | `28` | 112 |
| `1.5` | 6 | `8` | 32 | `32` | 128 |
| `2` | 8 | `9` | 36 | `36` | 144 |
| `2.5` | 10 | `10` | 40 | `40` | 160 |
| `3` | 12 | `11` | 44 | `48` | 192 |
| `3.5` | 14 | `12` | 48 | `56` | 224 |
| | | `14` | 56 | `64` | 256 |

(Also `72` → 288, `80` → 320, `96` → 384.) Assumes the default `1rem = 16px`. Tailwind v4
derives the whole scale from `--spacing` (default `0.25rem`), which yields the same
numbers — but if the theme overrides `--spacing`, multiply accordingly.

### Text size — `text-*` → `Size`

The second column is the CSS `line-height`, which is what you put in `Height` for a
single-line Label — not the font size.

| Token | font px | line-height px | → `Size:` | → `Height:` (1 line) |
|---|---|---|---|---|
| `text-xs` | 12 | 16 | `=12` | `=16` |
| `text-sm` | 14 | 20 | `=14` | `=20` |
| `text-base` | 16 | 24 | `=16` | `=24` |
| `text-lg` | 18 | 28 | `=18` | `=28` |
| `text-xl` | 20 | 28 | `=20` | `=28` |
| `text-2xl` | 24 | 32 | `=24` | `=32` |
| `text-3xl` | 30 | 36 | `=30` | `=36` |
| `text-4xl` | 36 | 40 | `=36` | `=40` |
| `text-5xl` | 48 | 48 | `=48` | `=48` |
| `text-6xl` | 60 | 60 | `=60` | `=60` |
| `text-7xl` | 72 | 72 | `=72` | `=72` |

For 5xl and up Tailwind's line-height is `1`, i.e. equal to the font size.
Multi-line text: `Height` = `line-height × lines`, and `line-clamp-n` gives you n directly.

**Unit caveat, stated honestly.** The bundled examples set `Size` equal to the mockup's
**px** value 1:1 — `example-card-grid.yaml` L67 uses `Size: =14` for a `text-sm` (14px)
title and L78 `Size: =12` for a `text-xs` (12px) subtitle. Whether Power Apps interprets
`Size` as points or as pixels is **not verified in this repo either way**. Follow the 1:1
convention because it is what the working examples do; if a Studio screenshot comes back
with text obviously too large, that is the first thing to re-measure (a pt→px factor of
4/3 would be the suspect).

### Font weight — `font-*` → `FontWeight`

| Token | CSS weight | Power Apps |
|---|---|---|
| `font-normal` | 400 | `=FontWeight.Normal` — **UNVERIFIED enum member** |
| `font-medium` | 500 | no confirmed member; round to Normal or Bold and say which |
| `font-semibold` | 600 | no confirmed member; round to `=FontWeight.Bold` |
| `font-bold` | 700 | `=FontWeight.Bold` — the only member any example uses |
| `font-extrabold` / `font-black` | 800 / 900 | no confirmed member; use Bold |

Two separate limits here, and they are easy to conflate:

- **The property.** `FontWeight` is confirmed **on `Label` only**. On
  `Classic/Button` the catalog lists it as `properties_unverified` (the bundled examples
  use it on Buttons anyway — an unresolved contradiction awaiting a Studio test), so
  `scripts/pa_lint.py` warns about it there. For bold button text, either accept the
  warning and tag the line `# UNVERIFIED`, or leave the weight off.
- **The enum members.** Only `FontWeight.Bold` appears in any example. Every other member
  is a guess about this Studio build. Two weights, regular and bold, is what you can
  actually deliver — collapse the mockup's five weights onto those and tell the user you
  did.

### Corner radius — `rounded-*` → `Radius*`

| Token | px | Set all four to |
|---|---|---|
| `rounded-none` | 0 | `=0` |
| `rounded-sm` | 2 | `=2` |
| `rounded` | 4 | `=4` |
| `rounded-md` | 6 | `=6` |
| `rounded-lg` | 8 | `=8` |
| `rounded-xl` | 12 | `=12` |
| `rounded-2xl` | 16 | `=16` |
| `rounded-3xl` | 24 | `=24` |
| `rounded-full` | 9999 | see below |

The four properties are `RadiusTopLeft`, `RadiusTopRight`, `RadiusBottomLeft`,
`RadiusBottomRight`. Always write all four; a single-corner radius
(`rounded-tl-lg`) is the one case where writing one of them alone is correct.

Confirmed on `GroupContainer`, `Classic/Button` and `Classic/TextInput`. **Not** on
`Rectangle` — the catalog lists `Rectangle`'s `Radius*` as `properties_unverified`, so a
rounded coloured block must be a `GroupContainer` with a `Fill`, not a `Rectangle`. And
`Classic/DropDown` has no radius property in the catalog at all.

`rounded-full` has no confirmed equivalent. A circle would need radius = half the side on
a square control, which is exactly the unverified case on `Rectangle`. Say so and offer
the square version, or a `GroupContainer` with `Radius*` = half its `Width` tagged
`# UNVERIFIED`.

### Border width — `border-*` → `BorderThickness`

| Token | px |
|---|---|
| `border-0` | 0 |
| `border` | 1 |
| `border-2` | 2 |
| `border-4` | 4 |
| `border-8` | 8 |

Pair it with `BorderColor`. Both are confirmed on `GroupContainer`,
`Classic/Button`, `Classic/TextInput` and `Classic/DropDown`.

Things with no border in the catalog: `Label`, `Rectangle`, `Image`. A bordered text block
is therefore a `GroupContainer` (border + fill) with a `Label` inside it.

One-sided borders (`border-l-4`, `border-t`, `divide-y`) are in `controls.yaml`'s
`impossible_css` list. The sanctioned substitute is a thin `Rectangle` along that edge —
see `assets/patterns/divider.pa.yaml`.

### Things to stop looking for

`impossible_css` in `controls.yaml` is the authority; these are the layout-adjacent ones:
`shadow-*` (no equivalent), `backdrop-blur-*` (none), `transition-*` / `duration-*`
(none), `group-hover:*` (Label and Button do not share hover state), and one-sided
borders (thin `Rectangle`). Name the gap to the user and offer the substitute; never fake
a property to cover it.

---

## 3. Flex row → cumulative X

Given a container whose **inner** box is `W_inner × H_inner` after padding `P`
(`W_inner = W - 2P`), children of widths `w₁…wₙ` and heights `h₁…hₙ`, and `gap-G`:

```
content = Σwₖ + (n - 1) × G
slack   = W_inner - content
```

`justify-*` decides where the row starts and whether `G` is honoured:

| `justify-*` | first child `X` | step to the next `X` |
|---|---|---|
| `start` (default) | `P` | `Xₖ = Xₖ₋₁ + wₖ₋₁ + G` |
| `end` | `P + slack` | `Xₖ = Xₖ₋₁ + wₖ₋₁ + G` |
| `center` | `P + slack / 2` | `Xₖ = Xₖ₋₁ + wₖ₋₁ + G` |
| `between` | `P` | `Xₖ = Xₖ₋₁ + wₖ₋₁ + g`, `g = (W_inner - Σw) / (n - 1)` |
| `around` | `P + g / 2` | `Xₖ = Xₖ₋₁ + wₖ₋₁ + g`, `g = (W_inner - Σw) / n` |
| `evenly` | `P + g` | `Xₖ = Xₖ₋₁ + wₖ₋₁ + g`, `g = (W_inner - Σw) / (n + 1)` |

`between`, `around` and `evenly` **supersede `gap`**: the computed `g` replaces `G`, and
the formulas above are exact, because CSS `gap` is a minimum and `justify-content`
distributes whatever is left after it. The one exception is an overflowing row
(`slack < 0`): then the gaps stay at `G` and the content runs past the container — which
means you misread a width, so go back and re-measure rather than laying that out.

`items-*` decides each child's `Y`, and it is computed **per child** because heights differ:

| `items-*` | child `Y` | child `Height` |
|---|---|---|
| `start` | `P_top` | its own `hₖ` |
| `center` | `P_top + (H_inner - hₖ) / 2` | its own `hₖ` |
| `end` | `P_top + H_inner - hₖ` | its own `hₖ` |
| `stretch` (default) | `P_top` | `H_inner` |
| `baseline` | approximate as `center`; say that you did | its own `hₖ` |

**`flex-1` / `flex-grow`.** Resolve it before anything else:

```
leftover = W_inner - Σ(fixed widths) - (n - 1) × G
```

One `flex-1` child takes all of `leftover`. m equal `flex-1` children take
`floor(leftover / m)` each, with the residue added to the last one so the row still
closes. `flex-grow: 2` against `flex-grow: 1` splits `leftover` 2:1 — again, floor and
give the residue to the last.

**Worked micro-example.** A 1086 × 64 top bar, `flex items-center justify-end gap-4
px-6`, holding a 295-wide name block (20 tall) and a 40 × 40 avatar. `px-6` pads the
horizontal axis only, so `P = 24` and `P_top = 0`:

```
G = 16 (gap-4),   W_inner = 1086 - 2 × 24 = 1038,   H_inner = 64
content  = 295 + 40 + 16 = 351
slack    = 1038 - 351    = 687                          (justify-end)
name   X = 24 + 687      = 711      Y = (64 - 20) / 2 = 22      (items-center)
avatar X = 711 + 295 + 16 = 1022    Y = (64 - 40) / 2 = 12
closing check: 1022 + 40 = 1062 = 1086 - 24             OK
```

The real example (`example-app-shell.yaml` L169–200) lands on `Y: =12` for the avatar and
`Y: =13` for the name — the 1px difference is the designer nudging the two-line name/role
block up. Keep a nudge like that if you can read it off the mockup; ignore it if you
cannot.

**Sanity-check `H_inner` against the tallest child.** Had you assumed `py-6` here,
`H_inner` would be `64 - 48 = 16` and the 40px avatar would not fit inside its own
parent's content box. A child taller than `H_inner`, or a negative coordinate, always
means a misread box — never a Power Apps limitation. Go back and re-read the padding.

## Flex column → cumulative Y

Identical, with the axes swapped: `justify-*` drives `Y`/`Height`, `items-*` drives
`X`/`Width`. The default `items-stretch` in a column is why a stacked form field's
`Width` is the container's full inner width.

```
Y₁ = P_top                      (justify-start)
Yₖ = Yₖ₋₁ + hₖ₋₁ + G
Xₖ = P                          (items-stretch)
Wₖ = W_inner
```

`space-y-N` is the same as `gap-N` for this purpose; `mt-N` on one child adds N to that
child's `Y` **and to every `Y` after it**.

---

## 4. Grid → column width math

For `grid grid-cols-n gap-G` (or `gap-x-Gx gap-y-Gy`) in a container of width `W` with
padding `P`:

```
inner    = W - 2P
column   = (inner - (n - 1) × Gx) / n
Xₖ       = P + (k - 1) × (column + Gx)          k = 1 … n
Yᵣ       = P_top + (r - 1) × (row_height + Gy)  r = 1 … rows
```

**Closing check, every time:** `X_n + column == W - P`. If it does not,
you mixed a rounded and an unrounded value.

**Non-integer columns.** Take `column = floor(...)`, then

```
residue = inner - (n - 1) × Gx - n × floor(column)
```

and add `residue` to the **last** column's `Width` only. Spreading it across columns makes
the gutters visibly uneven, which reads worse than one column being 2px wide.

**`col-span-s`** occupies s columns plus the gutters it swallows:

```
Width = s × column + (s - 1) × Gx
```

Its `X` is still `P + (k - 1) × (column + Gx)` for its starting column k.

**Auto-flowing grids** (`grid-cols-[repeat(auto-fill,minmax(280px,1fr))]`) have no fixed
n. Pick the n the mockup actually renders at its own width, state that you pinned it, and
lay it out as a fixed grid — there is no confirmed reflow behaviour to reproduce.

**Gap vs. pitch.** Once laid out, the distance between consecutive children (the *pitch*)
is `column + Gx` horizontally and `row_height + Gy` vertically. The examples are built on
pitches: nav rows 48 + 0 = 48 (`example-app-shell.yaml`, Y 104/152/200/248), grid rows
96 + 16 = 112 (`example-card-grid.yaml`, Y 208/320/432). Deriving the pitch once and
adding it repeatedly is less error-prone than recomputing each coordinate.

---

## 5. Nesting — the actual arithmetic

A child's coordinates are relative to its parent, and this composes down every level:

```
absolute_X(control) = X(control) + X(parent) + X(grandparent) + …
absolute_Y(control) = Y(control) + Y(parent) + Y(grandparent) + …
```

So to place something at a known absolute position, subtract:

```
child_X = wanted_absolute_X - parent_absolute_X
child_Y = wanted_absolute_Y - parent_absolute_Y
```

**Two-level example, from the form.** `Card1` sits at `X: =304, Y: =168`. Its badge sits
at `X: =32, Y: =32`. The badge's absolute position on the screen is
(304 + 32, 168 + 32) = **(336, 200)**. If the mockup instead measured the badge at
absolute (336, 200) and you already know the card is at (304, 168), the child values you
write are 336 − 304 = 32 and 200 − 168 = 32.

**Three-level example.** Screen → top bar (`X: =280, Y: =0`) → avatar (`X: =1033,
Y: =12`). Absolute: (280 + 1033, 0 + 12) = (1313, 12), and 1313 + 40 = 1353, which is
13px short of the 1366 canvas edge — the bar's right inset. That check is worth doing:
if the sum lands past the canvas width, the child is off-screen and Studio will not warn
you.

**Padding is not a property — it is the child's offset.** There is no confirmed padding
property on any control in the catalog. `p-8` on a container means:

```
first child X = 32,  first child Y = 32
usable inner  = (Width - 64) × (Height - 64)
```

and that is the whole implementation. Likewise `px-6 py-4` means `X = 24` and `Y = 16`
with `usable inner = (Width - 48) × (Height - 32)`.

**Overlaying is not nesting.** Two controls at the same coordinates just paint on top of
each other in declaration order (later = on top). The click-overlay Button in
`tile-grid-cell.pa.yaml` relies on exactly that. Real parenthood requires a literal
nested `Children:` key.

---

## 6. Vertical overflow → the screen's `Height`

A screen defaults to the viewport. When the content is taller, set the screen's own
`Height` in its `Properties` block. `confirmed-controls.md` records that this is what
makes a screen scroll (in Responsive layout mode).

```
content_bottom = max over all TOP-LEVEL children of (Y + Height)
```

Only top-level children: a nested child's `Y + Height` is inside its parent and already
counted by the parent's own `Height`. Then:

```
if content_bottom + bottom_margin > canvas_height:
        Height = round_up_to_8(content_bottom + bottom_margin)
else:
        omit Height entirely
```

`bottom_margin` is the mockup's own trailing padding (`p-8` → 32).

**Check the rule against the examples — it reproduces both.**

- `example-form.yaml`: the lowest top-level child is the footer at `Y: =1951`,
  `Height: =80` → `content_bottom = 2031`. The file sets `Height: =2032` (L5). Rounding
  2031 up to the next multiple of 8 gives 2032. Exact match.
- `example-card-grid.yaml`: the Next button is at `Y: =2144`, `Height: =48` →
  `content_bottom = 2192` (the progress dots at `Y: =2166` + 4 = 2170 are higher). The
  file sets `Height: =2232` (L5) — that is 2192 + 40 of trailing margin, then already a
  multiple of 8.

**Horizontal overflow has no equivalent.** There is no confirmed horizontal-scroll
property. If `X + Width` exceeds the canvas width for any top-level control, the content
is simply cut off. Re-scale (§1) or re-flow the row; do not ship a control that runs off
the right edge.

---

## 7. Fully worked example

**The mockup** — a 1440px-wide page:

```html
<div class="w-[1440px] p-8">
  <h1 class="text-3xl font-bold">Templates</h1>
  <p class="text-sm mt-2 text-slate-500">Pick one to start.</p>

  <div class="mt-6 grid grid-cols-3 gap-6">
    <!-- x6 -->
    <div class="h-[180px] rounded-lg border p-6 bg-white">
      <h3 class="text-lg font-semibold">Onboarding Form</h3>
      <p class="text-sm mt-2 text-slate-500">Word document</p>
    </div>
  </div>
</div>
```

### Step 1 — canvas and scale

Target 1366 × 768 (§1). `scale = 1366 / 1440 = 0.948611`.

### Step 2 — scale each token once, round once (§1, §2)

| Token | Tailwind px | × 0.948611 | Use |
|---|---|---|---|
| `p-8` (page padding) | 32 | 30.36 | **30** |
| `gap-6`, `mt-6` | 24 | 22.77 | **23** |
| `mt-2` | 8 | 7.59 | **8** |
| `p-6` (card padding) | 24 | 22.77 | **23** |
| `h-[180px]` | 180 | 170.75 | **171** |
| `rounded-lg` | 8 | 7.59 | **8** |
| `border` | 1 | 0.95 | **1** |
| `text-3xl` / line-height | 30 / 36 | 28.46 / 34.15 | **28** / **34** |
| `text-lg` / line-height | 18 / 28 | 17.08 / 26.56 | **17** / **27** |
| `text-sm` / line-height | 14 / 20 | 13.28 / 18.97 | **13** / **19** |

### Step 3 — the grid columns (§4)

```
inner   = 1366 - 2 × 30                = 1306
column  = (1306 - (3 - 1) × 23) / 3
        = (1306 - 46) / 3  =  1260 / 3 = 420      exact, no residue
X₁ = 30
X₂ = 30  + (420 + 23)                  = 473
X₃ = 473 + (420 + 23)                  = 916
closing check: 916 + 420 = 1336 = 1366 - 30      OK
```

### Step 4 — the vertical stack (§3, column direction)

Cumulative, starting at the page's top padding:

```
y = 30                                   p-8 top
h1      Y = 30                Height = 34      ->  y = 64
p       Y = 64 + 8  = 72      Height = 19      ->  y = 91      (mt-2 = 8)
grid    Y = 91 + 23 = 114                                      (mt-6 = 23)
row 1   Y = 114               Height = 171     -> bottom 285
row 2   Y = 285 + 23 = 308    Height = 171     -> bottom 479   (gap-6 = 23)
```

### Step 5 — inside one card (§5, coordinates relative to the card)

```
card padding  = 23
card inner W  = 420 - 2 × 23 = 374
h3   X = 23   Y = 23                Width = 374   Height = 27   Size = 17
p    X = 23   Y = 23 + 27 + 8 = 58  Width = 374   Height = 19   Size = 13
```

### Step 6 — the screen's `Height` (§6)

```
content_bottom = 479  (row 2 bottom, the lowest top-level child)
+ bottom p-8   = 30
               = 509   <  768     ->  omit Height
```

Had the mockup carried four rows instead of two:
`row 3 Y = 308 + 171 + 23 = 502`, `row 4 Y = 502 + 171 + 23 = 696`, bottom
`696 + 171 = 867`, plus 30 → 897 > 768 → `Height: =904` (897 rounded up to a
multiple of 8).

### Step 7 — every control, resolved

| Control | Parent | `X` | `Y` | `Width` | `Height` |
|---|---|---|---|---|---|
| `lblTitle` | screen | 30 | 30 | 1306 | 34 |
| `lblSubtitle` | screen | 30 | 72 | 1306 | 19 |
| `grpCard1` | screen | 30 | 114 | 420 | 171 |
| `grpCard2` | screen | 473 | 114 | 420 | 171 |
| `grpCard3` | screen | 916 | 114 | 420 | 171 |
| `grpCard4` | screen | 30 | 308 | 420 | 171 |
| `grpCard5` | screen | 473 | 308 | 420 | 171 |
| `grpCard6` | screen | 916 | 308 | 420 | 171 |
| `lblCardNTitle` | `grpCardN` | 23 | 23 | 374 | 27 |
| `lblCardNMeta` | `grpCardN` | 23 | 58 | 374 | 19 |

Absolute check on card 5's title: 473 + 23 = 496 across, 308 + 23 = 331 down.

### Step 8 — the YAML

Cards 2–6 are card 1 with the `X`/`Y` from the table above; two are shown.
`font-semibold` (600) has no confirmed `FontWeight` member, so it rounds up to
`FontWeight.Bold` — tell the user that is what happened.

```yaml
Screens:
  Templates:
    Properties:
      Fill: =RGBA(244, 244, 246, 1)
    Children:
      - lblTitle:
          Control: Label@2.5.1
          Properties:
            Text: ="Templates"
            Color: =RGBA(24, 28, 35, 1)
            Font: =Font.'Segoe UI'
            FontWeight: =FontWeight.Bold
            Size: =28
            X: =30
            Y: =30
            Width: =1306
            Height: =34
      - lblSubtitle:
          Control: Label@2.5.1
          Properties:
            Text: ="Pick one to start."
            Color: =RGBA(65, 71, 84, 1)
            Font: =Font.'Segoe UI'
            Size: =13
            X: =30
            Y: =72
            Width: =1306
            Height: =19
      - grpCard1:
          Control: GroupContainer@1.5.0
          Variant: ManualLayout
          Properties:
            Fill: =RGBA(255, 255, 255, 1)
            BorderColor: =RGBA(193, 198, 215, 1)
            BorderThickness: =1
            X: =30
            Y: =114
            Width: =420
            Height: =171
            RadiusTopLeft: =8
            RadiusTopRight: =8
            RadiusBottomLeft: =8
            RadiusBottomRight: =8
          Children:
            - lblCard1Title:
                Control: Label@2.5.1
                Properties:
                  Text: ="Onboarding Form"
                  Color: =RGBA(24, 28, 35, 1)
                  Font: =Font.'Segoe UI'
                  FontWeight: =FontWeight.Bold
                  Size: =17
                  X: =23
                  Y: =23
                  Width: =374
                  Height: =27
            - lblCard1Meta:
                Control: Label@2.5.1
                Properties:
                  Text: ="Word document"
                  Color: =RGBA(65, 71, 84, 1)
                  Font: =Font.'Segoe UI'
                  Size: =13
                  X: =23
                  Y: =58
                  Width: =374
                  Height: =19
      - grpCard2:
          Control: GroupContainer@1.5.0
          Variant: ManualLayout
          Properties:
            Fill: =RGBA(255, 255, 255, 1)
            BorderColor: =RGBA(193, 198, 215, 1)
            BorderThickness: =1
            X: =473
            Y: =114
            Width: =420
            Height: =171
            RadiusTopLeft: =8
            RadiusTopRight: =8
            RadiusBottomLeft: =8
            RadiusBottomRight: =8
          Children:
            - lblCard2Title:
                Control: Label@2.5.1
                Properties:
                  Text: ="Consent Form"
                  Color: =RGBA(24, 28, 35, 1)
                  Font: =Font.'Segoe UI'
                  FontWeight: =FontWeight.Bold
                  Size: =17
                  X: =23
                  Y: =23
                  Width: =374
                  Height: =27
            - lblCard2Meta:
                Control: Label@2.5.1
                Properties:
                  Text: ="Word document"
                  Color: =RGBA(65, 71, 84, 1)
                  Font: =Font.'Segoe UI'
                  Size: =13
                  X: =23
                  Y: =58
                  Width: =374
                  Height: =19
```

`scripts/validate.py` lints this block on every run, so it cannot drift out of date.
