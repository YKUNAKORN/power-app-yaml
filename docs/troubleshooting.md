# Troubleshooting

Two different things can tell you something is wrong, and they are not the same
thing:

- **`scripts/pa_lint.py`** — runs offline, before the file goes anywhere, and ends
  in a `VERDICT:` line.
- **Power Apps Studio** — runs on paste, and reports `PA` codes.

The linter is an approximation of Studio, built from the bundled v3.0 schema and
this repo's catalog of paste-tested controls. A clean verdict makes a clean paste
likely, not certain. Where they disagree, **Studio is right** — and that
disagreement is worth
[reporting](https://github.com/YKUNAKORN/power-app-yaml/issues/new?template=control-report.yml),
because it is how the catalog improves.

## Table of contents

- [The linter's verdict lines](#the-linters-verdict-lines)
- [The four layers, and what each one maps to](#the-four-layers-and-what-each-one-maps-to)
- [Studio message codes](#studio-message-codes)
- [Common paste failures](#common-paste-failures)
- [Still stuck?](#still-stuck)

## The linter's verdict lines

Every run of `python scripts/pa_lint.py FILE` ends in exactly one of these four.

| Verdict | Exit | Means | What to do |
|---|---|---|---|
| `VERDICT: SAFE TO PASTE` | 0 | Every layer ran and found nothing. | Paste it. This is the only verdict that means go. |
| `VERDICT: PASTES, BUT n UNVERIFIED ITEM(S)` | 0 | No blocking error. `n` things are not in the catalog, or break a SKILL.md convention. | Read the warnings. Each one names the control and, for an unverified control or property, ships a one-control snippet to paste-test in isolation first. |
| `VERDICT: WILL FAIL — n blocking error(s)` | 1 | The file is not valid YAML, or the schema rejects it. | Fix it. Studio will refuse this file. Do not hand it to anyone. |
| `VERDICT: UNPROVEN — schema layer skipped` | 0 | `jsonschema` is not installed, so the layer that catches `PA1001` never ran. | `pip install jsonschema` and run it again. |

Two of those deserve more than a table row.

### `PASTES, BUT n UNVERIFIED ITEM(S)` is not a failure

It is the normal verdict for any file that uses something this repo has no Studio
evidence for. The catalog records **positive results only** — a control or
property missing from it is untested, not unsupported — so "unverified" means "we
do not know", and the file may well paste perfectly.

What it is not is something to ignore. Each warning names an item and, where it
can, generates an isolated snippet: one control, one property per line, in a
complete `Screens:` wrapper. Paste that snippet on a scratch screen first. If it
works, you have learned something the catalog did not know, and
[`docs/harvesting.md`](harvesting.md) explains how to fold it in.

### `UNPROVEN` is deliberately not `SAFE`

Without `jsonschema`, layer L1 cannot run, and L1 is the one that catches the
error which blocks a whole paste. Reporting "safe" at that point would be a claim
the run cannot back up, so the linter refuses to make it — even though there were
no findings. `pip install jsonschema` fixes it.

`--strict` treats warnings **and** an unproven run as failures (exit 2), which is
what you want in a script. `--quiet` prints only the verdict line.

## The four layers, and what each one maps to

| Layer | Severity | Checks | Studio equivalent |
|---|---|---|---|
| **L0** | error | The file parses as YAML. Special-cased: flow-style `Properties` containing `RGBA(...)`. | A paste that silently does nothing. |
| **L1** | error | Microsoft's bundled `pa.yaml` v3.0 schema. | `PA1001`. |
| **L2** | warning | This repo's control catalog: unverified control types (`L2.unverified-control-type`), types Microsoft's own tooling lists but this repo has never paste-tested (`L2.candidate-control-type`), unverified properties (`L2.unverified-property`). | `PA2108`, usually. |
| **L3** | warning | SKILL.md's own rules: `Navigate()` to a screen that is not here, duplicate control names, child `X`/`Y` under a non-`ManualLayout` container, an unverified item with no `# UNVERIFIED` comment. | Nothing. Studio accepts all of these, which is exactly why they are worth catching here. |

The L3 checks are the ones with no Studio counterpart, and they are the expensive
failures: a duplicate control name is silently renamed to `_1` on paste, so the
names you wrote and the names in the app quietly diverge. Nothing errors. The app
is just subtly wrong.

`L2.candidate-control-type` carries the same severity and the same requirements as
`L2.unverified-control-type`. Appearing in Microsoft's control-id enum is a
wording aid — "known to Microsoft's tooling but not paste-tested here" reads
better than "unknown control" — and never evidence.

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

The linter catches all three at L0/L1 — if a file reached Studio and failed this
way, it was not linted.

### An unknown-property error (`PA2108`)

The control type is fine but one property is not recognised at that version.
Delete the offending line, re-paste, and add the property back only after an
isolated paste-test confirms it. Update your catalog with the result.

This is the code the linter's L2 layer is trying to predict, and the snippets it
generates exist to make the bisect cheap: one control, one property per line, so
you delete downward until it passes and the last line you deleted is the culprit.

### Controls overlap instead of nesting

Visual overlap in Studio does **not** nest controls. A child control must sit
inside a real `Children:` key on its parent `GroupContainer`, and that container
must be `Variant: ManualLayout` — under any other variant the child `X`/`Y` are
ignored and the screen lays out differently from the mockup.
`L3.xy-in-non-manual-container` catches that offline.

### `Navigate()` does nothing / errors

`OnSelect: =Navigate('Target', ScreenTransition.Fade)` only works if a screen
literally named `Target` exists in the app. If it does not yet, keep the
placeholder and say so in a comment on the same line:

```yaml
OnSelect: =Navigate('Settings', ScreenTransition.Fade)  # placeholder - not built yet
```

The comment is not decoration. `L3.navigate-target-missing` treats a commented
placeholder as deliberate and an uncommented one as a dangling link, which is the
only mechanical difference between the two.

### A control got renamed to `name_1`

Two controls in one screen had the same name. Studio renames the second silently
on paste — no error, no warning. `L3.duplicate-control-name` catches it before
that happens.

### Pasting into an app that already exists went subtly wrong

Name collisions, `Navigate()` to screens that were never there, and a second
hard-coded copy of the palette next to the theme variables `App.OnStart` already
defines. All three succeed and are wrong. Run
`python scripts/app_inventory.py <Src-folder-or-.msapp>` first and follow
[`extend-existing-app.md`](../skills/power-app-yaml/references/extend-existing-app.md).

### A CSS effect did not come through

Some effects have no confirmed Power Fx equivalent: box shadows, `backdrop-blur`,
CSS transitions/animations, `group-hover`, true one-sided borders, and any
non-`Segoe UI` font. The full list is `impossible_css` in
[`controls.yaml`](../skills/power-app-yaml/references/controls.yaml).

The skill will say so and offer the closest real substitute (for example, a thin
`Rectangle` standing in for a left border) rather than faking a property. If you
get a file that silently dropped one of these, or that invented a `Shadow:`
property to fake it, that is a bug worth reporting — it is exactly what the
`impossible-effects` eval case exists to catch (see [`evals.md`](evals.md)).

## Still stuck?

Open a [bug report](https://github.com/YKUNAKORN/power-app-yaml/issues/new?template=bug_report.yml)
with the `.pa.yaml`, the exact Studio message, and your Studio version
(Studio → `?` → About). The linter's `--json` output is useful to attach:

```bash
python scripts/pa_lint.py myscreen.pa.yaml --json > lint.json
```
