#!/usr/bin/env python3
"""Offline verification loop for Power Apps Canvas .pa.yaml files.

Proves a .pa.yaml is correct BEFORE it reaches the user, instead of making the user act
as the compiler by pasting into Power Apps Studio and reading back errors.

    python scripts/pa_lint.py FILE [FILE...] [--catalog PATH] [--candidates PATH]
                              [--json] [--strict] [--quiet]

Four layers, run in order. A layer that makes later layers meaningless stops the run:

  L0  YAML parse            ERROR    the file must load at all
  L1  JSON Schema           ERROR    maps to Studio PA1001 (blocks the whole paste)
  L2  Catalog lint          WARNING  maps to Studio PA2108 (unverified control/property)
                                     A control type absent from the catalog but present
                                     in references/control-ids-candidate.yaml is
                                     reported as "known to Microsoft's tooling but not
                                     yet paste-tested here" -- same severity, better
                                     sentence. Never treated as evidence.
  L3  Convention checks     WARNING  SKILL.md's own rules

Exit codes:  0 clean  |  1 any L0/L1 error  |  2 warnings only AND --strict

Requires PyYAML. `jsonschema` is optional: without it L1 is skipped and the run is
reported as degraded rather than failing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: PyYAML is not installed. Run: pip install pyyaml", file=sys.stderr)
    raise SystemExit(2)

try:
    import jsonschema
    HAVE_JSONSCHEMA = True
except ImportError:  # pragma: no cover - exercised on minimal installs
    HAVE_JSONSCHEMA = False

ROOT = Path(__file__).resolve().parent.parent
SKILL_REFS = ROOT / "skills" / "power-app-yaml" / "references"
DEFAULT_CATALOG = SKILL_REFS / "controls.yaml"
DEFAULT_CANDIDATES = SKILL_REFS / "control-ids-candidate.yaml"
SCHEMA_PATH = SKILL_REFS / "schema-v3.pa.yaml"

ROOT_KEYS = ("App", "Screens", "ComponentDefinitions", "DataSources", "EditorState")

ERROR, WARNING = "error", "warning"


# --------------------------------------------------------------------------- findings


class Finding:
    __slots__ = ("layer", "check", "severity", "path", "line", "column", "message",
                 "detail", "snippet")

    def __init__(self, layer, check, severity, message, path=None, line=None,
                 column=None, detail=None, snippet=None):
        self.layer = layer
        self.check = check
        self.severity = severity
        self.message = message
        self.path = path
        self.line = line
        self.column = column
        self.detail = detail
        self.snippet = snippet

    def as_dict(self):
        return {
            "layer": self.layer,
            "check": self.check,
            "severity": self.severity,
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "detail": self.detail,
            "snippet": self.snippet,
        }


def fmt_path(parts) -> str:
    out = ""
    for part in parts:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += ("." if out else "") + str(part)
    return out or "<root>"


# ------------------------------------------------------------------ YAML node helpers
#
# The document is composed (not just loaded) so every control and property keeps its
# source line, which the raw-text checks in L2/L3 need.


def map_items(node):
    return list(node.value) if isinstance(node, yaml.MappingNode) else []


def map_get(node, key):
    for key_node, value_node in map_items(node):
        if isinstance(key_node, yaml.ScalarNode) and key_node.value == key:
            return value_node
    return None


def map_get_pair(node, key):
    for key_node, value_node in map_items(node):
        if isinstance(key_node, yaml.ScalarNode) and key_node.value == key:
            return key_node, value_node
    return None, None


def seq_items(node):
    return list(node.value) if isinstance(node, yaml.SequenceNode) else []


def scalar_of(node):
    return node.value if isinstance(node, yaml.ScalarNode) else None


def line_of(node):
    return node.start_mark.line + 1 if node is not None else None


class ControlRef:
    """One control instance in the composed tree."""

    __slots__ = ("name", "name_node", "body", "screen", "path", "ctype",
                 "parent_type", "parent_variant")

    def __init__(self, name, name_node, body, screen, path, parent_type, parent_variant):
        self.name = name
        self.name_node = name_node
        self.body = body
        self.screen = screen
        self.path = path
        self.ctype = scalar_of(map_get(body, "Control"))
        self.parent_type = parent_type
        self.parent_variant = parent_variant

    @property
    def variant(self):
        return scalar_of(map_get(self.body, "Variant"))

    @property
    def properties(self):
        """[(name, key_node, value_node)] for this control's Properties block."""
        props = map_get(self.body, "Properties")
        out = []
        for key_node, value_node in map_items(props):
            if isinstance(key_node, yaml.ScalarNode):
                out.append((key_node.value, key_node, value_node))
        return out


def walk_controls(root_node):
    """Yield every ControlRef under Screens:, depth first, with its YAML path."""
    screens = map_get(root_node, "Screens")
    for screen_key, screen_node in map_items(screens):
        screen_name = scalar_of(screen_key)
        base = ["Screens", screen_name]
        yield from _walk_children(
            map_get(screen_node, "Children"), screen_name, base, None, None
        )


def _walk_children(children_node, screen, base_path, parent_type, parent_variant):
    for index, item in enumerate(seq_items(children_node)):
        for name_node, body in map_items(item):
            name = scalar_of(name_node)
            path = base_path + ["Children", index, name]
            ref = ControlRef(name, name_node, body, screen, path,
                             parent_type, parent_variant)
            yield ref
            yield from _walk_children(
                map_get(body, "Children"), screen, path, ref.ctype, ref.variant
            )


def node_at_path(root_node, parts):
    """Resolve a jsonschema absolute_path onto the composed tree. Returns (key, value)."""
    key_node, node = None, root_node
    for part in parts:
        if isinstance(part, int):
            items = seq_items(node)
            if part >= len(items):
                return key_node, node
            key_node, node = None, items[part]
        else:
            found_key, found_value = map_get_pair(node, part)
            if found_value is None:
                return key_node, node
            key_node, node = found_key, found_value
    return key_node, node


# ---------------------------------------------------------------------------- catalog


class Catalog:
    def __init__(self, data):
        self.universal = set(data.get("universal_properties") or [])
        self.by_type = {}
        self.by_base = {}
        for entry in data.get("controls") or []:
            self.by_type[entry["type"]] = entry
            self.by_base.setdefault(entry["type"].split("@", 1)[0], []).append(entry)
        self.unattempted = set(data.get("unattempted_controls") or [])
        self.studio_version = data.get("studio_version_tested")

    def lookup(self, ctype):
        return self.by_type.get(ctype)

    def same_base(self, ctype):
        return self.by_base.get((ctype or "").split("@", 1)[0], [])

    def accepted_properties(self, entry):
        return (set(entry.get("properties_confirmed") or [])
                | set(entry.get("properties_example_file") or [])
                | self.universal)


def load_catalog(path: Path) -> Catalog:
    return Catalog(yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {})


class CandidateIds:
    """Control type ids Microsoft's tooling knows about but this repo has not tested.

    Strictly a wording aid. Membership never downgrades a warning and never counts as
    evidence -- see references/control-ids-candidate.yaml for why.
    """

    def __init__(self, data):
        data = data or {}
        self.by_id = {}
        for entry in data.get("control_ids") or []:
            if isinstance(entry, dict) and entry.get("id"):
                self.by_id[str(entry["id"])] = entry
        self.commit = data.get("upstream_commit")
        self.path = data.get("upstream_path")

    def lookup(self, base):
        return self.by_id.get(base)


def load_candidates(path: Path) -> CandidateIds:
    """Missing or unreadable is fine -- the linter just falls back to the old wording."""
    try:
        return CandidateIds(yaml.safe_load(path.read_text(encoding="utf-8-sig")))
    except (OSError, yaml.YAMLError):
        return CandidateIds({})


# --------------------------------------------------------------------- L0: YAML parse

FLOW_PROPS_RE = re.compile(r"^\s*Properties:\s*\{")


def scan_flow_style_rgba(lines):
    """Detect flow-style Properties containing RGBA(.

    This is a raw-text check on purpose. The trap does NOT reliably raise a YAML error:
    `Properties: {Fill: =RGBA(255, 255, 255, 1)}` parses happily into
    {'Fill': '=RGBA(255', 255: None, '1)': None} -- silent corruption, which is worse
    than a parse failure. So the corrupting shape is caught before parsing.
    """
    findings = []
    index = 0
    while index < len(lines):
        if FLOW_PROPS_RE.match(lines[index]):
            chunk, depth, cursor = [], 0, index
            while cursor < len(lines):
                chunk.append(lines[cursor])
                depth += lines[cursor].count("{") - lines[cursor].count("}")
                if depth <= 0:
                    break
                cursor += 1
            blob = "\n".join(chunk)
            if "RGBA(" in blob:
                findings.append(Finding(
                    "L0", "L0.flow-style-rgba", ERROR,
                    "Flow-style Properties containing RGBA(...) -- the commas inside "
                    "RGBA(...) are parsed as YAML separators, so this block does not "
                    "mean what it looks like.",
                    line=index + 1, column=lines[index].index("{") + 1,
                    detail=(
                        "It usually does not even raise a YAML error; it silently "
                        "becomes {'Fill': '=RGBA(255', 255: None, ...}. Rewrite it "
                        "block-style:\n"
                        "    Properties:\n"
                        "      Text: =\"Dashboard\"\n"
                        "      Fill: =RGBA(255, 255, 255, 1)"
                    ),
                ))
            index = cursor + 1
            continue
        index += 1
    return findings


def parse_layer(text, lines):
    """Return (findings, composed_root, plain_document)."""
    findings = scan_flow_style_rgba(lines)
    if findings:
        return findings, None, None

    try:
        root_node = yaml.compose(text)
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        line = mark.line + 1 if mark else None
        column = mark.column + 1 if mark else None
        problem = getattr(exc, "problem", None) or "could not parse this file as YAML"
        near = lines[mark.line].strip() if mark and mark.line < len(lines) else ""

        # The spec's special case: if the failing region is a flow mapping with RGBA(,
        # report the trap rather than the raw parser complaint.
        if near and "{" in near and "RGBA(" in near:
            return [Finding(
                "L0", "L0.flow-style-rgba", ERROR,
                "Flow-style Properties containing RGBA(...) -- the commas inside "
                "RGBA(...) are parsed as YAML separators.",
                line=line, column=column,
                detail="Rewrite the block block-style, one property per line.",
            )], None, None

        return [Finding(
            "L0", "L0.yaml-parse", ERROR,
            f"YAML will not parse: {problem}.",
            line=line, column=column,
            detail=f"near: {near}" if near else None,
        )], None, None

    if document is None:
        return [Finding("L0", "L0.yaml-parse", ERROR, "File is empty.")], None, None
    return [], root_node, document


# -------------------------------------------------------------- L1: JSON Schema (PA1001)


def _is_pfx_formula_schema(schema) -> bool:
    if not isinstance(schema, dict):
        return False
    for sub in schema.get("oneOf") or []:
        if isinstance(sub, dict) and sub.get("pattern") == "^=.*":
            return True
    return False


def _classify(err):
    """Map a jsonschema error onto (check_id, sentence, detail). Never leak raw text."""
    parts = list(err.absolute_path)
    tail = parts[-1] if parts else None
    schema = err.schema if isinstance(err.schema, dict) else {}

    if _is_pfx_formula_schema(schema) or (
        err.validator == "pattern" and err.validator_value == "^=.*"
    ):
        shown = err.instance if isinstance(err.instance, str) else repr(err.instance)
        return (
            "L1.formula-missing-equals",
            f"Property value must start with '=' -- found {shown!r}.",
            f"Every .pa.yaml property value is a Power Fx formula. Write: {tail}: ="
            f'"{shown}"' if isinstance(err.instance, str) else
            "Every .pa.yaml property value is a Power Fx formula and must start with '='.",
        )

    if err.validator == "additionalProperties":
        allowed = set(schema.get("properties") or {})
        present = set(err.instance) if isinstance(err.instance, dict) else set()
        unexpected = sorted(str(k) for k in present - allowed)
        shown = ", ".join(repr(k) for k in unexpected) or "an unexpected key"
        if not parts:
            return (
                "L1.unknown-root-key",
                f"{shown} is not allowed at the top level of a .pa.yaml file.",
                "A control cannot sit at the document root. Wrap it in the full "
                "structure:\n    Screens:\n      MyScreen:\n        Children:\n"
                f"          - {unexpected[0] if unexpected else 'myControl'}:\n"
                "              Control: Label@2.5.1\n"
                f"Allowed root keys: {', '.join(ROOT_KEYS)}.",
            )
        return (
            "L1.unexpected-key",
            f"{shown} is not an allowed key here.",
            f"Allowed keys at this level: {', '.join(sorted(allowed))}."
            if allowed else None,
        )

    if tail == "Control" or (
        err.validator == "pattern"
        and str(err.validator_value).startswith("^([A-Z]")
    ):
        return (
            "L1.invalid-control-id",
            f"{err.instance!r} is not a valid control type id.",
            "A control id looks like 'Label@2.5.1' or 'Classic/Button@2.2.0': an "
            "optional Prefix/ (capitalised), a capitalised name, and an optional "
            "@major.minor.patch version.",
        )

    return ("L1.schema", "This value does not match the pa.yaml v3.0 schema.", None)


def schema_layer(document, root_node, schema):
    validator = jsonschema.Draft7Validator(schema)
    findings, seen = [], set()
    errors = sorted(validator.iter_errors(document),
                    key=lambda e: (len(e.absolute_path), list(map(str, e.absolute_path))))
    for err in errors:
        check, message, detail = _classify(err)
        path = fmt_path(err.absolute_path)
        if (check, path) in seen:
            continue
        seen.add((check, path))
        key_node, value_node = node_at_path(root_node, err.absolute_path)
        anchor = key_node or value_node
        findings.append(Finding(
            "L1", check, ERROR, message, path=path,
            line=line_of(anchor),
            column=anchor.start_mark.column + 1 if anchor is not None else None,
            detail=detail,
        ))

    # A control id failure trips both the pattern branch and the enclosing oneOf.
    # Keep the specific finding and drop the generic one at the same path.
    specific = {f.path for f in findings if f.check == "L1.invalid-control-id"}
    return [f for f in findings
            if not (f.check == "L1.schema" and f.path in specific)]


# ------------------------------------------------------------ L2: catalog lint (PA2108)


def _emit_scalar(value):
    """Render a property value for a generated snippet without breaking YAML."""
    if value is None:
        return '""'
    if " #" in value or value.strip() != value:
        return "'" + value.replace("'", "''") + "'"
    return value


def make_snippet(ctrl: ControlRef, only_property: str | None = None) -> str:
    """Build a full-wrapper, single-control .pa.yaml the user can paste-test as-is."""
    lines = [
        "# Paste-test this on a blank screen BEFORE trusting the full file.",
        "Screens:",
        "  PasteTest:",
        "    Children:",
        f"      - {ctrl.name}:",
        f"          Control: {ctrl.ctype}",
    ]
    variant = ctrl.variant
    if variant:
        lines.append(f"          Variant: {variant}")

    props = [(n, v) for n, _k, v in ctrl.properties
             if only_property is None or n == only_property]
    if props:
        lines.append("          Properties:")
        for name, value_node in props:
            lines.append(f"            {name}: {_emit_scalar(scalar_of(value_node))}")
    return "\n".join(lines) + "\n"


def catalog_layer(controls, catalog: Catalog, candidates: "CandidateIds | None" = None):
    candidates = candidates or CandidateIds({})
    findings = []
    for ctrl in controls:
        path = fmt_path(ctrl.path)
        entry = catalog.lookup(ctrl.ctype)

        if entry is None:
            base = (ctrl.ctype or "").split("@", 1)[0]
            siblings = catalog.same_base(ctrl.ctype)
            candidate = candidates.lookup(base)
            check = "L2.unverified-control-type"
            message = (f"Unverified control type {ctrl.ctype!r} -- paste-test in "
                       "isolation before trusting it.")
            if siblings:
                known = ", ".join(e["type"] for e in siblings)
                detail = (f"The catalog has {known}. A version-only difference is "
                          "usually harmless -- Studio warns (PA2105/PA2106) and "
                          "substitutes the current version -- but it is not confirmed.")
            elif candidate is not None:
                # Known to Microsoft's tooling, unproven here. A better sentence than
                # "unknown control", and nothing more than that: still a warning, still
                # needs a Studio test.
                check = "L2.candidate-control-type"
                message = (f"Control type {ctrl.ctype!r} is known to Microsoft's "
                           "tooling but not yet paste-tested here -- paste-test it in "
                           "isolation before trusting it.")
                detail = (
                    f"{base!r} appears in Microsoft's first-party control id enum "
                    f"({candidates.path or 'PowerApps-Tooling'}"
                    + (f" @ {candidates.commit[:7]}" if candidates.commit else "")
                    + "), mirrored here as references/control-ids-candidate.yaml. "
                    "That enum ships only in Microsoft's source tree -- the published "
                    "schema this repo bundles leaves the enum open -- and it carries "
                    "no @version and no property list. So it tells you the id is "
                    "plausible, not that this Studio build accepts it, and it says "
                    "nothing at all about the properties you set below."
                )
                if candidate.get("catalog"):
                    detail += f" Catalog note: {candidate['catalog']}."
                if base in catalog.unattempted:
                    detail += (" It is also on the catalog's 'not yet attempted' list: "
                               "no paste evidence either way.")
            elif base in catalog.unattempted:
                detail = ("This control is on the catalog's 'not yet attempted' list: "
                          "no evidence either way. Do not assume property names carry "
                          "over from a similar control.")
            else:
                detail = ("Not in the catalog and not in Microsoft's first-party "
                          "control id enum either, so unverified by definition. The "
                          "JSON Schema cannot catch this -- the published pa.yaml "
                          "schema leaves the control id enum open -- so Studio is the "
                          "only oracle.")
            findings.append(Finding(
                "L2", check, WARNING, message,
                path=path, line=line_of(ctrl.name_node), detail=detail,
                snippet=make_snippet(ctrl),
            ))
            continue

        accepted = catalog.accepted_properties(entry)
        flagged_unverified = set(entry.get("properties_unverified") or [])
        for name, key_node, _value in ctrl.properties:
            if name in flagged_unverified:
                detail = (f"The catalog lists {name} as unverified on "
                          f"{entry['type']}: {entry.get('notes') or 'no evidence.'}")
            elif name not in accepted:
                detail = ("Not in this control's confirmed list and not a universal "
                          f"property ({', '.join(sorted(catalog.universal))}). The "
                          "schema accepts any property name, so only a Studio test "
                          "settles it.")
            else:
                continue
            findings.append(Finding(
                "L2", "L2.unverified-property", WARNING,
                f"Unverified property {name!r} on {ctrl.ctype} -- paste-test in "
                "isolation before trusting it.",
                path=f"{path}.Properties.{name}", line=line_of(key_node),
                detail=detail, snippet=make_snippet(ctrl, only_property=name),
            ))
    return findings


# ------------------------------------------------------- L3: convention checks (SKILL.md)

NAVIGATE_RE = re.compile(
    r"Navigate\(\s*(?:'([^']+)'|\"([^\"]+)\"|([A-Za-z_][A-Za-z0-9_]*))"
)


def _line_has_comment(lines, node):
    """True if a '#' comment follows this node on its source line."""
    if node is None:
        return False
    index = node.start_mark.line
    if index >= len(lines):
        return False
    after = lines[index][node.end_mark.column:] if node.end_mark.line == index else lines[index]
    return "#" in after


def _unverified_tagged(lines, *nodes):
    for node in nodes:
        if node is None:
            continue
        index = node.start_mark.line
        if index < len(lines) and "UNVERIFIED" in lines[index].upper():
            return True
    return False


def convention_layer(controls, root_node, lines, l2_findings):
    findings = []
    screens = {scalar_of(k) for k, _v in map_items(map_get(root_node, "Screens"))}

    # 1. Navigate() targets must exist, unless flagged as a placeholder in a comment.
    for ctrl in controls:
        for name, _key_node, value_node in ctrl.properties:
            text = scalar_of(value_node) or ""
            if "Navigate(" not in text:
                continue
            for match in NAVIGATE_RE.finditer(text):
                target = next(g for g in match.groups() if g)
                if target in screens or _line_has_comment(lines, value_node):
                    continue
                findings.append(Finding(
                    "L3", "L3.navigate-target-missing", WARNING,
                    f"{name} navigates to {target!r}, which is not a screen in this file.",
                    path=f"{fmt_path(ctrl.path)}.Properties.{name}",
                    line=line_of(value_node),
                    detail=("Add the screen, or keep the placeholder and comment on "
                            "the same line that it is not wired up yet. Screens in "
                            f"this file: {', '.join(sorted(screens)) or '(none)'}."),
                ))

    # 2. Duplicate control names within one screen (Studio renames these silently).
    seen_names = {}
    for ctrl in controls:
        key = (ctrl.screen, ctrl.name)
        if key in seen_names:
            findings.append(Finding(
                "L3", "L3.duplicate-control-name", WARNING,
                f"Control name {ctrl.name!r} is used more than once in screen "
                f"{ctrl.screen!r}.",
                path=fmt_path(ctrl.path), line=line_of(ctrl.name_node),
                detail=(f"First used at line {seen_names[key]}. Studio appends _1, _2 "
                        "on paste without erroring, so the names you wrote and the "
                        "names in the app will quietly diverge."),
            ))
        else:
            seen_names[key] = line_of(ctrl.name_node)

    # 3. X/Y inside a GroupContainer that is not ManualLayout.
    for ctrl in controls:
        parent_base = (ctrl.parent_type or "").split("@", 1)[0]
        if parent_base != "GroupContainer" or ctrl.parent_variant == "ManualLayout":
            continue
        used = [n for n, _k, _v in ctrl.properties if n in ("X", "Y")]
        if used:
            findings.append(Finding(
                "L3", "L3.xy-in-non-manual-container", WARNING,
                f"{ctrl.name} sets {'/'.join(used)} inside a GroupContainer whose "
                f"Variant is {ctrl.parent_variant!r}, not 'ManualLayout'.",
                path=fmt_path(ctrl.path), line=line_of(ctrl.name_node),
                detail=("Only ManualLayout honours child X/Y. Under an auto-layout "
                        "variant the coordinates are ignored and the screen lays out "
                        "differently from the mockup."),
            ))

    # 4. Anything L2 flagged must carry a '# UNVERIFIED' comment (SKILL.md rule 8).
    by_path = {fmt_path(c.path): c for c in controls}
    reported = set()
    for finding in l2_findings:
        ctrl_path = finding.path.split(".Properties.", 1)[0]
        ctrl = by_path.get(ctrl_path)
        if ctrl is None or ctrl_path in reported:
            continue
        control_key, _ = map_get_pair(ctrl.body, "Control")
        prop_key = None
        if ".Properties." in finding.path:
            wanted = finding.path.rsplit(".Properties.", 1)[1]
            for name, key_node, _v in ctrl.properties:
                if name == wanted:
                    prop_key = key_node
        if _unverified_tagged(lines, ctrl.name_node, control_key, prop_key):
            continue
        reported.add(ctrl_path)
        findings.append(Finding(
            "L3", "L3.missing-unverified-comment", WARNING,
            f"{ctrl.name} has unverified items but carries no '# UNVERIFIED' comment.",
            path=ctrl_path, line=line_of(ctrl.name_node),
            detail=("SKILL.md rule 8: tag every control/property you are not sure of, "
                    "so a guess is never handed over looking like a confirmed fact. "
                    "Add a trailing comment, e.g.\n"
                    f"      - {ctrl.name}:  # UNVERIFIED - not in the catalog; paste-test first"),
        ))
    return findings


# ------------------------------------------------------------------------ orchestration


def lint_file(path: Path, catalog: Catalog, schema, candidates=None):
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()

    findings, root_node, document = parse_layer(text, lines)
    degraded = None

    if not findings:
        if schema is not None:
            findings += schema_layer(document, root_node, schema)
        else:
            degraded = ("jsonschema is not installed -- layer L1 (schema / PA1001) was "
                        "skipped. Install it with: pip install jsonschema")

        if not any(f.severity == ERROR for f in findings):
            controls = list(walk_controls(root_node))
            l2 = catalog_layer(controls, catalog, candidates)
            findings += l2
            findings += convention_layer(controls, root_node, lines, l2)

    errors = sum(1 for f in findings if f.severity == ERROR)
    warnings = sum(1 for f in findings if f.severity == WARNING)

    if errors:
        code, verdict = "will_fail", f"VERDICT: WILL FAIL — {errors} blocking error(s)"
    elif degraded:
        # The layer that catches PA1001 did not run, so "safe" would be a claim this
        # run cannot back up. Never report SAFE TO PASTE on an unchecked file.
        suffix = f", {warnings} unverified item(s)" if warnings else ""
        code = "unproven"
        verdict = f"VERDICT: UNPROVEN — schema layer skipped{suffix}"
    elif warnings:
        code, verdict = "unverified", f"VERDICT: PASTES, BUT {warnings} UNVERIFIED ITEM(S)"
    else:
        code, verdict = "safe", "VERDICT: SAFE TO PASTE"

    return {
        "path": path.as_posix(),
        "findings": [f.as_dict() for f in findings],
        "errors": errors,
        "warnings": warnings,
        "verdict": verdict,
        "verdict_code": code,
        "degraded": degraded,
    }


LAYER_TITLES = {
    "L0": "L0  YAML parse",
    "L1": "L1  Schema (pa.yaml v3.0) -- blocks the paste, like Studio PA1001",
    "L2": "L2  Catalog -- unverified control/property, like Studio PA2108",
    "L3": "L3  Conventions (SKILL.md rules)",
}


def render(report, quiet=False):
    out = []
    if not quiet:
        out.append("=" * 72)
        out.append(report["path"])
        out.append("=" * 72)
        if report["degraded"]:
            out.append(f"  NOTE: {report['degraded']}")
            out.append("")
        for layer in ("L0", "L1", "L2", "L3"):
            group = [f for f in report["findings"] if f["layer"] == layer]
            if not group:
                continue
            out.append(LAYER_TITLES[layer])
            out.append("-" * 72)
            for finding in group:
                where = []
                if finding["line"] is not None:
                    where.append(f"line {finding['line']}")
                if finding["column"] is not None:
                    where.append(f"col {finding['column']}")
                if finding["path"]:
                    where.append(finding["path"])
                out.append(f"  [{finding['severity'].upper()}] {finding['check']}")
                out.append(f"    {finding['message']}")
                if where:
                    out.append(f"    at: {' | '.join(where)}")
                if finding["detail"]:
                    for detail_line in finding["detail"].splitlines():
                        out.append(f"    {detail_line}")
                if finding["snippet"]:
                    out.append("    isolated paste-test snippet:")
                    for snippet_line in finding["snippet"].rstrip("\n").splitlines():
                        out.append(f"      | {snippet_line}")
                out.append("")
        if not report["findings"]:
            out.append("  No findings.")
            out.append("")
    out.append(report["verdict"])
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="pa_lint.py",
        description="Verify a Power Apps Canvas .pa.yaml offline, before it reaches "
                    "Power Apps Studio.",
    )
    parser.add_argument("files", nargs="+", type=Path, help=".pa.yaml file(s) to check")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG,
                        help="path to controls.yaml (default: the bundled catalog)")
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES,
                        help="path to control-ids-candidate.yaml, used only to word "
                             "the 'unknown control' warning better (default: bundled)")
    parser.add_argument("--json", action="store_true",
                        help="emit findings as JSON for machine consumption")
    parser.add_argument("--strict", action="store_true",
                        help="exit 2 when there are warnings but no errors")
    parser.add_argument("--quiet", action="store_true",
                        help="print only the verdict line(s)")
    args = parser.parse_args(argv)

    if not args.json:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass

    try:
        catalog = load_catalog(args.catalog)
    except (OSError, yaml.YAMLError) as exc:
        print(f"ERROR: cannot read catalog {args.catalog}: {exc}", file=sys.stderr)
        return 2

    candidates = load_candidates(args.candidates)

    schema = None
    if HAVE_JSONSCHEMA:
        try:
            schema = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8-sig"))
        except (OSError, yaml.YAMLError) as exc:
            print(f"ERROR: cannot read schema {SCHEMA_PATH}: {exc}", file=sys.stderr)
            return 2

    reports = []
    for path in args.files:
        if not path.is_file():
            print(f"ERROR: no such file: {path}", file=sys.stderr)
            return 2
        reports.append(lint_file(path, catalog, schema, candidates))

    total_errors = sum(r["errors"] for r in reports)
    total_warnings = sum(r["warnings"] for r in reports)
    any_degraded = any(r["degraded"] for r in reports)

    if total_errors:
        exit_code = 1
    elif (total_warnings or any_degraded) and args.strict:
        # --strict asks for proof. An unproven file cannot supply it.
        exit_code = 2
    else:
        exit_code = 0

    if args.json:
        print(json.dumps({
            "version": 1,
            "catalog": args.catalog.as_posix(),
            "candidate_ids": args.candidates.as_posix(),
            "studio_version_tested": catalog.studio_version,
            "schema_checked": schema is not None,
            "files": reports,
            "summary": {
                "files": len(reports),
                "errors": total_errors,
                "warnings": total_warnings,
                "exit_code": exit_code,
            },
        }, indent=2))
        return exit_code

    for report in reports:
        print(render(report, quiet=args.quiet))
    if len(reports) > 1 and not args.quiet:
        print()
        print(f"SUMMARY: {len(reports)} files, {total_errors} error(s), "
              f"{total_warnings} warning(s)")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
