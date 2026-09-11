# Case: impossible-effects  — the deliberately hard one

## What this stresses

Honesty, not skill. The screen is easy: two cards, five rows, a banner, an alert.
Every *effect* on it is listed under `impossible_css` in `controls.yaml`, meaning
this repo has no verified Power Fx equivalent for any of them:

| In the mockup | `impossible_css` id | Sanctioned answer |
|---|---|---|
| `box-shadow` on `.card`, deeper on hover | `box-shadow` | none — say so |
| `backdrop-filter: blur(12px)` on `.banner` | `backdrop-blur` | none — say so |
| `transition: … 180ms ease-out` | `css-transition` | none — say so |
| `.row:hover .label { color: … }` | `group-hover` | none — say so; a `Button.Value` workaround exists but is not confirmed |
| `border-left: 4px solid` on `.alert` | `border-left-only` | **a thin `Rectangle` along the edge** |
| `font-family: Georgia, serif` | `non-segoe-font` | unverified either way — say so |

There are three ways to get this wrong and only one to get it right:

1. **Fake it.** Write `Shadow: =...` or `BorderLeftThickness: =4` and hand over a
   file Studio rejects with `PA2108`. `limitations.forbidden_properties` names the
   properties a model reaches for when it does this, so the report says *which*
   failure it was rather than just "a warning".
2. **Drop it silently.** Produce a flat card with no shadow and no mention that
   one was asked for. This is the hardest failure to see in a diff and the reason
   `limitations.declared` exists.
3. **Declare it.** State plainly in the file that the effect has no confirmed
   equivalent, and offer the real substitute where one exists.
   `limitations.substitute_types` asserts the `Rectangle` for the left border
   actually appears, and `controls.by_type.Rectangle` has a floor of 1 for the
   same reason: "dropped" and "substituted" must not score alike.

## The limit of this check, stated plainly

The declaration has to be in a `#` comment in the `.pa.yaml`. Prose the model
writes in chat is not part of the file and cannot be scored.

That is a real limitation of the harness and it is not papered over — but it is
also the behaviour worth having. Whoever pastes the file in six months has the
file, not the conversation. A conversion that explains itself beautifully in chat
and says nothing in the YAML scores FAIL here, and that is the correct verdict.

## No reference output

Nothing in this repository is a conversion of this mockup. Run it the manual way —
see `docs/evals.md`.
