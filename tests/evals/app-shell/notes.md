# Case: app-shell

## What this stresses

Persistent chrome. The whole screen is chrome — a fixed 280px sidebar, a top bar
across the remaining 1086px, and a content block centred inside that remainder.
Nothing here is hard arithmetic; what it tests is whether the conversion keeps
one coordinate system straight across three regions that are each anchored to a
different edge.

Specifically:

- **Nav rows have to be buttons.** The mockup draws them as `<a>` with plain text
  and a coloured background. SKILL.md rule 5 says a nav row is a
  `Classic/Button@2.2.0` regardless, because it has to be clickable. A conversion
  that reads "text on a background" and writes a `Label` produces a screen that
  looks right and navigates nowhere — the exact silent failure the skill exists to
  prevent. `controls.required_types` asserts at least one Button; the 7–16 range
  asserts there are enough of them for four nav rows, four tiles and the CTA.
- **The active-row indicator is a 4 × 48 strip against the left edge**, which is a
  one-sided border by another name. The sanctioned answer is a thin `Rectangle`,
  and the range on `Rectangle` leaves room for it plus the three progress segments.
- **`Navigate()` goes to screens that do not exist in a single-screen file.** That
  is legitimate — SKILL.md rule 7 allows the placeholder — but only if the line
  says so in a comment. `navigation.targets-resolve` is what makes the difference
  between "acknowledged gap" and "dangling link" checkable.
- **Everything fits 768px.** The screen sets no `Height`, so
  `structure.required_screen_properties` asks only for `Fill`. A conversion that
  adds a `Height` has misread the layout, and `geometry.in-bounds` will not catch
  that on its own — it is the one thing here a human reviewer still has to look at.

## Reference output

`skills/power-app-yaml/assets/examples/example-app-shell.yaml` — 25 controls. It
is **not model output**: it is a hand-written screen that predates the eval
harness, used so the scorer can be exercised in CI without running a model.

It carries three known deviations, all the same five `FontWeight` properties on
`Classic/Button`. `controls.yaml` confirms `FontWeight` on `Label` only and marks
it explicitly unverified on `Button`, while this file uses it — a contradiction
recorded in the 0.2.0 known issues and still open, because settling it needs a
Studio paste test nobody has run. The file tags each one `# UNVERIFIED`, which is
why `catalog.untagged-unverified` passes: the guess is labelled, not hidden.

Delete the waivers from `expectations.yaml` when a Studio result settles it.
