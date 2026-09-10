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
check((ROOT / "scripts" / "pa_lint.py").is_file(), "scripts/pa_lint.py present")
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
        check(isinstance(desc, str) and len(desc.strip()) >= 40,
              "frontmatter has a substantive 'description'")

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
