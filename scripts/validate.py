#!/usr/bin/env python3
"""Repository sanity checks for the power-app-yaml skill.

Run locally before opening a PR:

    python scripts/validate.py

Exits non-zero if anything fails. Requires PyYAML (`pip install pyyaml`).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "power-app-yaml"

# --- Budgets -----------------------------------------------------------------
# SKILL.md is loaded into context on every single invocation, so its size is a
# running cost, not a one-off. Everything that is not procedure belongs in
# README.md or a references/ file that is read on demand.
SKILL_MD_MAX_BYTES = 8192
# The frontmatter description is what makes the skill fire. It has to keep every
# distinct trigger phrase, which is why the ceiling is a ceiling and not a target:
# trim justification prose, never a trigger.
DESCRIPTION_MAX_CHARS = 650
DESCRIPTION_MIN_CHARS = 40
# Pattern snippets exist to be read instead of a 1,700-line example, so they stay
# small. tile-grid-cell is an acknowledged exception: it is a six-control
# composite (card, title, subtitle, checkbox, check icon, click overlay) and
# cutting it to 60 lines would mean dropping the selection mechanic that is the
# whole reason to extract it.
PATTERN_MAX_LINES = 60
PATTERN_MAX_LINES_EXCEPTIONS = {"tile-grid-cell.pa.yaml": 90}
PATTERN_MIN_LINES = 20
# Every pattern file opens with these header fields, so a reader knows what it is
# and -- crucially -- where the evidence for it came from.
PATTERN_HEADER_FIELDS = ("PATTERN", "What", "Controls", "Source", "Evidence")
# A paste-test snippet is the opposite of a pattern: a pattern is extracted evidence,
# a snippet is an isolated guess for the user to disprove in Studio. The header has to
# say which control is under test, where its property names came from, how to run it
# and where the answer goes.
SNIPPET_HEADER_FIELDS = ("SNIPPET", "What", "Control", "Evidence", "Test", "Record")
SNIPPET_MIN = 12
# The inventory tool exists to save context. If its one-page summary of a ten-screen
# app stops fitting on a page, it has stopped doing its job.
INVENTORY_MAX_BYTES = 2048
# Eval cases. Five archetypes, each covering a layout shape the others do not --
# plus the hard one, which covers the honesty path rather than a layout at all.
EVAL_CASES_MIN = 5
REQUIRED_EVAL_CASES = {
    "app-shell", "multi-section-form", "card-grid",
    "shell-with-form", "impossible-effects",
}
# A case asserting one or two of these is not measuring enough to tell a good
# conversion from a bad one.
EVAL_ASSERTION_BLOCKS = ("structure", "lint", "controls", "geometry", "navigation",
                         "catalog", "limitations")

errors: list[str] = []
checks = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global checks
    checks += 1
    if ok:
        print(f"  ok   {label}")
    else:
        msg = f"{label}" + (f" -- {detail}" if detail else "")
        print(f"  FAIL {msg}")
        errors.append(msg)


def load_yaml():
    try:
        import yaml  # type: ignore
        return yaml
    except ImportError:
        print("ERROR: PyYAML is not installed. Run: pip install pyyaml")
        sys.exit(2)


yaml = load_yaml()

print("Layout")
check(SKILL_DIR.is_dir(), "skills/power-app-yaml/ exists")
skill_md = SKILL_DIR / "SKILL.md"
check(skill_md.is_file(), "SKILL.md present")
schema = SKILL_DIR / "references" / "schema-v3.pa.yaml"
check(schema.is_file(), "bundled Microsoft schema present",
      "references/schema-v3.pa.yaml is referenced by NOTICE and must not be removed")
check((SKILL_DIR / "references" / "confirmed-controls.md").is_file(),
      "confirmed-controls.md present")
check((SKILL_DIR / "references" / "controls.yaml").is_file(),
      "controls.yaml present", "the machine-readable catalog scripts/pa_lint.py reads")
check((SKILL_DIR / "references" / "layout-mapping.md").is_file(),
      "layout-mapping.md present",
      "the HTML/CSS -> X/Y/Width/Height reference SKILL.md step 3 sends the model to")
check((SKILL_DIR / "assets" / "patterns").is_dir(),
      "assets/patterns/ present", "the extracted pattern snippets SKILL.md step 2 uses")
check((SKILL_DIR / "assets" / "examples" / "INDEX.md").is_file(),
      "assets/examples/INDEX.md present",
      "the line-range index that lets a slice be read instead of a whole example")
check((ROOT / "scripts" / "pa_lint.py").is_file(), "scripts/pa_lint.py present")
check((SKILL_DIR / "references" / "extend-existing-app.md").is_file(),
      "extend-existing-app.md present",
      "the procedure SKILL.md branches to when the app already exists")
check((SKILL_DIR / "references" / "data-binding.md").is_file(),
      "data-binding.md present", "the UNVERIFIED data-binding groundwork")
check((SKILL_DIR / "assets" / "test-snippets").is_dir(),
      "assets/test-snippets/ present", "the one-control paste-test kit")
check((ROOT / "docs" / "test-plan.md").is_file(), "docs/test-plan.md present",
      "the results table the paste-test kit reports into")
check((ROOT / "scripts" / "app_inventory.py").is_file(),
      "scripts/app_inventory.py present",
      "the one-page summariser for an app that already exists")
check((ROOT / "tests" / "apps" / "ten-screen-app").is_dir(),
      "tests/apps/ten-screen-app/ present",
      "the synthetic fixture the inventory byte budget is measured against")
check((ROOT / "scripts" / "harvest_controls.py").is_file(),
      "scripts/harvest_controls.py present",
      "the Studio-export harvester documented in docs/harvesting.md")
check((ROOT / "docs" / "harvesting.md").is_file(), "docs/harvesting.md present")
check((SKILL_DIR / "references" / "control-ids-candidate.yaml").is_file(),
      "control-ids-candidate.yaml present",
      "the mirrored Microsoft control-id enum pa_lint.py reads for wording")
check(not (ROOT / "skill").exists(), "no stray top-level skill/ directory")
check(not (ROOT / "confirmed-controls.md").exists(),
      "no duplicate confirmed-controls.md at repo root")

print("SKILL.md frontmatter")
if skill_md.is_file():
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    check(bool(m), "has a YAML frontmatter block")
    if m:
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError as e:  # pragma: no cover
            fm = {}
            check(False, "frontmatter parses as YAML", str(e))
        check(isinstance(fm.get("name"), str) and fm.get("name").strip() != "",
              "frontmatter has non-empty 'name'")
        check(fm.get("name") == "power-app-yaml",
              "frontmatter name is 'power-app-yaml'", f"got {fm.get('name')!r}")
        desc = fm.get("description")
        check(isinstance(desc, str) and len(desc.strip()) >= DESCRIPTION_MIN_CHARS,
              "frontmatter has a substantive 'description'")
        if isinstance(desc, str):
            n = len(desc.strip())
            check(n <= DESCRIPTION_MAX_CHARS,
                  f"frontmatter description is within {DESCRIPTION_MAX_CHARS} chars",
                  f"got {n}. Cut justification sentences, never a trigger phrase -- "
                  "the triggers are what make the skill fire.")

print("SKILL.md size budget")
if skill_md.is_file():
    size = len(skill_md.read_bytes())
    check(size <= SKILL_MD_MAX_BYTES,
          f"SKILL.md is within {SKILL_MD_MAX_BYTES} bytes",
          f"got {size} ({size - SKILL_MD_MAX_BYTES} over). SKILL.md is procedure only: "
          "move rationale to README.md and detail to references/.")
    body = skill_md.read_text(encoding="utf-8")
    # The things SKILL.md must never lose while being shrunk.
    for needle, label in (
        ("## The workflow", "the ordered workflow"),
        ("## Control picker", "the control picker table"),
        ("## Templates", "the templates"),
        ("## Rules while writing", "the rules list"),
        ("## Pre-send checklist", "the pre-send checklist"),
        ("assets/patterns/", "a pointer to assets/patterns/"),
        ("layout-mapping.md", "a pointer to layout-mapping.md"),
        ("INDEX.md", "a pointer to the example INDEX.md"),
        ("pa_lint.py", "the lint step"),
        ("extend-existing-app.md", "the existing-app branch"),
        ("data-binding.md", "the data-binding branch"),
        ("test-snippets", "a pointer to the paste-test kit"),
    ):
        check(needle in body, f"SKILL.md still contains {label}", f"missing {needle!r}")

print("Example screens are valid YAML")
examples = sorted((SKILL_DIR / "assets" / "examples").glob("*.yaml"))
check(len(examples) >= 1, "at least one example screen exists")
for ex in examples:
    try:
        doc = yaml.safe_load(ex.read_text(encoding="utf-8"))
        top = next(iter(doc)) if isinstance(doc, dict) else None
        check(isinstance(doc, dict) and top in {"Screens", "App", "ComponentDefinitions"},
              f"{ex.name} parses and has a known top-level key", f"top-level key: {top!r}")
    except yaml.YAMLError as e:
        check(False, f"{ex.name} parses as YAML", str(e))

print("Control catalog (controls.yaml <-> confirmed-controls.md)")
catalog_path = SKILL_DIR / "references" / "controls.yaml"
catalog = None
if catalog_path.is_file():
    try:
        catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
        check(isinstance(catalog, dict), "controls.yaml parses as a YAML mapping")
    except yaml.YAMLError as e:
        check(False, "controls.yaml parses as YAML", str(e))

if isinstance(catalog, dict):
    for key in ("schema_version", "evidence_levels", "universal_properties", "controls"):
        check(key in catalog, f"controls.yaml has '{key}'")

    entries = catalog.get("controls") or []
    check(all(isinstance(e, dict) and {"name", "type", "evidence"} <= set(e)
              for e in entries),
          "every catalog entry has name/type/evidence")

    levels = set(catalog.get("evidence_levels") or [])
    bad_evidence = sorted({e.get("evidence") for e in entries} - levels)
    check(not bad_evidence, "every entry's evidence is a declared level",
          f"unknown: {bad_evidence}")

    # An entry without a source is an entry without evidence, which is the exact
    # failure mode this project exists to prevent.
    missing_source = [e.get("type") for e in entries if not str(e.get("source") or "").strip()]
    check(not missing_source, "every catalog entry cites a source", f"missing: {missing_source}")

    yaml_types = {e.get("type") for e in entries}

    # A harvest merge adds a control entry but deliberately does not edit the
    # hand-curated "not yet attempted" list; this is the check that catches the
    # leftover. See docs/harvesting.md.
    catalogued_bases = {str(t).split("@", 1)[0].rsplit("/", 1)[-1] for t in yaml_types}
    overlap = sorted(catalogued_bases & set(catalog.get("unattempted_controls") or []))
    check(not overlap,
          "no control is both catalogued and listed in unattempted_controls",
          f"remove from unattempted_controls: {overlap}")

    # Cross-check against the human-readable view: the two must not drift apart.
    md_text = (SKILL_DIR / "references" / "confirmed-controls.md").read_text(encoding="utf-8")
    section = md_text.split("## Control types", 1)[-1].split("\n## ", 1)[0]
    control_id_re = re.compile(r"^[A-Z][A-Za-z0-9]*(?:/[A-Z][A-Za-z0-9]*)?@\d+\.\d+\.\d+$")
    md_types = set()
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        for token in re.findall(r"`([^`]+)`", cells[1]):
            if control_id_re.match(token):
                md_types.add(token)
                break

    check(bool(md_types), "confirmed-controls.md control table is parseable")
    check(md_types <= yaml_types, "every control in confirmed-controls.md is in controls.yaml",
          f"missing from controls.yaml: {sorted(md_types - yaml_types)}")
    check(yaml_types <= md_types, "every control in controls.yaml is in confirmed-controls.md",
          f"missing from the markdown: {sorted(yaml_types - md_types)}")

print("Candidate control ids (control-ids-candidate.yaml)")
candidates_path = SKILL_DIR / "references" / "control-ids-candidate.yaml"
candidates = None
if candidates_path.is_file():
    try:
        candidates = yaml.safe_load(candidates_path.read_text(encoding="utf-8"))
        check(isinstance(candidates, dict), "control-ids-candidate.yaml parses as a mapping")
    except yaml.YAMLError as e:
        check(False, "control-ids-candidate.yaml parses as YAML", str(e))

if isinstance(candidates, dict):
    ids = candidates.get("control_ids") or []
    check(bool(ids), "control-ids-candidate.yaml lists control_ids")
    # The whole point of this file is that it is a hint, not evidence. A single entry
    # promoted here would quietly turn Microsoft's internal enum into a confirmation.
    not_unverified = [e.get("id") for e in ids
                      if not isinstance(e, dict) or e.get("evidence") != "unverified"]
    check(not not_unverified,
          "every candidate control id is marked evidence: unverified",
          f"not unverified: {not_unverified}")
    for key in ("upstream_repo", "upstream_path", "upstream_commit", "retrieved"):
        check(bool(str(candidates.get(key) or "").strip()),
              f"control-ids-candidate.yaml records '{key}'",
              "provenance is the only thing that makes this file re-checkable")

print("Linter accepts the bundled examples")
lint = ROOT / "scripts" / "pa_lint.py"
if lint.is_file() and examples:
    proc = subprocess.run(
        [sys.executable, str(lint), *[str(p) for p in examples], "--quiet"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
    )
    check(proc.returncode == 0,
          "pa_lint.py returns 0 for all three bundled examples",
          f"exit {proc.returncode}\n{proc.stdout}\n{proc.stderr}")


def lint_json(paths):
    """Run pa_lint.py over paths and return its JSON report, or None."""
    if not lint.is_file() or not paths:
        return None
    proc = subprocess.run(
        [sys.executable, str(lint), *[str(x) for x in paths], "--json"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        check(False, "pa_lint.py --json produced parseable output",
              f"exit {proc.returncode}\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}")
        return None


print("Pattern snippets (assets/patterns/)")
patterns = sorted((SKILL_DIR / "assets" / "patterns").glob("*.pa.yaml"))
check(len(patterns) >= 10, "assets/patterns/ holds the extracted snippets",
      f"found {len(patterns)}")

for pat in patterns:
    src = pat.read_text(encoding="utf-8")
    lines = src.splitlines()
    header = "\n".join(ln for ln in lines if ln.startswith("#"))
    missing = [f for f in PATTERN_HEADER_FIELDS if f"# {f}" not in header]
    check(not missing, f"{pat.name} header records {'/'.join(PATTERN_HEADER_FIELDS)}",
          f"missing: {missing}. A pattern without a cited Source and Evidence level is "
          "an unsourced claim, which is the failure mode this repo exists to prevent.")
    # The Source field has to name a real bundled example -- patterns are extracted,
    # never invented.
    cites = [ex.name for ex in examples if ex.name in header]
    check(bool(cites), f"{pat.name} cites a bundled example as its source",
          "no assets/examples/*.yaml filename appears in the header")
    cap = PATTERN_MAX_LINES_EXCEPTIONS.get(pat.name, PATTERN_MAX_LINES)
    check(PATTERN_MIN_LINES <= len(lines) <= cap,
          f"{pat.name} is {PATTERN_MIN_LINES}-{cap} lines",
          f"got {len(lines)}. Patterns are read instead of a 1,700-line example; "
          "split it or move detail into the header comment.")

report = lint_json(patterns)
if report:
    for f in report.get("files", []):
        name = Path(f["path"]).name
        check(f.get("verdict_code") == "safe",
              f"{name} lints SAFE TO PASTE",
              f"{f.get('verdict')}: "
              + "; ".join(x["message"] for x in f.get("findings", [])))

print("Paste-test snippets (assets/test-snippets/)")
snippets = sorted((SKILL_DIR / "assets" / "test-snippets").glob("*.pa.yaml"))
check(len(snippets) >= SNIPPET_MIN,
      f"assets/test-snippets/ holds at least {SNIPPET_MIN} paste tests",
      f"found {len(snippets)}")


def control_count(node) -> int:
    """Control instances under a Screens: mapping, counted recursively."""
    total = 0
    for screen in (node or {}).values():
        total += _children_count((screen or {}).get("Children"))
    return total


def _children_count(children) -> int:
    total = 0
    for item in children or []:
        if not isinstance(item, dict):
            continue
        for body in item.values():
            if isinstance(body, dict):
                total += 1 + _children_count(body.get("Children"))
    return total


for snip in snippets:
    src = snip.read_text(encoding="utf-8")
    header = "\n".join(ln for ln in src.splitlines() if ln.startswith("#"))
    missing = [f for f in SNIPPET_HEADER_FIELDS if f"# {f}" not in header]
    check(not missing, f"{snip.name} header records {'/'.join(SNIPPET_HEADER_FIELDS)}",
          f"missing: {missing}. A snippet without a stated Evidence line reads as a "
          "recommendation, which is the opposite of what this kit is.")
    # The kit's whole premise: a failure must be attributable to one control.
    try:
        doc = yaml.safe_load(src) or {}
        count = control_count(doc.get("Screens"))
        check(count == 1, f"{snip.name} contains exactly one control",
              f"found {count}. Two controls in one file means a paste failure cannot "
              "be attributed to either of them.")
    except yaml.YAMLError as e:
        check(False, f"{snip.name} parses as YAML", str(e))
    # One property per line is what makes bisecting-by-deletion work.
    check("UNVERIFIED below here" in src,
          f"{snip.name} marks where the unverified properties start",
          "the bisect marker is the line the user deletes downward from")

report = lint_json(snippets)
if report:
    for f in report.get("files", []):
        name = Path(f["path"]).name
        blocking = [x for x in f.get("findings", []) if x["layer"] in ("L0", "L1")]
        check(not blocking, f"{name} has no L0/L1 error",
              "; ".join(x["message"] for x in blocking))
        # L2 warnings are the POINT. A snippet that lints clean is either already
        # catalogued -- so it does not belong in the kit -- or the catalog drifted.
        check(any(x["layer"] == "L2" for x in f.get("findings", [])),
              f"{name} raises an L2 unverified warning",
              "nothing in this file is unverified any more; either it belongs in "
              "assets/patterns/ now, or controls.yaml changed underneath it")

print("docs/test-plan.md covers every snippet")
test_plan = ROOT / "docs" / "test-plan.md"
if test_plan.is_file() and snippets:
    plan = test_plan.read_text(encoding="utf-8")
    uncovered = [s.name for s in snippets if s.name not in plan]
    check(not uncovered, "every test-snippet file has a row in the results table",
          f"missing rows: {uncovered}. A snippet with nowhere to report its result "
          "will never be run.")
    check("controls.yaml" in plan,
          "test-plan.md says how a result gets into the catalog")

print("data-binding.md keeps every expression marked")
data_binding = SKILL_DIR / "references" / "data-binding.md"
if data_binding.is_file():
    text = data_binding.read_text(encoding="utf-8")
    # Every fenced yaml/text block is a Power Fx or .pa.yaml example, and the phase
    # brief is explicit: all of them are unverified until a Studio test says otherwise.
    unmarked = [body.splitlines()[0][:50]
                for _lang, body in re.findall(r"(?ms)^```(yaml|text)\n(.*?)^```", text)
                if "UNVERIFIED" not in body]
    check(not unmarked, "every yaml/text example in data-binding.md is marked UNVERIFIED",
          f"unmarked blocks start: {unmarked}")
    # Each recipe has to name the paste test that unblocks it, and that file has to
    # exist -- otherwise the pairing is decoration.
    # `schema-v3.pa.yaml` and friends are references/ files, not snippets.
    named = {n for n in re.findall(r"`([a-z0-9-]+\.pa\.yaml)`", text)
             if not (SKILL_DIR / "references" / n).is_file()}
    have = {s.name for s in snippets}
    check(named <= have, "every snippet data-binding.md names exists",
          f"named but missing: {sorted(named - have)}")
    check(bool(named), "data-binding.md pairs its recipes with paste-test snippets")
    check("schema-v3.pa.yaml" in text,
          "data-binding.md cites the bundled schema for the DataSources block")
    # The yaml blocks are complete documents, so they can be proven, not just claimed.
    blocks = re.findall(r"(?ms)^```yaml\n(.*?)^```", text)
    tmp = ROOT / ".validate-tmp-db"
    written = []
    try:
        if blocks:
            tmp.mkdir(exist_ok=True)
            for i, block in enumerate(blocks):
                f = tmp / f"data-binding-block-{i}.pa.yaml"
                f.write_text(block, encoding="utf-8")
                written.append(f)
        rep = lint_json(written)
        if rep:
            for f in rep.get("files", []):
                bad = [x for x in f.get("findings", []) if x["layer"] in ("L0", "L1")]
                check(not bad,
                      f"data-binding.md example ({Path(f['path']).name}) is valid pa.yaml",
                      "; ".join(x["message"] for x in bad))
    finally:
        for f in written:
            f.unlink(missing_ok=True)
        if tmp.is_dir():
            tmp.rmdir()

print("app_inventory.py stays inside its page budget")
inventory = ROOT / "scripts" / "app_inventory.py"
fixture = ROOT / "tests" / "apps" / "ten-screen-app"
if inventory.is_file() and fixture.is_dir():
    proc = subprocess.run([sys.executable, str(inventory), str(fixture)],
                          capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
    check(proc.returncode == 0, "app_inventory.py runs against the 10-screen fixture",
          f"exit {proc.returncode}\n{proc.stderr[-500:]}")
    size = len(proc.stdout.encode("utf-8"))
    check(size < INVENTORY_MAX_BYTES,
          f"the 10-screen summary is under {INVENTORY_MAX_BYTES} bytes",
          f"got {size}. Summarise harder -- the tool exists to save context, not to "
          "reformat the source.")
    for needle, label in (("SCREENS", "the screen list"),
                          ("TYPES:", "the control types with their versions"),
                          ("ONSTART", "the App.OnStart variables"),
                          ("DATASOURCES", "the data sources"),
                          ("COMPONENTS", "the component definitions"),
                          ("_1", "the collision warning")):
        check(needle in proc.stdout, f"the summary still carries {label}",
              f"missing {needle!r}")

print("layout-mapping.md recommends only catalogued properties")
layout_md = SKILL_DIR / "references" / "layout-mapping.md"
if layout_md.is_file() and isinstance(catalog, dict):
    entries = catalog.get("controls") or []
    # Every property name the catalog knows about, at any evidence level. An
    # unverified property is still a real property; an absent one is an invention.
    known = set(catalog.get("universal_properties") or [])
    for e in entries:
        for key in ("properties_confirmed", "properties_example_file",
                    "properties_unverified"):
            known |= set(e.get(key) or [])
    # Not properties, but legitimately written in backticks: the .pa.yaml structural
    # keys, the control base names, and the Variant values -- all derived from the
    # catalog itself rather than hand-listed, so they cannot drift.
    structural = {"Screens", "Properties", "Children", "Control", "Variant",
                  "App", "ComponentDefinitions"}
    for e in entries:
        structural.add(str(e.get("name")))
        structural.add(str(e.get("type")).split("@", 1)[0].rsplit("/", 1)[-1])
        if e.get("variant"):
            structural.add(str(e["variant"]))
    vocabulary = known | structural

    def resolves(token: str) -> bool:
        """True if token is a catalogued property, a structural key, or a Prop* stem."""
        if token in vocabulary:
            return True
        if token.endswith("*"):
            stem = token[:-1]
            return any(k.startswith(stem) for k in vocabulary)
        return False

    for md in (layout_md, skill_md):
        prose = re.sub(r"(?ms)^```.*?^```", "", md.read_text(encoding="utf-8"))
        offenders = set()
        for span in set(re.findall(r"`([^`\n]+)`", prose)):
            # "Name: =value" -- unambiguously a property being written.
            assigned = re.match(r"^([A-Za-z][A-Za-z0-9.]*\*?)\s*:", span)
            if assigned:
                if not resolves(assigned.group(1)):
                    offenders.add(assigned.group(1))
                continue
            # A bare multi-word CamelCase identifier reads as a property name
            # (LayoutGap, PaddingTop, DropShadow, FillPortions...). Single-word
            # tokens are too ambiguous to flag -- they are just as likely prose.
            if re.match(r"^(?:[A-Z][a-z0-9]+){2,}\*?$", span) and not resolves(span):
                offenders.add(span)
        check(not offenders,
              f"{md.name} names no property absent from controls.yaml",
              f"not in the catalog: {sorted(offenders)}. Either add it to "
              "controls.yaml with a cited Studio test, or stop recommending it.")

print("layout-mapping.md's worked example lints clean")
if layout_md.is_file():
    blocks = re.findall(r"(?ms)^```yaml\n(.*?)^```", layout_md.read_text(encoding="utf-8"))
    check(bool(blocks), "layout-mapping.md contains a worked .pa.yaml example")
    tmp = ROOT / ".validate-tmp"
    written = []
    try:
        if blocks:
            tmp.mkdir(exist_ok=True)
            for i, block in enumerate(blocks):
                f = tmp / f"layout-mapping-block-{i}.pa.yaml"
                f.write_text(block, encoding="utf-8")
                written.append(f)
        rep = lint_json(written)
        if rep:
            for f in rep.get("files", []):
                check(f.get("verdict_code") == "safe",
                      f"layout-mapping.md worked example ({Path(f['path']).name}) "
                      "lints SAFE TO PASTE",
                      f"{f.get('verdict')}: "
                      + "; ".join(x["message"] for x in f.get("findings", [])))
    finally:
        for f in written:
            f.unlink(missing_ok=True)
        if tmp.is_dir():
            tmp.rmdir()

print("Eval cases (tests/evals/)")
evals_dir = ROOT / "tests" / "evals"
check(evals_dir.is_dir(), "tests/evals/ present",
      "the eval fixtures scripts/run_eval.py scores against")
case_dirs = sorted(d for d in evals_dir.iterdir()
                   if d.is_dir()) if evals_dir.is_dir() else []
check(len(case_dirs) >= EVAL_CASES_MIN,
      f"at least {EVAL_CASES_MIN} eval cases exist", f"found {len(case_dirs)}")
missing_required = REQUIRED_EVAL_CASES - {d.name for d in case_dirs}
check(not missing_required,
      "the five archetypes all have a case",
      f"missing: {sorted(missing_required)}. Each one covers a layout shape the "
      "others do not, and the hard case covers the honesty path.")

for case_dir in case_dirs:
    name = case_dir.name
    for filename in ("mockup.html", "expectations.yaml", "notes.md"):
        check((case_dir / filename).is_file(), f"{name}/{filename} present",
              "a case is a mockup, its assertions, and a written reason to exist")

    mockup = case_dir / "mockup.html"
    if mockup.is_file():
        html = mockup.read_text(encoding="utf-8")
        # A case that needs the network scores differently on a machine without it.
        external = re.search(r"""(?:src|href)\s*=\s*["'](?:https?:)?//""", html, re.I)
        imported = re.search(r"""@import\s+(?:url\()?['"]?(?:https?:)?//""", html, re.I)
        check(external is None and imported is None,
              f"{name}/mockup.html is self-contained",
              "it pulls an external asset; a fixture that needs the network is not "
              "a fixture")

    spec_path = case_dir / "expectations.yaml"
    if not spec_path.is_file():
        continue
    try:
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8-sig")) or {}
        check(isinstance(spec, dict), f"{name}/expectations.yaml is a mapping")
    except yaml.YAMLError as e:
        check(False, f"{name}/expectations.yaml parses", str(e))
        continue
    if not isinstance(spec, dict):
        continue

    asserted = [b for b in EVAL_ASSERTION_BLOCKS if b in spec]
    check(len(asserted) >= 3,
          f"{name}/expectations.yaml asserts something worth running",
          f"only {asserted}. A case with one or two blocks is not measuring enough "
          "to tell a good conversion from a bad one.")

    # Every waiver has to say why. A deviation nobody can read is indistinguishable
    # from a bug that was never fixed.
    ref = spec.get("reference") or {}
    for entry in ref.get("known_deviations") or []:
        label = (entry or {}).get("check", "<unnamed>")
        check(bool((entry or {}).get("check")) and bool((entry or {}).get("reason")),
              f"{name} known deviation {label} states a reason",
              "a waiver without a stated reason hides a regression")
    if ref.get("output"):
        target = (case_dir / ref["output"]).resolve()
        check(target.is_file(), f"{name} reference output exists",
              f"{ref['output']} does not resolve to a file")

    # The hard case must assert effects controls.yaml actually takes a position on.
    if "limitations" in spec and isinstance(catalog, dict):
        known_ids = {e.get("id") for e in (catalog.get("impossible_css") or [])}
        for entry in spec["limitations"].get("declared") or []:
            eid = (entry or {}).get("id")
            check(eid in known_ids,
                  f"{name} limitation {eid!r} is in controls.yaml's impossible_css",
                  "asserting an effect the catalog takes no position on means the "
                  "case and the skill disagree about what is impossible")

# The acceptance criterion, run rather than asserted: the scorer must score the
# bundled examples against their matching cases without crashing.
if case_dirs:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_eval.py"), "--json"],
        capture_output=True, text=True, cwd=str(ROOT))
    payload = None
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        pass
    check(proc.returncode in (0, 1) and payload is not None,
          "run_eval.py scores the bundled references without crashing",
          f"exit {proc.returncode}: {proc.stderr.strip()[:300]}")
    if payload:
        scored = {r["case"] for r in payload["results"]}
        check(len(scored) >= 3,
              "at least three cases carry a reference output",
              f"scored: {sorted(scored)}")
        bad = [(r["case"], row["check"], row["result"])
               for r in payload["results"] for row in r["rows"]
               if row["result"] in ("FAIL", "XPASS")]
        check(not bad, "the eval self-check is clean",
              f"{bad[:4]} -- an XPASS means a known deviation is stale and its "
              "waiver should be deleted; a FAIL means the references drifted.")
    check((ROOT / "docs" / "evals.md").is_file(), "docs/evals.md present",
          "the manual loop; the scorer is deliberately not wired to a model")
    evals_doc = (ROOT / "docs" / "evals.md")
    if evals_doc.is_file():
        text = evals_doc.read_text(encoding="utf-8")
        check("CI does not run a model" in text,
              "docs/evals.md states the boundary",
              "the one thing a reader must not get wrong is that the scored half "
              "and the generated half are different halves")

print("Plugin metadata")
plugin_json = ROOT / ".claude-plugin" / "plugin.json"
market_json = ROOT / ".claude-plugin" / "marketplace.json"
plugin = market = None
try:
    plugin = json.loads(plugin_json.read_text(encoding="utf-8"))
    check(True, "plugin.json is valid JSON")
except (OSError, json.JSONDecodeError) as e:
    check(False, "plugin.json is valid JSON", str(e))
try:
    market = json.loads(market_json.read_text(encoding="utf-8"))
    check(True, "marketplace.json is valid JSON")
except (OSError, json.JSONDecodeError) as e:
    check(False, "marketplace.json is valid JSON", str(e))

if plugin:
    check(plugin.get("name") == "power-app-yaml", "plugin.json name is 'power-app-yaml'")
    check(bool(re.match(r"^\d+\.\d+\.\d+$", str(plugin.get("version", "")))),
          "plugin.json version is SemVer", f"got {plugin.get('version')!r}")
if plugin and market:
    names = [p.get("name") for p in market.get("plugins", [])]
    check(plugin.get("name") in names,
          "marketplace.json lists the plugin", f"plugins: {names}")

print("CHANGELOG mentions the current version")
if plugin:
    cl = (ROOT / "CHANGELOG.md")
    check(cl.is_file() and f"[{plugin.get('version')}]" in cl.read_text(encoding="utf-8"),
          f"CHANGELOG.md has a section for {plugin.get('version')}")

print("Internal Markdown links resolve")
md_files = [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]
link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
for md in md_files:
    for target in link_re.findall(md.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path_part = target.split("#", 1)[0]
        if not path_part:
            continue
        resolved = (md.parent / path_part).resolve()
        check(resolved.exists(),
              f"link in {md.relative_to(ROOT).as_posix()} -> {target}")

print()
if errors:
    print(f"{len(errors)} of {checks} checks FAILED")
    sys.exit(1)
print(f"All {checks} checks passed")
