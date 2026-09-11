# Case: multi-section-form

## What this stresses

Field-type fidelity and vertical overflow — the two things a form conversion gets
wrong.

- **`<select>` is not `<input>`.** Sixteen of the twenty-one fields are text
  inputs and five are selects, and they look nearly identical in a rendered
  mockup: same box, same border, same height. Turning a select into a
  `Classic/TextInput` produces a screen that pastes cleanly, looks right, and
  silently loses the constrained choice. That is why `Classic/DropDown` has its
  own `required_types` entry and its own 3–8 range rather than being folded into a
  generic "input" count.
- **The content runs to about 2032px on a 768px canvas.** The screen has to
  declare `Height:`, which is why `structure.required_screen_properties` asks for
  it here and deliberately does not in `shell-with-form`. A conversion that omits
  it produces a screen whose bottom two-thirds cannot be reached.
  `geometry.in-bounds` reads the screen's own `Height` when one is set, so
  declaring a tall screen is never punished — only failing to declare it is.
- **Five structurally identical cards.** The temptation is to write card 1 in full
  and abbreviate the rest. The 55–130 `controls.total` range is the guard: an
  abbreviated file lands under it.
- **`Gallery` and `Form` are forbidden.** They are the controls a Power Apps
  developer would actually reach for, and this repo has no evidence for either —
  both sit in `controls.yaml`'s `unattempted_controls`. They belong in an isolated
  test snippet from `assets/test-snippets/`, never in a file handed over as ready
  to paste. `controls.forbidden_types` makes that mechanical.
- **Two-column arithmetic inside a padded card.** Each field is 479 wide inside a
  1038-wide card with 24px padding and a 32px gutter: 24 + 479 + 32 + 479 + 24 =
  1038. The row has to close exactly, and `geometry.in-bounds` catches it when it
  does not.

## Reference output

`skills/power-app-yaml/assets/examples/example-form.yaml` — 87 controls, screen
`Height: =2032`. **Not model output**: a hand-written screen used so the scorer
can be exercised in CI without running a model. The mockup in this directory was
written to match it field for field (16 inputs, 5 selects, 5 cards), so the ranges
are tight enough to mean something.

No known deviations — it scores clean.
