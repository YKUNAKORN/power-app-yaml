# Case: shell-with-form

## What this stresses

The seam. `app-shell` and `multi-section-form` each test one layout idiom in
isolation; this case puts three in the same coordinate space and checks they still
add up.

- **Three different derivations, one canvas.** The sidebar's coordinates come from
  a fixed-position box anchored to the left edge. The form column's come from a
  wrapping flex grid with a 24px row gap and a 24px column gap. The summary
  panel's come from a stack of 28px rows with a 1px rule in the middle. Each is a
  different section of `layout-mapping.md`, and the answers have to land in one
  absolute coordinate system without overlapping.
- **The two-column split has to close.** `304 + 686 + 24 + 328 = 1342`, and the
  right edge of the content area is at `1342`, inside the 1366 canvas with the
  24px right margin the other cases use. Get the gutter wrong and the summary
  panel either overlaps the form or runs off the canvas — `geometry.in-bounds`
  catches the second, and the control counts will not catch the first, which is
  noted honestly rather than claimed.
- **Read-only text is not a field.** The summary panel is five rows of label/value
  text that look like a form when rendered. Converting them to
  `Classic/TextInput` would give the user five editable boxes where the mockup
  shows a receipt. The `Classic/TextInput` range is 3–8 — three inputs exist in
  the mockup, and eight leaves room for a different but defensible reading, while
  a conversion that turns the summary into fields lands well past it.
- **Nothing scrolls.** Unlike `multi-section-form`, everything fits 768px, so
  `structure.required_screen_properties` asks only for `Fill`. Declaring a
  `Height` here is a misread — which is the mirror image of the mistake the form
  case tests, and the reason both cases exist.

## No reference output

Nothing in this repository is a conversion of this mockup, and writing one by hand
would mean scoring an answer against itself. Run this case the manual way — see
`docs/evals.md`.
