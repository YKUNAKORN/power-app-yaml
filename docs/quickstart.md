# Quickstart

Get from a mockup to a pasted Power Apps screen in about five minutes.

## 1. Install the skill

You have two options. They deliver the same skill — pick whichever fits your setup.

### Option A — as a Claude Code plugin (recommended)

```bash
/plugin marketplace add YKUNAKORN/power-app-yaml
/plugin install power-app-yaml@power-app-yaml
```

Claude Code reads the plugin from `.claude-plugin/plugin.json` and loads the skill
from `skills/power-app-yaml/`. Update later with:

```bash
/plugin marketplace update power-app-yaml
```

### Option B — as a plain skill folder

Copy the skill directory into wherever your Claude setup loads skills from:

```bash
git clone https://github.com/YKUNAKORN/power-app-yaml.git
cp -r power-app-yaml/skills/power-app-yaml  <your-skills-directory>/
```

The folder that must land in your skills directory is
**`skills/power-app-yaml/`** (the one containing `SKILL.md`), not the repository
root.

### Optional, but worth two minutes: the linter's dependencies

The scripts under `scripts/` are plain Python and need two packages:

```bash
pip install pyyaml jsonschema
```

`pyyaml` is required. `jsonschema` is optional in the sense that the linter still
runs without it — but the layer it powers is the one that catches the error which
blocks a whole paste (`PA1001`). Without it the linter says **UNPROVEN** instead
of **SAFE TO PASTE**, and it is right to: it cannot claim a file is clean when the
check that would have caught the worst failure did not run.

## 2. Give Claude a mockup

Anything visual works:

- An HTML/CSS export from Google Stitch, v0, or Figma
- A screenshot of a UI
- A hand-drawn wireframe photo

Ask, in plain words:

> Convert this to pa.yaml — make it a Power Apps screen.

If the screen is going into an **app that already exists**, say so and hand over an
export of it (`pac canvas download -d <dir>`, or just unzip the `.msapp`). Claude
runs `scripts/app_inventory.py` over it first, so the new screen matches the app's
naming convention, reuses its theme variables, and does not collide with a name
that is already taken. See
[`extend-existing-app.md`](../skills/power-app-yaml/references/extend-existing-app.md).

## 3. Claude produces the `.pa.yaml`

It reads the confirmed-controls catalog, picks the patterns the mockup needs,
derives the absolute coordinates, and writes the full file. Anything it is not
sure about is tagged `# UNVERIFIED` and comes with a small isolated paste-test
snippet.

## 4. Lint it before it goes near Studio

This is the step that saves the round trip, and Claude runs it as part of its own
workflow. Run it yourself on anything you did not watch it lint:

```bash
python scripts/pa_lint.py myscreen.pa.yaml
```

Four layers run in order, and each maps to something Studio would have told you
later:

| Layer | Checks | Studio equivalent |
|---|---|---|
| **L0** | the file is YAML at all | a paste that does nothing |
| **L1** | the bundled Microsoft v3.0 schema | `PA1001` — blocks the whole paste |
| **L2** | this repo's control catalog | `PA2108` — unknown control or property |
| **L3** | SKILL.md's own conventions | nothing; Studio accepts these silently |

The last line is the verdict. **`VERDICT: SAFE TO PASTE` is the only one that
means go.** The others, and what to do about each, are in
[troubleshooting](troubleshooting.md#the-linters-verdict-lines).

Useful flags: `--quiet` prints only the verdict, `--strict` exits non-zero on
warnings, `--json` is for scripting.

## 5. Paste into Power Apps Studio

1. Open your Canvas app in **Power Apps Studio**.
2. Add a **blank screen**.
3. With the screen selected, use **Paste code** (the tree-view context menu, or
   `Ctrl+V` after copying the whole file).
4. Paste the **entire** file — Studio needs the full `Screens:` wrapper, not a
   fragment.

If the file came with isolated paste-test snippets, paste each of those onto a
scratch screen **first**. That is what they are for: a one-control file fails in a
way you can attribute, and a 200-control file does not.

## 6. Feed results back

If Studio shows an error or warning, paste the exact text back to Claude. It
knows which codes block a paste (`PA1001`, `PA2108`) and which are harmless
version warnings (`PA2105`, `PA2106`) — see [troubleshooting](troubleshooting.md).

If a Studio test confirms a control the catalog did not have, record it in your
own `controls.yaml` and `confirmed-controls.md`, and please
[report it](https://github.com/YKUNAKORN/power-app-yaml/issues/new?template=control-report.yml)
so the next person benefits. Results for the twelve bundled test snippets go in
[`test-plan.md`](test-plan.md).

## Next steps

- **Add another screen:** ask Claude to "add a screen to this app" and give it the
  new mockup — it reuses the existing screen names for `Navigate()`.
- **Grow the catalog from a real export** instead of one paste test at a time:
  `python scripts/harvest_controls.py ./myapp/src --report`, then `--merge`. Full
  walkthrough in [`harvesting.md`](harvesting.md).
- **Check whether a change helped.** If you edit `SKILL.md` or the catalog, the
  eval cases under `tests/evals/` and `scripts/run_eval.py` are how you tell better
  from worse — see [`evals.md`](evals.md).
