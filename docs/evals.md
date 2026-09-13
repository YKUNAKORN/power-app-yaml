# Evals — telling better from worse

Every earlier phase of this project answered "is this file valid?". `pa_lint.py`
proves a `.pa.yaml` will paste. It cannot tell you whether the screen is the one
the mockup showed, and it cannot tell you whether a change you just made to
`SKILL.md` helped or hurt.

This is the part that can. It is small, and the boundary around it is the most
important thing on this page.

## Table of contents

- [What is automated and what is not](#what-is-automated-and-what-is-not)
- [The loop, in three commands](#the-loop-in-three-commands)
- [Reading the table](#reading-the-table)
- [What a case asserts](#what-a-case-asserts)
- [The five cases](#the-five-cases)
- [Comparing two runs](#comparing-two-runs)
- [What the harness cannot see](#what-the-harness-cannot-see)
- [Adding a case](#adding-a-case)
- [The self-check CI runs](#the-self-check-ci-runs)

## What is automated and what is not

`scripts/run_eval.py` is a **scorer**, not an eval loop. It takes a `.pa.yaml`
that already exists and checks it against assertions that can be settled
mechanically.

It does not produce that file. Producing it means giving a model a mockup and
asking for a conversion, and **CI does not run a model**. There is deliberately
no API-key step in the scorer and none in `.github/workflows/validate.yml`,
because a harness that quietly depended on a key would be an eval loop in name
only — green on every run where the key happened to be missing, and nobody the
wiser.

So:

| Step | Who does it |
|---|---|
| Give Claude `mockup.html`, get a `.pa.yaml` back | you, by hand |
| Save the answer to a file | you, by hand |
| Score the file against the case | `scripts/run_eval.py` |
| Score the bundled references, to prove the scorer works | CI, on every push |

The manual half is two minutes of work per case. It is manual because the
alternative is a green checkmark that means nothing.

## The loop, in three commands

```bash
# 1. Ask Claude to convert one case's mockup. In a session with the skill loaded:
#
#       Convert tests/evals/app-shell/mockup.html to pa.yaml.
#
# 2. Save the .pa.yaml it hands back.
#    (Save the whole file, including any comments — the scorer reads them.)

# 3. Score it.
python scripts/run_eval.py /tmp/app-shell-run1.pa.yaml --case tests/evals/app-shell
```

`--case` is required when you pass a file: the scorer never guesses which case an
output belongs to.

List what is available:

```bash
python scripts/run_eval.py --list
```

## Reading the table

```
RESULT  CHECK                             EXPECTED         ACTUAL
PASS    controls.by_type:Classic/Button   7-16             9
FAIL    lint.verdict                      safe             unverified
          -> VERDICT: PASTES, BUT 5 UNVERIFIED ITEM(S)
```

| Result | Meaning |
|---|---|
| `PASS` | The assertion held. |
| `FAIL` | It did not. This is the only result that means something is wrong. |
| `XFAIL` | It did not hold, and the case says so in advance with a reason. Reference runs only — see [the self-check](#the-self-check-ci-runs). |
| `XPASS` | A declared deviation stopped failing. The waiver is stale; delete it. Counts as a failure so it cannot be ignored. |
| `UNPROVEN` | The evidence could not be gathered. Almost always `jsonschema` not installed, which disables the layer that catches `PA1001`. Never silently counted as a pass. |
| `SKIP` | The case does not assert this. Not a result, just a reminder of what is unmeasured. |

Exit code is `0` when nothing is `FAIL` or `XPASS`, `1` when something is, and
`2` for a usage or file error. `--json` emits the same rows for scripting.

## What a case asserts

A case is a directory under `tests/evals/`:

```
tests/evals/app-shell/
├── mockup.html          the input — small, self-contained, no external assets
├── expectations.yaml    the assertions
└── notes.md             what this case is meant to stress, in prose
```

`expectations.yaml` has seven optional blocks. Anything you leave out is reported
`SKIP`, never assumed.

| Block | Asserts |
|---|---|
| `structure` | how many screens, and which screen properties must be present |
| `lint` | `pa_lint.py`'s verdict code, error and warning ceilings, per-check budgets |
| `controls` | total count, per-type counts, types that must appear, types that must not |
| `geometry` | every `X`/`Y`/`Width`/`Height` inside the canvas; how many may be non-numeric |
| `navigation` | how many `Navigate()` calls, and that every target resolves |
| `catalog` | how many unverified items may go untagged, how many unverified properties are allowed at all |
| `limitations` | which `impossible_css` effects must be named in a comment, which invented property names must not appear, which substitute controls must |

**Every count is a range.** Two good conversions of the same mockup will not agree
on control count — one draws a divider with a `Rectangle`, another leaves it out —
so an exact number would score style rather than correctness. The ranges are wide
enough to admit any sane reading of the mockup and narrow enough to catch an
output that dropped a region or padded it with filler.

A few details worth knowing:

- **`geometry.in_bounds` reads the screen's own `Height`** when the output sets
  one, and the canvas height otherwise. A screen that correctly declares
  `Height: =2232` because its content scrolls is not punished for it.
- **A geometry value that is not a plain number is counted, never guessed at.**
  `Width: =Parent.Width - 40` is legitimate, but placing it on the canvas would
  mean evaluating Power Fx, which this scorer never does. `geometry.max_unresolved`
  is the budget for those.
- **`navigation.targets_resolve` accepts a commented placeholder**, per SKILL.md
  rule 7. A single-screen deliverable cannot contain the screen it navigates to;
  what it can do is say so on the line.
- **`catalog.max_untagged_unverified` reuses `pa_lint`'s L3 check** rather than
  reimplementing "an unverified item with no `# UNVERIFIED` comment", so the two
  cannot drift apart.

## The five cases

| Case | Stresses | Reference output |
|---|---|---|
| [`app-shell`](../tests/evals/app-shell/notes.md) | persistent chrome; nav rows that must be Buttons, not Labels | `example-app-shell.yaml` |
| [`multi-section-form`](../tests/evals/multi-section-form/notes.md) | `<select>` vs `<input>` fidelity; a screen that must declare `Height` | `example-form.yaml` |
| [`card-grid`](../tests/evals/card-grid/notes.md) | 17 repeated rows without abbreviating; per-row state; no `Gallery` | `example-card-grid.yaml` |
| [`shell-with-form`](../tests/evals/shell-with-form/notes.md) | the seam — three layout idioms in one coordinate space | none |
| [`impossible-effects`](../tests/evals/impossible-effects/notes.md) | honesty: declare the limitation, or fake it | none |

`impossible-effects` is the one that matters most and the one a scorer is least
obviously able to check. Every effect in its mockup is listed under
`impossible_css` in `controls.yaml`, so there is no right conversion — only a
right disclosure. The case asserts that each effect is **named in a comment in the
produced file**, that none of the invented property names a model reaches for
(`BoxShadow`, `BorderLeftThickness`, `Transition`, …) appear, and that the
sanctioned substitute for the one-sided border — a thin `Rectangle` — is actually
there, so "dropped it" and "substituted it" do not score alike.

## Comparing two runs

The harness exists to answer one question: *did that change to `SKILL.md` make
output better or worse?* The procedure is the boring one.

1. Before the change, run every case once and keep the outputs and the tables.
2. Make the change.
3. Run the same cases again with the same prompts.
4. Diff the tables.

```bash
for c in app-shell multi-section-form card-grid shell-with-form impossible-effects; do
  python scripts/run_eval.py "runs/before/$c.pa.yaml" --case "tests/evals/$c" --json \
    > "runs/before/$c.json"
done
# ... make the change, regenerate, then:
diff <(jq -r '.results[0].rows[] | "\(.check) \(.result)"' runs/before/app-shell.json) \
     <(jq -r '.results[0].rows[] | "\(.check) \(.result)"' runs/after/app-shell.json)
```

Two honest cautions about that number:

- **One run per case is a sample of one.** Model output varies between runs on the
  same prompt. A single row flipping from PASS to FAIL is weak evidence; the same
  row flipping across three runs is worth acting on.
- **A row that goes from PASS to PASS tells you nothing about what changed inside
  the range.** Control counts moving from 25 to 38 while both sit inside 16–40 is
  invisible to the table and may matter. `--json` carries the actual numbers; look
  at them when a change was supposed to affect size.

## What the harness cannot see

Stated plainly, because a scorer that oversells itself is worse than no scorer:

- **Whether the screen looks like the mockup.** Nothing here renders anything.
  Colours, fonts, alignment, spacing rhythm, and visual hierarchy are all
  unmeasured. A conversion that puts every control in the right coordinate space
  with the wrong colours scores full marks.
- **Whether the file actually pastes into Studio.** `pa_lint.py` checks the
  bundled v3.0 schema and this repo's catalog, both of which are approximations of
  what Studio enforces. Only a paste test settles it.
- **Prose.** A conversion that explains its limitations beautifully in chat and
  says nothing in the YAML scores FAIL on `limitations.declared`, and that is the
  intended verdict — whoever pastes the file in six months has the file, not the
  conversation.
- **Whether a control is the *right* control**, beyond the type counts. Using a
  `Label` where a `Classic/Button` belongs is caught because the counts move; using
  the wrong one of two Labels is not.

## Adding a case

1. `mkdir tests/evals/<name>` and write a **small, self-contained** `mockup.html`
   — no CDN, no webfont, no image file. A case that needs the network scores
   differently on a machine that does not have it.
2. Write `notes.md` first, in prose: what is this case meant to stress, and what
   is the specific wrong answer you expect it to catch? If you cannot name that,
   the case is not earning its place.
3. Write `expectations.yaml`. Start from the nearest existing case. Derive every
   range from the mockup, and write the derivation into a comment next to it —
   `# 16 <input> in the mockup` is what makes the number reviewable a year later.
4. Run it against a real conversion before committing it. A case nobody has ever
   seen pass is a case with unknown thresholds.
5. Add a `reference.output` **only** if a file already in this repo is genuinely a
   conversion of that mockup. Hand-writing one to make CI greener means scoring an
   answer against itself.

`scripts/validate.py` checks the shape of every case on each run: the three files
exist, the mockup pulls nothing external, `expectations.yaml` parses and asserts
something, every `known_deviations` entry carries a reason, and every reference
output exists and still scores as the case says it will.

## The self-check CI runs

```bash
python scripts/run_eval.py          # no arguments
```

With no arguments, the scorer runs every case that names a `reference.output` and
scores it against that file. Three of the five do, and the reference in each case
is one of the bundled example screens.

**This exercises the scorer. It says nothing about the skill's output quality.**
The examples were written by hand, long before the harness, and were never
generated by a model. What the self-check proves is that the assertions run, that
they read the files correctly, and that a change to `pa_lint.py` or to the catalog
has not quietly changed what the harness measures.

`app-shell` carries three declared deviations, all the same five `FontWeight`
properties on `Classic/Button`: `controls.yaml` confirms `FontWeight` on `Label`
only and marks it explicitly unverified on `Button`, while the example uses it.
That contradiction is real, open, and settled only by a Studio paste test —
recorded in the [0.2.0 known issues](../CHANGELOG.md) and waived here with the
reason written out in `tests/evals/app-shell/expectations.yaml`. If a Studio
result settles it, the row turns `XPASS` and the waiver should be deleted.
