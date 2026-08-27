# Troubleshooting

When Power Apps Studio rejects a paste, the first job is to sort the message into
**blocking error** or **non-blocking warning**. Do not panic-fix a warning, and
do not wave away a real error.

## Studio message codes

| Code | Bucket | Meaning | What to do |
|---|---|---|---|
| `PA1001` | **Error — blocks the whole paste** | Invalid schema / malformed structure | Fix the structure. Usually a missing `Screens:` wrapper, a value that does not start with `=`, or inline `{ }` flow-style `Properties`. |
| `PA2108` | **Error — blocks the whole paste** | Unknown property on a control | Remove or correct that property. It is not confirmed for this control/version — paste-test it in isolation before trusting it. |
| `PA2105` | Warning — non-blocking | Control version is older than the one Studio ships | Ignore, or bump the `@x.y.z` to the version Studio names. Studio auto-substitutes. |
| `PA2106` | Warning — non-blocking | Control version is newer than the one Studio ships | Ignore, or lower the `@x.y.z`. Studio auto-substitutes. |

If you see a code not listed here, treat it as blocking until proven otherwise
and [open an issue](https://github.com/YKUNAKORN/power-app-yaml/issues/new?template=control-report.yml).

## Common paste failures

### "Nothing pastes" / `PA1001`

- **No full wrapper.** The file must be `Screens:` → `<ScreenName>:` →
  `Properties:` / `Children:`. A bare control never pastes.
- **A value without `=`.** Every property value starts with `=`: `Text: ="hi"`,
  `X: =0`, `Fill: =RGBA(244, 244, 246, 1)`.
- **Flow-style `Properties`.** `{X: =0, Fill: =RGBA(1,1,1,1)}` breaks because the
  commas inside `RGBA(...)` are parsed as YAML separators. Use block style.

### An unknown-property error (`PA2108`)

The control type is fine but one property is not recognised at that version.
Delete the offending line, re-paste, and add the property back only after an
isolated paste-test confirms it. Update your catalog with the result.

### Controls overlap instead of nesting

Visual overlap in Studio does **not** nest controls. A child control must sit
inside a real `Children:` key on its parent `GroupContainer`.

### `Navigate()` does nothing / errors

`OnSelect: =Navigate('Target', ScreenTransition.Fade)` only works if a screen
literally named `Target` exists in the app. If it does not yet, use a placeholder
and wire it up after both screens are pasted.

### A CSS effect did not come through

Some effects have no confirmed Power Fx equivalent: box shadows, `backdrop-blur`,
CSS transitions/animations, `group-hover`, and true one-sided borders. The skill
will say so and offer the closest real substitute (for example, a thin
`Rectangle` standing in for a left border) rather than faking a property.

## Still stuck?

Open a [bug report](https://github.com/YKUNAKORN/power-app-yaml/issues/new?template=bug_report.yml)
with the `.pa.yaml`, the exact Studio message, and your Studio version
(Studio → `?` → About).
