# Harvesting the control catalog from real Studio exports

Phase 1 grew [`controls.yaml`](../skills/power-app-yaml/references/controls.yaml) by hand:
one paste test, one row. That works, but it is slow and it only ever covers controls
somebody remembered to test.

This page describes the faster route. Power Apps Studio can write your app out as
`.pa.yaml` source. Those files are **Studio's own output**, which makes them the
strongest evidence available that a control type and a property name are real — nobody
guessed them, the product emitted them. `scripts/harvest_controls.py` reads them and
turns them into catalog entries.

- [The absence caveat](#the-absence-caveat-read-this-first)
- [Route A — Power Platform CLI](#route-a--power-platform-cli-pac)
- [Route B — unzip the .msapp by hand](#route-b--unzip-the-msapp-by-hand)
- [Route C — a plain folder of .pa.yaml files](#route-c--a-plain-folder-of-payaml-files)
- [Running the harvester](#running-the-harvester)
- [Reviewing a merge before you commit](#reviewing-a-merge-before-you-commit)
- [Reporting the result upstream](#reporting-the-result-upstream)
- [What harvesting cannot tell you](#what-harvesting-cannot-tell-you)
- [Open question: does Microsoft publish a list of control ids?](#open-question-does-microsoft-publish-a-list-of-control-ids)

---

## The absence caveat (read this first)

> **Studio's export only writes properties whose value differs from the default.**
> A property missing from an export is **not** evidence that the control lacks it.

This is not our inference. Microsoft's own documentation for `.pa.yaml` states it
plainly: *"Only properties that differ from the default values are serialized."*
([Source code files for canvas apps (pa.yaml)](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/power-apps-yaml).)

Everything downstream follows from that one sentence:

| | |
|---|---|
| A property **present** in an export | Positive evidence. Studio wrote it, so the name is real for that control at that version. |
| A property **absent** from an export | **Nothing.** It may be unsupported, or it may simply have been left at its default. |
| A control type **absent** from an export | Nothing. The app just didn't use it. |

So the harvester only ever makes positive claims:

- it **never** writes to `properties_unverified`;
- it **never** emits a "does not support" list — there is no such field to write to;
- it **never** removes or demotes an existing catalog entry;
- its `--report` section 2 is titled *"never exercised by this export"*, meaning
  **untested**, never **unsupported**;
- `accepts_children: false` in generated output means *no `Children:` seen*, and the
  generated line says so in a comment.

The same caveat is pinned at the top of
[`controls.yaml`](../skills/power-app-yaml/references/controls.yaml) and printed by
`harvest_controls.py --report`.

---

## Route A — Power Platform CLI (`pac`)

> **Status: documented, not verified in this repo.** Nobody here has run
> `pac canvas download` against a real tenant yet. The flags below come from
> [Microsoft's `pac canvas` reference](https://learn.microsoft.com/en-us/power-platform/developer/cli/reference/canvas);
> if a step behaves differently for you, that is a finding worth reporting — see
> [Reporting the result upstream](#reporting-the-result-upstream). Route B needs no CLI
> at all and is a complete substitute.

### A1. Install the CLI

Pick whichever you already have:

```bash
# .NET tool (cross-platform)
dotnet tool install --global Microsoft.PowerApps.CLI.Tool

# Windows, winget
winget install Microsoft.PowerPlatformCLI
```

Check it responds:

```bash
pac --version
```

There is also a **Power Platform Tools** extension for VS Code that bundles `pac`.

### A2. Sign in to the environment

```bash
pac auth create --environment <environment-id-or-url>
pac auth list
```

`--environment` accepts a GUID or an absolute `https://` org URL. If you omit it, `pac`
uses the environment of your active Dataverse auth profile.

### A3. Find the app

```bash
pac canvas list
```

Optional: `pac canvas list --environment <id-or-url>`.

Note the app's **name** or **App ID** from the output — the next step needs one of them.

### A4. Download and extract in one step

```bash
pac canvas download --name "<app name or App ID>" --extract-to-directory ./harvest/myapp
```

`-n` is short for `--name` (required; exact name, partial name, or App ID) and `-d` is
short for `--extract-to-directory`. Other flags on this command:

| Flag | Short | Meaning |
|---|---|---|
| `--name` | `-n` | Canvas app exact name, partial name, or App ID. **Required.** |
| `--extract-to-directory` | `-d` | Directory to extract the app into. |
| `--file-name` | `-f` | Where to write the `.msapp` itself. Defaults to the current directory. |
| `--environment` | `-env` | Target Dataverse environment (GUID or absolute URL). |
| `--overwrite` | `-o` | Allow overwriting existing files. |

Leave `-d` off and you get the raw `.msapp`, which the harvester also reads directly —
see [Route B](#route-b--unzip-the-msapp-by-hand).

### A5. Find `src/`

Inside the extracted folder, the source lives under **`src/`** (`\Src\` on Windows):

```
harvest/myapp/
  src/
    App.pa.yaml                 <- app-level; no control instances, harvester skips it
    <ScreenName>.pa.yaml        <- one per screen; this is where the controls are
    Component/
      <ComponentName>.pa.yaml   <- one per component
  ...other folders (.json, .xml) -- ignore them
```

**Only files under `src/` are source.** Microsoft is explicit that the other JSON in an
`.msapp` is not stable between save/load cycles, and that these `.pa.yaml` files are
read-only: editing them and repacking is not a supported round trip. For harvesting we
only ever read them, so that limitation does not bite.

If there is no `src/` folder, your `pac` predates the v3.0 source format — update it, or
use Route B and check the archive's contents yourself.

---

## Route B — unzip the `.msapp` by hand

No CLI needed. An `.msapp` is an ordinary ZIP archive.

### B1. Get the `.msapp`

Either of these, from Power Apps Studio with the app open:

- **File → Save as → This computer**, or
- the **Save** dropdown → **Download a copy**.

(`pac canvas download` without `-d` produces the same file.)

### B2. Unzip it

```bash
# macOS / Linux
unzip MyApp.msapp -d ./harvest/myapp
```

```powershell
# Windows PowerShell
Expand-Archive -Path .\MyApp.msapp -DestinationPath .\harvest\myapp
```

On Windows Explorer you may have to rename `MyApp.msapp` to `MyApp.zip` before the
right-click **Extract All** appears.

### B3. Look under `src/`

Same layout as [A5](#a5-find-src).

### B4. Or skip unzipping entirely

The harvester opens `.msapp` archives itself and reads `src/**/*.pa.yaml` straight out
of them:

```bash
python scripts/harvest_controls.py ./MyApp.msapp --report
```

---

## Route C — a plain folder of `.pa.yaml` files

Any folder works. The harvester walks it recursively and picks up `.pa.yaml`, `.yaml`,
`.yml` and `.msapp`. Files that do not contain a `Screens:` or `ComponentDefinitions:`
key are skipped and listed in the report, so an `App.pa.yaml` or a stray config file in
the same folder is harmless.

This is the mode that keeps working if Route A fails in your tenant: however you got
the files, point the harvester at them.

---

## Running the harvester

```
python scripts/harvest_controls.py SRC [SRC...] [--out FILE] [--merge] [--report]
                                   [--catalog PATH] [--dry-run] [--date YYYY-MM-DD]
```

`SRC` is a `.pa.yaml` file, a folder of them, or an `.msapp`. You can pass several.

| Mode | What it does |
|---|---|
| *(no flag)* | Prints a `controls.yaml` fragment on stdout. |
| `--out FILE` | Writes that fragment to `FILE`. Combines with the other flags. |
| `--report` | Prints a coverage diff: export vs catalog, in both directions. |
| `--merge` | Folds the fragment into `controls.yaml` **in place**. |
| `--dry-run` | With `--merge`: report what would change, write nothing. |
| `--catalog PATH` | Merge into / compare against a different catalog file. |
| `--date` | Override the harvest date stamp (useful in tests). |

Exit codes: `0` clean · `1` nothing readable / IO failure · `2` the merge found
conflicts.

### Step 1 — look before you leap

```bash
python scripts/harvest_controls.py ./harvest/myapp/src --report
```

The report has four parts:

1. **In the export, missing from the catalog** — new control types and new property
   names. This is the value you are harvesting.
   - **1b. Observed, but held back** — properties the catalog explicitly flags
     `properties_unverified`. The export exercising one is positive evidence, but a
     human deliberately wrote that flag, so `--merge` will not promote it. Settle it
     with a Studio paste test.
2. **In the catalog, never exercised by this export** — the absence case. It means
   *this app never set that property*, and nothing more. Never delete a catalog row
   because of this section.
3. **Disagreements** — same control at a different version, a `Variant` that does not
   match, `Children` on a control the catalog says has none, a control id with no
   `@version`. Reported, never auto-resolved.
4. **Third-party instances** — `CanvasComponent` / `CodeComponent`, which are not
   control-library types and are never catalogued.

### Step 2 — see the fragment

```bash
python scripts/harvest_controls.py ./harvest/myapp/src --out /tmp/fragment.yaml
```

The fragment is a `controls.yaml`-shaped block with `evidence: studio-export` and
`source: "<file> (harvested <date>)"` on every entry. Read it. It is a proposal, not a
result.

### Step 3 — merge

```bash
python scripts/harvest_controls.py ./harvest/myapp/src --merge
```

The merge is deliberately conservative:

- **adds** control types the catalog has never seen;
- **unions** new property names into the existing `properties_confirmed`, keeping the
  hand-written order and appending the new names, with a `# harvested <date>: +Name`
  comment above the list recording where they came from;
- **never** overwrites a hand-written `notes`, `source`, or `evidence` field;
- **never** downgrades a `studio-tested` entry;
- **never** touches `properties_unverified`;
- **holds back** anything in a conflict — a different `@version` of a control the
  catalog already has, or a control id with no version at all — and prints it;
- edits the file as **text**, so every comment in `controls.yaml` survives (a
  load-and-dump through a YAML library would silently delete all of them);
- writes nothing at all when there is nothing to change, so a re-run over the same
  export leaves the file **byte-identical**.

### Worked example

The three bundled examples under `skills/power-app-yaml/assets/examples/` are real
paste-tested screens, so they make a good dry run:

```bash
python scripts/harvest_controls.py skills/power-app-yaml/assets/examples/ --report
```

That reproduces the eight control types the catalog already carries
(`Label@2.5.1`, `Classic/Button@2.2.0`, `GroupContainer@1.5.0`, `Rectangle@2.3.0`,
`Image@2.2.3`, `Classic/Icon@2.5.0`, `Classic/TextInput@2.3.2`,
`Classic/DropDown@2.3.1`) with zero conflicts, and `--merge` over it is a no-op. The
ninth catalogued control, `Classic/Radio@2.3.0`, shows up in report section 2: the
examples never use it. That is the absence caveat in miniature — it means untested by
these files, not broken.

---

## Reviewing a merge before you commit

**Always look at the diff.** `--merge` edits a file that the linter treats as ground
truth.

In a git checkout:

```bash
python scripts/harvest_controls.py ./harvest/myapp/src --merge
git diff -- skills/power-app-yaml/references/controls.yaml
```

Without git, or to see the plan first:

```bash
# what would change, nothing written
python scripts/harvest_controls.py ./harvest/myapp/src --merge --dry-run

# or diff by hand
cp skills/power-app-yaml/references/controls.yaml /tmp/controls.before.yaml
python scripts/harvest_controls.py ./harvest/myapp/src --merge
diff -u /tmp/controls.before.yaml skills/power-app-yaml/references/controls.yaml
```

Checklist for the diff:

- [ ] Every added property name looks like a real Power Apps property, not a typo or a
      custom-component property that leaked in.
- [ ] No hand-written `notes:` line changed. (The merge will not touch one; check
      anyway.)
- [ ] Nothing was removed, and no `evidence:` was weakened.
- [ ] Every new control entry has a `source:` naming the file it came from.
- [ ] If a new control's base name is still listed in `unattempted_controls:`, remove
      it there — the merge prints a `! todo` line reminding you, and
      `scripts/validate.py` fails if the two lists overlap.
- [ ] `confirmed-controls.md` updated to match. `scripts/validate.py` fails if a
      control is in one file and not the other; the two must move in the same commit.

Then run the repo checks:

```bash
python scripts/validate.py
python -m unittest discover tests
```

An entry merged from an export carries `evidence: studio-export`, which is deliberately
weaker than `studio-tested`. Promoting it to `studio-tested` requires an actual isolated
paste test — see the next section.

---

## Reporting the result upstream

A harvest is worth more to everyone else than to you. Two ways to share it:

**1. Open a Control test report issue.** Use the
[Control test report](https://github.com/YKUNAKORN/power-app-yaml/issues/new?template=control-report.yml)
template (`.github/ISSUE_TEMPLATE/control-report.yml`). Map the harvest onto its fields:

| Template field | From your harvest |
|---|---|
| Control type and version | The `type:` from the fragment, verbatim, e.g. `Classic/DropDown@2.3.1`. |
| Property tested | The property name, or `(the control itself)` for a whole new control type. |
| Studio outcome | **Only fill this in from a real paste test.** A harvest alone does not produce an outcome — see below. |
| Power Apps Studio version | Studio → `?` → **About**. Fill this in; the catalog currently records `studio_version_tested: unknown` and that is a gap worth closing. |
| Minimal YAML you pasted | A full `Screens:` wrapper with just this control. `scripts/pa_lint.py` generates one for you in its warning output. |
| Notes / exact error text | Say it came from a harvest, name the route (`pac canvas download` or manual unzip), and paste the exact Studio message. |

The template asks for a **Studio outcome**, and a harvested export cannot supply one on
its own: the export proves Studio *wrote* the property, not that Studio *accepts it on
paste* at your version. To fill that field honestly, take the isolated snippet, paste it
into a blank screen, and report what actually happened. That one extra minute is what
turns `studio-export` into `studio-tested`.

**2. Open a PR.** Run `--merge`, review the diff, update
`confirmed-controls.md` to match, add a CHANGELOG entry, and open a pull request. See
[CONTRIBUTING.md](../CONTRIBUTING.md). Do **not** hand-promote anything to
`studio-tested` in that PR without a Studio version to cite.

Please don't attach a real app's `.msapp` or `.pa.yaml` to a public issue — they carry
formulas, data source names, and often customer-specific text. The fragment the
harvester emits contains only control type ids and property names, which is all the
catalog needs.

---

## What harvesting cannot tell you

Worth being blunt about the limits, so nobody over-reads a green run:

- **Not what a control does not support.** The absence caveat, again. This is the big
  one.
- **Not whether a paste will succeed.** An export is what Studio *wrote*; a paste is
  what Studio *reads back*, at possibly a different version. Only a paste test settles
  `PA1001` / `PA2108`.
- **Not which `@version` you should write.** The harvest records the version *that app*
  was saved at. A different Studio build will emit different numbers and warn
  (`PA2105` / `PA2106`) rather than fail.
- **Not property value types.** The harvester records that `Size` was set, not that it
  takes a number.
- **Not layout correctness.** A screen can export cleanly and still render wrong.

---

## Open question: does Microsoft publish a list of control ids?

**Yes — and it is now mirrored here as
[`control-ids-candidate.yaml`](../skills/power-app-yaml/references/control-ids-candidate.yaml),
with every entry marked `evidence: unverified`.** Recorded here so nobody spends another
afternoon looking.

**What was checked.** `microsoft/PowerApps-Tooling`, cloned at commit
`aed72a37c3b10b08f81c9d2257d5c38da33dccbe` (2026-08-24) and searched in full.

**What was found.** A 62-entry enum of first-party control type ids at:

```
src/schemas/pa-yaml/v3.0/ControlLibraryVDev/ControlTypeId-1P-controls-enum.schema.yaml
```

referenced from the source schema as `ControlTypeId-1P-controls-enum`. It lists ids such
as `Button`, `ComboBox`, `DatePicker`, `Gallery`, `GroupContainer`, `Label`, `Rectangle`,
`Toggle`, the `FluentV8/*` family, the `FluentV9/*` family, and `Classic/Icon`.

**Why every mirrored entry is `unverified` anyway.** Four independent reasons:

1. **The published schema deliberately leaves the enum open.** The distributed
   `schemas/pa-yaml/v3.0/pa.schema.yaml` — the file this repo bundles as
   `references/schema-v3.pa.yaml`, byte-for-byte — defines
   `ControlTypeId-1P-controls-enum:` as literally `true`, which matches anything.
   Microsoft ships the closed enum only inside its source tree. Whatever the reason,
   the artefact intended for third-party tooling does not carry the list, and building
   validation on the internal one is building on something Microsoft chose not to
   publish.
2. **`ControlLibraryVDev`** — the folder name says it: a *development* snapshot of the
   control library. It can move.
3. **It is a tooling list, not a paste test.** No `@version`, no property names, no
   statement about which Studio build accepts the id.
4. **It disagrees with this repo's own Studio tests on the `Classic/` prefix.** The enum
   lists bare `Button`, `TextInput`, `DropDown` and `Radio`, and only `Classic/Icon`
   carries a prefix — while `controls.yaml` records `Classic/Button@2.2.0`,
   `Classic/TextInput@2.3.2`, `Classic/DropDown@2.3.1` and `Classic/Radio@2.3.0` from
   real paste tests. Bare `Button` and `Classic/Button` are not interchangeable. Until
   somebody paste-tests both, that contradiction is unresolved, and it is on its own
   enough reason to trust nothing in the list without a test.

**What it is used for.** Exactly one thing: wording. `scripts/pa_lint.py` reads the
mirror so that a control it has never seen gets

> Control type `'Toggle@1.0.0'` is known to Microsoft's tooling but not yet paste-tested
> here — paste-test it in isolation before trusting it.

(check id `L2.candidate-control-type`) instead of the blunter "unverified control type"
(`L2.unverified-control-type`). Same severity, same `# UNVERIFIED` tagging requirement,
same paste-test snippet. Nothing in the candidate list is ever promoted into
`controls.yaml` automatically, and `scripts/validate.py` fails if any entry there is
marked as anything other than `unverified`.

**Two smaller lists in the same schema**, worth knowing about but not mirrored, because
the bundled published schema already enforces them at layer L1:

- `ControlTypeId-disallowed-types`: `AppInfo`, `HostControl`, `Screen`, `AppTest`,
  `TestCase`, `TestSuite`.
- `ControlTypeId-not-yet-supported`: `CommandComponent`, `DataComponent`,
  `FunctionComponent`.

**If you re-check this later**, compare against the commit and `sha256` recorded in the
header of `control-ids-candidate.yaml`, and regenerate only if the upstream enum has
actually changed.
