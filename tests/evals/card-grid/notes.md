# Case: card-grid

## What this stresses

Repetition at a scale where abbreviating is tempting, and per-row state.

- **Seventeen rows, and all seventeen have to be there.** This is the case a model
  is most likely to fake: write three rows, then a comment saying "repeat this
  block for the remaining fourteen". That file does not paste into a working
  screen, and it is not obvious from reading the first page of it. The 95–230
  `controls.total` range is the assertion — an abbreviated file lands far under it.
  Within the range, how many controls each row costs is a real design choice (the
  reference spends 8; a leaner reading could spend 5), which is why the window is
  the widest of the five cases.
- **`Gallery` is forbidden, and this is where that hurts.** Seventeen identical
  rows bound to a list is exactly what a `Gallery` is for, and any Power Apps
  developer would reach for one. This repo has no evidence that a `Gallery` pastes
  from YAML at all — it is in `controls.yaml`'s `unattempted_controls`, and
  `assets/test-snippets/gallery.pa.yaml` exists precisely so somebody can settle it
  in Studio. Until then, the honest output is seventeen explicit rows.
- **Per-row selection state.** Each row is a click target that toggles its own
  checkbox. The reference does it with a transparent full-card `Classic/Button`
  running `Set(varRow1, !varRow1)`, a `Rectangle` whose `Fill` is an `If()` over
  that variable, and a check `Icon` gated by `Visible`. The `Classic/Button` range
  (17–32) asserts there is a click target per row, not just per screen.
- **A fixed 112px pitch over 17 rows.** Row *n* sits at `208 + 112(n-1)`. One
  arithmetic slip compounds down the file, and the screen `Height: =2232` has to
  cover the result. `geometry.in-bounds` is the check that notices.

## Reference output

`skills/power-app-yaml/assets/examples/example-card-grid.yaml` — 158 controls,
screen `Height: =2232`. **Not model output**: a hand-written screen used so the
scorer can be exercised in CI without running a model. The mockup here reproduces
its 17 row titles so the counts line up.

No known deviations — it scores clean.
