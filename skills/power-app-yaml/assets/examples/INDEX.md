# Example index — read a slice, not the whole file

These three files are real, working `.pa.yaml` screens. They are also big:
1,732 + 1,124 + 378 = 3,234 lines. Reading one in full costs more context than the
rest of the skill combined, and most of those lines are the same block repeated.

**Order of preference: a pattern file, then a slice from here, then the whole file.**

1. Try `assets/patterns/` first — 13 extracted 30–85 line snippets, each already
   lint-clean. Most conversions need nothing else.
2. If you need to see a pattern *in situ* (surrounding coordinates, how regions
   compose), read one line range from the tables below:
   `sed -n '29,113p' assets/examples/example-card-grid.yaml`.
3. Read a whole file only when you need the complete coordinate system of a screen
   archetype you are reproducing closely.

Line numbers are for the files as committed. If you edit an example, re-derive them
(`grep -n '^      - ' <file>`) rather than trusting these.

---

## example-app-shell.yaml — 378 lines

The application chrome: a 280-wide white sidebar with four nav rows, a top bar with
the signed-in user, a centred headline pair, four large tile buttons in a 2×2 block,
and a three-segment progress indicator. Laid out on a 1366 × 768 canvas that fits the
viewport — the screen sets no `Height`. This is the file to slice when the mockup has
persistent navigation. Every nav row is a `Classic/Button` with a separate
`Classic/Icon` drawn on top; the current row additionally has a 4 × 48 `Rectangle`
against the left edge.

| Control | Count |
|---|---|
| `Classic/Button@2.2.0` | 9 |
| `Label@2.5.1` | 5 |
| `Rectangle@2.3.0` | 4 |
| `Classic/Icon@2.5.0` | 4 |
| `GroupContainer@1.5.0` | 2 |
| `Image@2.2.3` | 1 |
| **total** | **25** |

| Lines | Region | Pattern file |
|---|---|---|
| 1–5 | Screen wrapper, viewport-height (no `Height`) | `screen-shell` |
| 6–17 | Sidebar `GroupContainer` properties (280 × 768) | — |
| 18–30 | Logo `Label`, centred in the sidebar | — |
| 31–56 | **Active nav row**: Button + `recNavActiveIndicator` | `sidebar-nav-item` |
| 57–117 | Three inactive nav rows (Y 152 / 200 / 248) | `sidebar-nav-item` |
| 118–155 | The four nav icons, X 16, Y = row Y + 12 | `sidebar-nav-item` |
| 156–168 | Top-bar `GroupContainer` (X 280, 1086 × 64) | `top-bar` |
| 169–200 | **Avatar row**: name + role + 40 × 40 avatar | `avatar-row` |
| 201–224 | Centred headline (26 Bold) + subheadline (14) | `section-header` |
| 225–248 | Three-segment progress bar (48 × 4 and 8 × 4) | `divider` |
| 249–274 | Outlined secondary CTA with `Navigate()` | `footer-nav` |
| 275–378 | Four 420 × 128 tile buttons, 2 × 2 (X 387/839, Y 247/402) | — |

---

## example-form.yaml — 1,124 lines

A five-card scrolling request form inside the same shell. Screen `Height: =2032`
because the content runs well past 768. Each card is a bordered white
`GroupContainer` at X 304, 1038 wide, opened by a numbered badge and a title, then
filled with label-over-input pairs in two 479-wide columns. Card 3 is the widest
sample of field types (four text inputs, three dropdowns, a postcode). Slice this
file for anything form-shaped; the five cards are structurally identical, so read one.

| Control | Count |
|---|---|
| `Label@2.5.1` | 37 |
| `Classic/TextInput@2.3.2` | 16 |
| `Rectangle@2.3.0` | 10 |
| `GroupContainer@1.5.0` | 8 |
| `Classic/Button@2.2.0` | 6 |
| `Classic/DropDown@2.3.1` | 5 |
| `Classic/Icon@2.5.0` | 4 |
| `Image@2.2.3` | 1 |
| **total** | **87** |

| Lines | Region | Pattern file |
|---|---|---|
| 1–6 | Screen wrapper with `Height: =2032` (scrolls) | `screen-shell` |
| 7–16 | Page title (26 Bold) | `section-header` |
| 17–32 | **Card 1** `GroupContainer` properties (1038 × 288 at Y 168) | `card-container` |
| 33–53 | Numbered badge: 32 × 32 Rectangle + centred Label | `badge` |
| 54–64 | Card title (20 Bold) at X 80, clear of the badge | `section-header` |
| 65–92 | **One text field**: Label (Y 96) + TextInput (Y 120) | `form-field-text` |
| 93–120 | The same field in column 2 (X 527) | `two-column-split` |
| 121–145 | **One dropdown field**: Label + `Classic/DropDown` | `form-field-dropdown` |
| 146–173 | Fourth field, row 2 column 2 | `two-column-split` |
| 174–333 | Card 2 — four text fields, same skeleton | — |
| 334–624 | Card 3 — the biggest card: 5 inputs + 3 dropdowns, 1038 × 464 | — |
| 625–752 | Card 4 — two inputs + one dropdown | — |
| 753–800 | Card 5 header (badge + title) | `badge` |
| 801–818 | Tinted info/callout box: Rectangle + Label on top | — |
| 819–843 | Multiline remark field (`TextInput`, `Height: =100`) | `form-field-text` |
| 844–857 | Footer `GroupContainer` (X 280, 1086 × 80 at Y 1951) | `footer-nav` |
| 858–867 | Footer status Label | `footer-nav` |
| 868–903 | **Secondary + primary footer buttons** | `footer-nav` |
| 904–1055 | Sidebar (same as app-shell, renamed `_7`) | `sidebar-nav-item` |
| 1056–1100 | Top bar + avatar row | `top-bar`, `avatar-row` |
| 1101–1124 | Progress indicator segments | `divider` |

---

## example-card-grid.yaml — 1,732 lines

A 17-row selectable checklist. One 1038 × 96 white card per row on a 112px pitch,
each holding an icon box, a title/subtitle pair, a checkbox `Rectangle` whose `Fill`
is an `If()` over a per-row variable, a check `Icon` gated by `Visible`, and a
transparent full-card `Button` that toggles the variable. Screen `Height: =2232`.

**Rows 2–17 are byte-for-byte the same block with a different name, variable, `Text`
and `Y`.** The entire pattern is in lines 29–113 — roughly 5% of the file. There is
almost never a reason to read past line 113 except for the shell at the end.

| Control | Count |
|---|---|
| `Label@2.5.1` | 39 |
| `Rectangle@2.3.0` | 38 |
| `Classic/Icon@2.5.0` | 38 |
| `Classic/Button@2.2.0` | 23 |
| `GroupContainer@1.5.0` | 19 |
| `Image@2.2.3` | 1 |
| **total** | **158** |

| Lines | Region | Pattern file |
|---|---|---|
| 1–6 | Screen wrapper with `Height: =2232` (scrolls) | `screen-shell` |
| 7–28 | Page title (26 Bold) + subtitle (12) | `section-header` |
| 29–42 | Row-1 card `GroupContainer` (1038 × 96 at Y 208) | `card-container` |
| 43–59 | Icon box: 48 × 48 Rectangle + 24 × 24 Icon inside it | `badge` |
| 60–82 | Title (14 Bold) + subtitle (12 at 60% alpha), X 88 | — |
| 83–100 | **Selection state**: `If()` Fill + `Visible`-gated check Icon | `tile-grid-cell` |
| 101–113 | **Transparent click overlay** with `Set(var, !var)` | `tile-grid-cell` |
| 114–1473 | Rows 2–17 — identical, 112px apart. Skip. | — |
| 1474–1625 | Sidebar, with the indicator on row 2 (Y 152) | `sidebar-nav-item` |
| 1626–1670 | Top bar + avatar row | `top-bar`, `avatar-row` |
| 1671–1708 | Back / Next buttons placed on the screen, not in a footer | `footer-nav` |
| 1709–1732 | Progress indicator segments | `divider` |

---

## Cross-file shell comparison

The sidebar, top bar and progress indicator appear in all three files with `_N`
suffixes. They are the same geometry every time, so read whichever copy you are
already near:

| Region | app-shell | form | card-grid |
|---|---|---|---|
| Sidebar | 6–155 | 904–1055 | 1474–1625 |
| Top bar | 156–200 | 1056–1100 | 1626–1670 |
| Progress dots | 225–248 | 1101–1124 | 1709–1732 |
