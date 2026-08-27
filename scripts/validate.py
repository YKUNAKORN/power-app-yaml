#!/usr/bin/env python3
"""Repository sanity checks for the power-app-yaml skill.

Run locally before opening a PR:

    python scripts/validate.py

Exits non-zero if anything fails. Requires PyYAML (`pip install pyyaml`).
"""

from __future__ import annotations

import json
import re
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
