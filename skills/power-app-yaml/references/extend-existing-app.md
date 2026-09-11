# Extending an app that already exists

The main workflow in [`SKILL.md`](../SKILL.md) assumes a blank canvas. This is the
branch for when there is already an app: a new screen for it, or a change to a screen
it already has.

Everything in the main workflow still applies — catalogued controls only,
[`layout-mapping.md`](layout-mapping.md) for the geometry, `pa_lint.py` before hand-off.
This file adds the six steps that only matter when there is a host app, and the failure
each one prevents. All six failures are silent: the paste succeeds and the app is
subtly wrong, which is worse than `PA1001`.

---

## 0. Get the export

You need the app's source, not a screenshot of it. Any of:

- **Git integration** — the `Src/` folder in the repo the app is synced to.
- **`pac canvas download -d <file>.msapp`**, then point the tool at the `.msapp`
  directly; it reads `src/**/*.pa.yaml` from inside the archive without unzipping.
- **Manual**: rename the `.msapp` to `.zip`, extract, use the `Src\` folder.

[`docs/harvesting.md`](../../../docs/harvesting.md) has the full write-up. If no export
is available at all, say so and work from what the user can tell you — but then say
plainly which of the checks below you could not run, rather than guessing your way
through them.

---

## 1. Run the inventory first — never paste the export into the conversation

```bash
python scripts/app_inventory.py <folder-or-.msapp>
```

About a page: screens in editor order, controls per screen with their nesting depth,
the control types **with the versions this app uses**, the variables `App.OnStart`
sets, the `DataSources:` entries, the components, and the list of names already taken.

The export itself is tens of thousands of tokens of property values you will not read
and cannot use. Two extra flags when the page is not enough:

```bash
python scripts/app_inventory.py <src> --names   # the full collision list
python scripts/app_inventory.py <src> --json    # everything, machine-readable
```

**Prevents:** burning the context you need for the actual conversion on a file you are
going to skim. The tool degrades to coarser detail rather than overflowing its budget,
and its last line says which level it used.

---

## 2. Adopt the app's naming convention — do not import yours

Read the convention off the inventory's name list before writing a single control name.
Apps are consistent in ways that are obvious once seen and invisible once ignored:

| What the inventory shows | What to write |
|---|---|
| `lblTitle`, `btnSave`, `grpCard` | Hungarian prefixes — match the exact prefix set, including oddities like `rec` vs `rect` |
| `Label1`, `Rectangle7` | Studio auto-names — the app has no convention; introduce one and say you did |
| `scrHome`, `scrRequestList` | screens carry a prefix too — a new `Dashboard` would stand out |
| `Card3_AddressLine`, `Card1_Person` | a generated/structured scheme — do not invent a new shape inside it |

The inventory prints a name-prefix histogram (`lbl*x62 btn*x35 …`) when the app is too
big to list every name, which is usually enough to read the convention off directly.

**Prevents:** a screen that is visibly foreign inside its own app, and a maintainer who
has to guess which screen you wrote.

---

## 3. Check every new name against the collision list

Power Apps control names are unique across the whole app, not per screen. On paste,
**Studio silently appends `_1` to anything that collides** — no error, no warning, and
nothing in the pasted file says it happened.

```bash
python scripts/app_inventory.py <src> --names | tr ' ' '\n' | sort > /tmp/taken.txt
# then check each name you intend to use against that list
```

Two things break when a rename happens behind your back:

- Any formula referring to the control by name — `galRequests.Selected`,
  `frmRequest.Error`, `Reset(txtTitle)` — now points at the *old* control, or at
  nothing.
- The names you hand back in your explanation no longer match the names in the app,
  so every follow-up instruction is wrong.

`pa_lint.py` catches duplicates *within your file* (`L3.duplicate-control-name`). It
cannot see the host app, so collisions against the host are entirely on this step.

**Prevents:** silent `_1` renames and the broken cross-control references that follow.

---

## 4. `Navigate()` only to screens that exist

The inventory's screen list is the complete set of legal `Navigate()` targets. Anything
else is either a screen the user has to create first, or a typo.

```text
Navigate(scrRequestList)       # in the inventory -> fine
Navigate(scrDashboard)         # not in the inventory -> do not write this
```

If the mockup has a link with no destination in the app yet, keep the placeholder and
**comment on the same line** that it is not wired up:

```yaml
OnSelect: =Navigate(ScrPlaceholder)  # not wired up - no such screen in this app yet
```

`pa_lint.py` enforces exactly this at `L3.navigate-target-missing`, and the trailing
comment is what tells it the placeholder is deliberate. Screen names are also
case-sensitive and also collide: a new screen called `Home` in an app that already has
`Home` becomes `Home_1`, and every `Navigate(Home)` in your file then points at the old
one.

**Prevents:** dead navigation that looks wired up, and invented screen names.

---

## 5. Reuse the theme variables the app already sets

The inventory prints what `App.OnStart` establishes, with literal values where the value
is a literal:

```text
ONSTART: varThemePrimary=ColorValue("#005AB6") varThemeText=RGBA(24,28,35,1)
  varAppTitle="Field Service Requests" varUserEmail=~expr
```

When the app has a theme variable for a colour, **use the variable, not the hex**:

```yaml
Fill: =varThemePrimary                 # yes
Fill: =ColorValue("#005AB6")           # no - now there are two places to change it
```

`~expr` means the value is a formula, not a literal — the tool reports the name without
pretending to know what it evaluates to. `varUserEmail=~expr` in the example above is
almost certainly `User().Email`; if you need its actual value, read that one line out of
`App.pa.yaml` rather than assuming.

Two caveats:

- A variable set in `App.OnStart` is not in scope at design time in your pasted file —
  it resolves at run time. The paste still succeeds.
- If the app sets **no** theme variables, do not introduce `Set(...)` calls as a side
  effect of adding a screen. Use literal colours, and suggest the refactor separately.

**Prevents:** a second, divergent copy of the palette, and a theme change that updates
every screen except the new one.

---

## 6. Paste onto a blank screen, then lint, then hand over

Unchanged from the main workflow, and the last two are not optional:

```bash
python scripts/pa_lint.py <your-file>.pa.yaml
```

Zero L0/L1 errors before anything is handed over. Every L2/L3 warning is reported
verbatim as the UNVERIFIED list, with the isolated snippet the linter generates.

One addition for this branch: **a new screen goes onto a new blank screen**, never
pasted over an existing one. A paste replaces nothing — it adds — so pasting onto a
populated screen leaves both sets of controls stacked on top of each other with the
collisions renamed. If the job is to change an existing screen, say which controls
change and hand over only those, rather than a full-screen file that will duplicate
everything it touches.

---

## Checklist

- [ ] Inventory run; export never pasted into the conversation whole
- [ ] Naming convention read off the inventory and matched
- [ ] Every new control and screen name checked against `--names`
- [ ] Control **versions** match what the inventory says the app already uses
- [ ] Every `Navigate()` target is in the inventory's screen list, or is a commented
      placeholder
- [ ] Theme variables from `App.OnStart` reused instead of re-hardcoded hex
- [ ] `pa_lint.py` run; zero L0/L1 errors; every warning reported with its snippet
- [ ] Hand-off says "paste onto a **new blank** screen", and names any control whose
      name might still collide
