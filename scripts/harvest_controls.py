#!/usr/bin/env python3
"""Harvest control evidence from real Power Apps Studio exports.

Phase 1 grew `controls.yaml` by hand, one paste test at a time. This grows it from
Studio's own output instead: the `.pa.yaml` files Studio writes under `src\\` when an app
is downloaded with `pac canvas download` or unpacked from an `.msapp`. Those files are
the strongest evidence available that a control type and a property name are real,
because Studio itself wrote them.

    python scripts/harvest_controls.py SRC [SRC...] [--out FILE] [--merge] [--report]

SRC is a `.pa.yaml` file, a folder containing them, or an `.msapp` (unzipped in memory).

What each mode does:

    (no flag)   print a `controls.yaml` fragment on stdout
    --out FILE  write that fragment to FILE (works alongside the other flags)
    --report    print a coverage diff: export vs catalog, both directions
    --merge     fold the fragment into the catalog in place

THE ABSENCE CAVEAT -- the single most important thing about this tool:

    Studio's export only writes properties whose value differs from the default.
    A property missing from an export is NOT evidence that the control lacks it.

So this tool only ever makes positive claims. It never writes to
`properties_unverified`, never emits a "does not support" list, and never removes
anything from the catalog. The one place absence is surfaced at all is the `--report`
"never exercised" section, which is labelled as untested, not unsupported.

Exit codes:  0 clean  |  1 usage / IO / parse failure  |  2 merge found conflicts

Requires PyYAML.
"""

from __future__ import annotations

import argparse
import datetime as _datetime
import io
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: PyYAML is not installed. Run: pip install pyyaml", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path(__file__).resolve().parent.parent
SKILL_REFS = ROOT / "skills" / "power-app-yaml" / "references"
DEFAULT_CATALOG = SKILL_REFS / "controls.yaml"

# Folder walks pick these up. Studio writes `.pa.yaml`; the bundled examples under
# assets/examples/ are plain `.yaml`, and hand-kept exports often are too.
SOURCE_SUFFIXES = (".pa.yaml", ".yaml", ".yml")

# Sections of a source file that can contain control instances.
CONTROL_SECTIONS = ("Screens", "ComponentDefinitions")

# `Control: CanvasComponent` / `CodeComponent` mark a third-party instance, not a
# first-party control-library type. They are counted but never written to the catalog.
NON_LIBRARY_TYPES = frozenset({"CanvasComponent", "CodeComponent"})

# Inside an .msapp the sources live under `src/`. Studio uses a backslash path on
# Windows; zipfile normalises to forward slashes, but be forgiving anyway.
MSAPP_SRC_RE = re.compile(r"(?:^|/)src/.*\.pa\.yaml$", re.IGNORECASE)

CAVEAT = (
    "Studio's export only writes properties whose value differs from the default.\n"
    "A property missing from an export is NOT evidence that the control lacks it.\n"
    "Nothing below may be read as a negative result."
)

WRAP_AT = 92


# ------------------------------------------------------------------- source collection


class SourceError(Exception):
    """A source could not be read at all. Distinct from 'read, but had no controls'."""


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _msapp_documents(path: Path):
    """Yield (label, text) for every src/**/*.pa.yaml inside an .msapp."""
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise SourceError(f"{path}: not a readable .msapp ({exc})") from exc
    with archive:
        names = [n for n in archive.namelist() if MSAPP_SRC_RE.search(n)]
        if not names:
            raise SourceError(
                f"{path}: no src/**/*.pa.yaml entries. Either this is not a canvas "
                ".msapp, or it predates the v3.0 source format."
            )
        for name in sorted(names):
            with archive.open(name) as handle:
                raw = io.TextIOWrapper(handle, encoding="utf-8-sig").read()
            yield f"{path.as_posix()}!{name}", raw


def collect_sources(paths):
    """Resolve CLI arguments into an ordered list of (label, text) documents."""
    documents, problems = [], []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            problems.append(f"{path}: no such file or directory")
            continue
        if path.is_dir():
            found = sorted(
                p for p in path.rglob("*")
                if p.is_file() and p.name.lower().endswith(SOURCE_SUFFIXES + (".msapp",))
            )
            if not found:
                problems.append(f"{path}: folder contains no .pa.yaml/.yaml/.msapp files")
            for child in found:
                try:
                    documents.extend(_documents_for_file(child))
                except SourceError as exc:
                    problems.append(str(exc))
            continue
        try:
            documents.extend(_documents_for_file(path))
        except SourceError as exc:
            problems.append(str(exc))
    return documents, problems


def _documents_for_file(path: Path):
    if path.name.lower().endswith(".msapp"):
        return list(_msapp_documents(path))
    try:
        return [(path.as_posix(), _read_text(path))]
    except OSError as exc:
        raise SourceError(f"{path}: cannot read ({exc})") from exc


# ----------------------------------------------------------------------- observations


class TypeObservation:
    """Everything one control type id was seen doing across all sources."""

    __slots__ = ("ctype", "count", "variants", "with_children", "properties", "files")

    def __init__(self, ctype: str):
        self.ctype = ctype
        self.count = 0
        self.variants = Counter()      # Variant string or None, per instance
        self.with_children = 0
        self.properties = Counter()    # property name -> instances that set it
        self.files = []                # source labels, insertion-ordered, deduplicated

    @property
    def base(self) -> str:
        return self.ctype.split("@", 1)[0]

    @property
    def version(self):
        return self.ctype.split("@", 1)[1] if "@" in self.ctype else None

    @property
    def short_name(self) -> str:
        """`Classic/Button@2.2.0` -> `Button`, matching the catalog's `name` field."""
        return self.base.rsplit("/", 1)[-1]

    @property
    def sole_variant(self):
        """The Variant every instance agreed on, or None if absent/inconsistent."""
        seen = [v for v in self.variants if v is not None]
        if len(seen) == 1 and self.variants[seen[0]] == self.count:
            return seen[0]
        return None

    @property
    def variant_is_mixed(self) -> bool:
        return len([v for v in self.variants if v is not None]) > 1 or (
            any(v is not None for v in self.variants)
            and self.variants.get(None, 0) > 0
        )

    def note_file(self, label: str) -> None:
        if label not in self.files:
            self.files.append(label)


class Harvest:
    def __init__(self):
        self.types: dict[str, TypeObservation] = {}
        self.instances = 0
        self.documents = 0
        self.skipped: list[str] = []

    def observe(self, ctype, variant, has_children, property_names, label):
        obs = self.types.get(ctype)
        if obs is None:
            obs = self.types[ctype] = TypeObservation(ctype)
        obs.count += 1
        obs.variants[variant] += 1
        if has_children:
            obs.with_children += 1
        for name in property_names:
            obs.properties[name] += 1
        obs.note_file(label)
        self.instances += 1

    def library_types(self):
        """Catalogable observations, ordered by name, excluding 3P instance markers."""
        return [obs for _t, obs in sorted(self.types.items())
                if obs.base not in NON_LIBRARY_TYPES]


def _iter_children(children, label, harvest: Harvest):
    """Walk a `Children:` sequence, recursing into nested `Children:` keys."""
    if not isinstance(children, list):
        return
    for item in children:
        if not isinstance(item, dict):
            continue
        # A control instance is a single-key mapping: `- <Name>: {Control: ...}`.
        for _name, body in item.items():
            if not isinstance(body, dict):
                continue
            ctype = body.get("Control")
            props = body.get("Properties")
            nested = body.get("Children")
            if isinstance(ctype, str) and ctype.strip():
                names = list(props) if isinstance(props, dict) else []
                harvest.observe(
                    ctype.strip(),
                    body.get("Variant") if isinstance(body.get("Variant"), str) else None,
                    isinstance(nested, list) and bool(nested),
                    names,
                    label,
                )
            _iter_children(nested, label, harvest)


def harvest_documents(documents) -> Harvest:
    harvest = Harvest()
    for label, text in documents:
        try:
            doc = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            harvest.skipped.append(f"{label}: not valid YAML ({exc.__class__.__name__})")
            continue
        if not isinstance(doc, dict):
            harvest.skipped.append(f"{label}: top level is not a mapping")
            continue
        if not any(section in doc for section in CONTROL_SECTIONS):
            why = ("App-level file (App:), which holds no control instances"
                   if "App" in doc
                   else "no Screens:/ComponentDefinitions: key -- not a control source")
            harvest.skipped.append(f"{label}: {why}")
            continue
        harvest.documents += 1
        for section in CONTROL_SECTIONS:
            node = doc.get(section)
            if not isinstance(node, dict):
                continue
            for _entity_name, body in node.items():
                if isinstance(body, dict):
                    _iter_children(body.get("Children"), label, harvest)
    return harvest


# ------------------------------------------------------------------------- the catalog


class CatalogView:
    """Read-only view of controls.yaml, mirroring how pa_lint.py reads it."""

    def __init__(self, data: dict):
        self.data = data or {}
        self.universal = set(self.data.get("universal_properties") or [])
        self.entries = [e for e in (self.data.get("controls") or []) if isinstance(e, dict)]
        self.by_type = {e.get("type"): e for e in self.entries}
        self.by_base = {}
        for entry in self.entries:
            self.by_base.setdefault(str(entry.get("type", "")).split("@", 1)[0], []).append(entry)

    def accepted(self, entry) -> set:
        return (set(entry.get("properties_confirmed") or [])
                | set(entry.get("properties_example_file") or [])
                | self.universal)

    @staticmethod
    def flagged_unverified(entry) -> set:
        return set(entry.get("properties_unverified") or [])


def load_catalog(path: Path) -> CatalogView:
    return CatalogView(yaml.safe_load(_read_text(path)) or {})


# --------------------------------------------------------------------- fragment output


PLAIN_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def _flow_item(name) -> str:
    """Property names come from someone else's YAML; quote anything unusual."""
    text = str(name)
    if PLAIN_NAME_RE.match(text):
        return text
    return "'" + text.replace("'", "''") + "'"


def _wrap_flow_list(key: str, items, indent: int):
    """Render `key: [a, b, c]`, wrapping like the hand-written catalog entries."""
    items = [_flow_item(i) for i in items]
    pad = " " * indent
    inline = f"{pad}{key}: [{', '.join(items)}]"
    if not items:
        return [f"{pad}{key}: []"]
    if len(inline) <= WRAP_AT:
        return [inline]
    lines = [f"{pad}{key}:"]
    body, cont = " " * (indent + 2) + "[", " " * (indent + 3)
    current = body
    for index, item in enumerate(items):
        piece = item + ("," if index < len(items) - 1 else "]")
        candidate = current + (" " if current.endswith(",") else "") + piece
        if len(candidate) > WRAP_AT and current not in (body,):
            lines.append(current)
            current = cont + piece
        else:
            current = current + piece if current is body else candidate
    lines.append(current)
    return lines


def _quote(text: str) -> str:
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _source_string(obs: TypeObservation, date: str, max_files: int = 3) -> str:
    names = []
    for label in obs.files:
        name = Path(label.split("!", 1)[0]).name if "!" in label else Path(label).name
        if name not in names:
            names.append(name)
    shown = names[:max_files]
    if len(names) > max_files:
        shown.append(f"+{len(names) - max_files} more")
    return f"{', '.join(shown)} (harvested {date})"


def build_fragment(harvest: Harvest, universal: set, date: str, source_labels) -> str:
    """A controls.yaml fragment. Positive claims only -- see the absence caveat."""
    out = [
        "# controls.yaml fragment -- GENERATED by scripts/harvest_controls.py.",
        "# Review every line before merging; this tool reports, it does not decide.",
        "#",
        "# ABSENCE CAVEAT",
    ]
    out += [f"#   {line}" for line in CAVEAT.splitlines()]
    out += [
        "#",
        "#   Consequently `properties_unverified` is always empty here and",
        "#   `accepts_children: false` means 'no Children seen', not 'cannot have any'.",
        "#   Universal properties "
        f"({', '.join(sorted(universal)) or 'none declared'}) are omitted from each",
        "#   entry, exactly as the hand-written catalog omits them.",
        "",
        "schema_version: 1",
        f"harvested: {_quote(date)}",
        "evidence: studio-export",
        "sources:",
    ]
    out += [f"  - {label}" for label in source_labels]
    out += ["", "controls:"]

    catalogable = harvest.library_types()
    if not catalogable:
        out.append("  []  # no first-party control instances found")
        return "\n".join(out) + "\n"

    for obs in catalogable:
        variant = obs.sole_variant
        props = sorted(set(obs.properties) - universal)
        out.append("")
        out.append(f"  # {obs.count} instance(s) in {len(obs.files)} file(s)"
                   + (f"; Variant mixed across instances: "
                      f"{', '.join(str(v) for v in sorted(obs.variants, key=str))}"
                      if obs.variant_is_mixed else ""))
        out.append(f"  - name: {obs.short_name}")
        out.append(f"    type: {obs.ctype}")
        out.append("    evidence: studio-export")
        out.append(f"    source: {_quote(_source_string(obs, date))}")
        if obs.with_children:
            out.append(f"    accepts_children: true   # Children seen on "
                       f"{obs.with_children}/{obs.count} instance(s)")
        else:
            out.append("    accepts_children: false  # no Children seen -- "
                       "absence is not evidence")
        out.append(f"    variant: {variant if variant else 'null'}")
        out += _wrap_flow_list("properties_confirmed", props, 4)
        out.append("    properties_example_file: []")
        out.append("    properties_unverified: []  # never written from an export")
        out.append("    notes: >-")
        out.append("      Harvested from a Studio export. The property list is what this "
                   "export happened")
        out.append("      to set; it is not a complete list of what the control accepts.")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------------- the report


def _bullets(pairs, empty="(none)"):
    if not pairs:
        return [f"    {empty}"]
    return [f"    {left:<28} {right}" for left, right in pairs]


def build_report(harvest: Harvest, catalog: CatalogView, source_labels) -> str:
    out = [
        "=" * WRAP_AT,
        "COVERAGE REPORT -- Studio export vs controls.yaml",
        "=" * WRAP_AT,
        f"  sources     {len(source_labels)} path(s), {harvest.documents} document(s) parsed",
        f"  instances   {harvest.instances} control instance(s)",
        f"  types       {len(harvest.library_types())} distinct first-party control type(s)",
        "",
        "-" * WRAP_AT,
        "ABSENCE CAVEAT -- read this before acting on section 2",
        "-" * WRAP_AT,
    ]
    out += [f"  {line}" for line in CAVEAT.splitlines()]
    out += [
        "  Section 2 below therefore means UNTESTED BY THIS EXPORT. It never means",
        "  unsupported, and it is never a reason to demote a catalog entry.",
        "",
    ]

    if harvest.skipped:
        out.append("-" * WRAP_AT)
        out.append("Skipped sources")
        out.append("-" * WRAP_AT)
        out += [f"    {line}" for line in harvest.skipped]
        out.append("")

    # ---- 1. in the export, missing from the catalog
    out.append("-" * WRAP_AT)
    out.append("1. In the export, MISSING from the catalog  (things to add)")
    out.append("-" * WRAP_AT)

    new_types, new_props = [], []
    for obs in harvest.library_types():
        entry = catalog.by_type.get(obs.ctype)
        if entry is None:
            siblings = catalog.by_base.get(obs.base) or []
            hint = (f"catalog has {', '.join(str(e.get('type')) for e in siblings)}"
                    if siblings else "no catalog entry at any version")
            new_types.append((obs.ctype, f"{obs.count} instance(s); {hint}"))
            continue
        # Properties the catalog explicitly flags unverified are listed separately;
        # they are not "missing", they are a human decision this tool must not undo.
        extra = sorted(set(obs.properties)
                       - catalog.accepted(entry)
                       - catalog.flagged_unverified(entry))
        if extra:
            new_props.append((obs.ctype, ", ".join(extra)))

    out.append("  control types:")
    out += _bullets(new_types)
    out.append("  properties on already-catalogued controls:")
    out += _bullets(new_props)
    out.append("")

    held = list(_held_back(harvest, catalog))
    if held:
        out.append("-" * WRAP_AT)
        out.append("1b. Observed, but HELD BACK  (the catalog flags these unverified)")
        out.append("-" * WRAP_AT)
        out += _bullets([(ctype, ", ".join(names)) for ctype, names in held])
        out.append("  The export exercising a property is positive evidence, but the")
        out.append("  catalog says a human deliberately marked it unverified. Settle it")
        out.append("  with a Studio paste test; --merge will not promote these.")
        out.append("")

    # ---- 2. in the catalog, never exercised by the export
    out.append("-" * WRAP_AT)
    out.append("2. In the catalog, NEVER EXERCISED by this export  (untested, "
               "NOT unsupported)")
    out.append("-" * WRAP_AT)

    seen_types = {obs.ctype for obs in harvest.library_types()}
    cold_types, cold_props = [], []
    for entry in catalog.entries:
        ctype = str(entry.get("type"))
        if ctype not in seen_types:
            cold_types.append((ctype, f"evidence: {entry.get('evidence')}"))
            continue
        obs = harvest.types[ctype]
        claimed = (set(entry.get("properties_confirmed") or [])
                   | set(entry.get("properties_example_file") or []))
        unused = sorted(claimed - set(obs.properties))
        if unused:
            cold_props.append((ctype, ", ".join(unused)))

    out.append("  control types:")
    out += _bullets(cold_types)
    out.append("  properties:")
    out += _bullets(cold_props)
    out.append("")

    # ---- 3. disagreements
    out.append("-" * WRAP_AT)
    out.append("3. Disagreements between the export and the catalog  (for a human)")
    out.append("-" * WRAP_AT)
    rows = [(kind, text) for kind, text in _disagreements(harvest, catalog)]
    out += _bullets(rows, empty="(none)")
    out.append("")

    # ---- 4. non-library instances, if any
    third_party = [obs for obs in harvest.types.values()
                   if obs.base in NON_LIBRARY_TYPES]
    if third_party:
        out.append("-" * WRAP_AT)
        out.append("4. Third-party instances seen (not control-library types, not "
                   "catalogued)")
        out.append("-" * WRAP_AT)
        out += _bullets([(obs.ctype, f"{obs.count} instance(s)") for obs in third_party])
        out.append("")

    return "\n".join(out)


def _disagreements(harvest: Harvest, catalog: CatalogView):
    """Yield (kind, description). These are reported, never auto-resolved."""
    for obs in harvest.library_types():
        entry = catalog.by_type.get(obs.ctype)
        if entry is None:
            siblings = catalog.by_base.get(obs.base) or []
            if siblings:
                known = ", ".join(str(e.get("type")) for e in siblings)
                yield ("conflict: version", f"export has {obs.ctype}, catalog has {known}")
            if obs.version is None:
                yield ("conflict: no version",
                       f"{obs.ctype} carries no @version -- cannot be pinned")
            continue

        catalog_variant = entry.get("variant")
        if obs.variant_is_mixed:
            seen = ", ".join(str(v) for v in sorted(obs.variants, key=str))
            yield ("conflict: variant",
                   f"{obs.ctype} uses more than one Variant in the export ({seen})")
        elif obs.sole_variant != catalog_variant:
            yield ("conflict: variant",
                   f"{obs.ctype} export Variant {obs.sole_variant!r} != catalog "
                   f"{catalog_variant!r}")

        if obs.with_children and entry.get("accepts_children") is False:
            yield ("conflict: children",
                   f"{obs.ctype} has Children in the export but accepts_children: "
                   "false in the catalog")


def _held_back(harvest: Harvest, catalog: CatalogView):
    """Observed properties the catalog explicitly flags unverified.

    Positive evidence that nonetheless contradicts a deliberate human note, so it is
    never auto-promoted. Distinct from a conflict: the merge can still proceed.
    """
    for obs in harvest.library_types():
        entry = catalog.by_type.get(obs.ctype)
        if entry is None:
            continue
        clash = sorted(set(obs.properties) & catalog.flagged_unverified(entry))
        if clash:
            yield (obs.ctype, clash)


# -------------------------------------------------------------------------- the merge
#
# The catalog is edited as TEXT, not loaded-and-dumped. Round-tripping it through
# PyYAML would silently delete every comment in the file -- including the absence
# caveat this phase exists to protect. So the merge makes surgical line edits and, when
# there is nothing to change, does not write the file at all.


ENTRY_START_RE = re.compile(r"^  - name:\s*(\S.*?)\s*$")
TOP_KEY_RE = re.compile(r"^[A-Za-z_][\w-]*:")


def _controls_block(lines):
    """(first_line_index, end_index_exclusive) of the `controls:` block body."""
    start = None
    for index, line in enumerate(lines):
        if line.rstrip() == "controls:":
            start = index + 1
            break
    if start is None:
        raise SourceError("catalog has no top-level `controls:` key")
    end = len(lines)
    for index in range(start, len(lines)):
        stripped = lines[index]
        if stripped.strip() and not stripped.startswith((" ", "\t", "#")) \
                and TOP_KEY_RE.match(stripped):
            end = index
            break
    return start, end


def _entry_spans(lines):
    """[(type_string, start, end_exclusive)] for each entry in `controls:`."""
    block_start, block_end = _controls_block(lines)
    starts = [i for i in range(block_start, block_end) if ENTRY_START_RE.match(lines[i])]
    spans = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else block_end
        ctype = None
        for index in range(start, end):
            match = re.match(r"^    type:\s*(\S+)\s*$", lines[index])
            if match:
                ctype = match.group(1)
                break
        spans.append((ctype, start, end))
    return spans, block_start, block_end


def _flow_value_span(lines, start, end, key):
    """(key_index, value_end_inclusive, parsed_list) for a flow-sequence key."""
    pattern = re.compile(rf"^    {re.escape(key)}:\s*(.*)$")
    for index in range(start, end):
        match = pattern.match(lines[index])
        if not match:
            continue
        text = match.group(1)
        last = index
        depth = text.count("[") - text.count("]")
        while (depth > 0 or not text.strip()) and last + 1 < end:
            last += 1
            text += "\n" + lines[last]
            depth = text.count("[") - text.count("]")
            if depth <= 0 and text.strip():
                break
        try:
            parsed = yaml.safe_load(text)
        except yaml.YAMLError:
            return index, last, None
        if parsed is None:
            parsed = []
        return index, last, parsed if isinstance(parsed, list) else None
    return None, None, None


def _insertion_point(lines, block_end):
    """Where a new entry goes: after the last entry, before the next key's preamble.

    `controls:` is followed by a column-0 comment introducing `unattempted_controls:`.
    That comment belongs to the next key, so back up over it (and over blank lines)
    rather than appending underneath it.
    """
    index = block_end
    while index - 1 >= 0 and (not lines[index - 1].strip()
                              or lines[index - 1].startswith("#")):
        index -= 1
    return index


def merge_into_catalog(catalog_path: Path, harvest: Harvest, catalog: CatalogView,
                       date: str, dry_run: bool):
    """Fold the harvest into controls.yaml. Returns (summary_lines, conflicts, changed)."""
    text = _read_text(catalog_path)
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.replace("\r\n", "\n").split("\n")
    trailing_newline = lines and lines[-1] == ""
    if trailing_newline:
        lines.pop()

    spans, _block_start, block_end = _entry_spans(lines)
    span_by_type = {ctype: (start, end) for ctype, start, end in spans if ctype}

    conflicts = [f"{kind}: {detail}" for kind, detail in _disagreements(harvest, catalog)]
    held = list(_held_back(harvest, catalog))

    summary, edits, additions = [], [], []
    universal = catalog.universal
    unattempted = set(catalog.data.get("unattempted_controls") or [])

    for obs in harvest.library_types():
        entry = catalog.by_type.get(obs.ctype)

        if entry is None:
            if catalog.by_base.get(obs.base):
                # Same control, different version. Reported above; never auto-resolved,
                # because picking a version is a judgement about which Studio build the
                # catalog describes.
                summary.append(f"  ! held     {obs.ctype:<28} version conflict -- not added")
                continue
            if obs.version is None:
                summary.append(f"  ! held     {obs.ctype:<28} no @version -- not added")
                continue
            additions.append(obs)
            if obs.base in unattempted:
                summary.append(
                    f"  ! todo     {obs.ctype:<28} now catalogued -- remove "
                    f"{obs.base!r} from unattempted_controls by hand")
            summary.append(f"  + control  {obs.ctype:<28} "
                           f"{obs.count} instance(s), "
                           f"{len(set(obs.properties) - universal)} property name(s)")
            continue

        start, end = span_by_type.get(obs.ctype, (None, None))
        if start is None:
            conflicts.append(f"internal: cannot locate {obs.ctype} in the catalog text")
            continue

        blocked = catalog.flagged_unverified(entry)
        additions_here = sorted(
            set(obs.properties) - catalog.accepted(entry) - blocked - universal
        )
        if not additions_here:
            continue

        key_index, value_end, existing = _flow_value_span(
            lines, start, end, "properties_confirmed")
        if key_index is None or existing is None:
            conflicts.append(
                f"{obs.ctype}: properties_confirmed is missing or not a flow list -- "
                "merge it by hand")
            continue

        # Keep the hand-written order -- those lists are grouped on purpose --
        # and append the harvested names after them.
        merged = list(existing) + [n for n in additions_here if n not in existing]
        replacement = [
            f"    # harvested {date}: +{', +'.join(additions_here)} "
            f"(scripts/harvest_controls.py)"
        ] + _wrap_flow_list("properties_confirmed", merged, 4)
        edits.append((key_index, value_end + 1, replacement))
        summary.append(f"  + props    {obs.ctype:<28} "
                       f"{', '.join(additions_here)}")

    for ctype, names in held:
        summary.append(f"  ! held     {ctype:<28} "
                       f"{', '.join(names)} -- catalog flags these unverified")

    if additions:
        insert_at = _insertion_point(lines, block_end)
        new_lines = []
        for obs in additions:
            new_lines.append("")
            new_lines += _new_entry_lines(obs, universal, date)
        edits.append((insert_at, insert_at, new_lines))

    changed = bool(edits)
    if changed:
        for start, end, replacement in sorted(edits, key=lambda e: e[0], reverse=True):
            lines[start:end] = replacement
        for index, line in enumerate(lines):
            if line.startswith("catalog_updated:"):
                lines[index] = f'catalog_updated: "{date}"'
                break
        if dry_run:
            summary.append("  = --dry-run: nothing written")
        else:
            rendered = newline.join(lines) + (newline if trailing_newline else "")
            catalog_path.write_text(rendered, encoding="utf-8", newline="")
            summary.append(f"  = wrote    {catalog_path.as_posix()}")
    else:
        summary.append("  = no changes -- catalog already covers this export")

    return summary, conflicts, changed


def _new_entry_lines(obs: TypeObservation, universal: set, date: str):
    props = sorted(set(obs.properties) - universal)
    lines = [
        f"  - name: {obs.short_name}",
        f"    type: {obs.ctype}",
        "    evidence: studio-export",
        f"    source: {_quote(_source_string(obs, date))}",
    ]
    if obs.with_children:
        lines.append("    accepts_children: true")
    else:
        lines.append("    accepts_children: false  # no Children seen -- "
                     "absence is not evidence")
    lines.append(f"    variant: {obs.sole_variant if obs.sole_variant else 'null'}")
    lines += _wrap_flow_list("properties_confirmed", props, 4)
    lines.append("    properties_example_file: []")
    lines.append("    properties_unverified: []")
    lines.append("    notes: >-")
    lines.append("      Harvested from a Studio export on "
                 f"{date}. The property list is what that")
    lines.append("      export happened to set, not a complete list of what the "
                 "control accepts.")
    return lines


# ------------------------------------------------------------------------------- main


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="harvest_controls.py",
        description="Harvest control-type evidence from real Power Apps Studio "
                    "exports (.pa.yaml / .msapp) and fold it into controls.yaml.",
        epilog="ABSENCE CAVEAT: Studio exports only record properties that differ from "
               "their default, so a property missing from an export is not evidence "
               "that the control lacks it. This tool only ever makes positive claims.",
    )
    parser.add_argument("sources", nargs="+",
                        help=".pa.yaml file, folder of them, or .msapp")
    parser.add_argument("--out", type=Path,
                        help="write the controls.yaml fragment to this file")
    parser.add_argument("--merge", action="store_true",
                        help="fold the fragment into the catalog in place")
    parser.add_argument("--report", action="store_true",
                        help="print a coverage diff against the catalog")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG,
                        help="path to controls.yaml (default: the bundled catalog)")
    parser.add_argument("--dry-run", action="store_true",
                        help="with --merge, report what would change and write nothing")
    parser.add_argument("--date", default=None,
                        help="harvest date stamp (default: today, YYYY-MM-DD)")
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover
        pass

    date = args.date or _datetime.date.today().isoformat()

    documents, problems = collect_sources(args.sources)
    for problem in problems:
        print(f"WARNING: {problem}", file=sys.stderr)
    if not documents:
        print("ERROR: no readable source documents.", file=sys.stderr)
        return 1

    harvest = harvest_documents(documents)
    if harvest.documents == 0:
        for line in harvest.skipped:
            print(f"WARNING: {line}", file=sys.stderr)
        print("ERROR: no source document contained Screens: or ComponentDefinitions:.",
              file=sys.stderr)
        return 1

    try:
        catalog = load_catalog(args.catalog)
    except (OSError, yaml.YAMLError) as exc:
        print(f"ERROR: cannot read catalog {args.catalog}: {exc}", file=sys.stderr)
        return 1

    fragment = build_fragment(harvest, catalog.universal, date, list(args.sources))

    if args.out:
        try:
            args.out.write_text(fragment, encoding="utf-8")
        except OSError as exc:
            print(f"ERROR: cannot write {args.out}: {exc}", file=sys.stderr)
            return 1
        print(f"wrote fragment to {args.out.as_posix()}", file=sys.stderr)

    exit_code = 0

    if args.report:
        print(build_report(harvest, catalog, list(args.sources)))

    if args.merge:
        try:
            summary, conflicts, _changed = merge_into_catalog(
                args.catalog, harvest, catalog, date, args.dry_run)
        except (SourceError, OSError) as exc:
            print(f"ERROR: merge failed: {exc}", file=sys.stderr)
            return 1
        print("=" * WRAP_AT)
        print(f"MERGE -- {args.catalog.as_posix()}")
        print("=" * WRAP_AT)
        for line in summary:
            print(line)
        print("")
        if conflicts:
            print(f"{len(conflicts)} conflict(s) -- left for a human, nothing "
                  "auto-resolved:")
            for line in conflicts:
                print(f"  ! {line}")
            exit_code = 2
        else:
            print("0 conflicts.")
        print("")
        print("Review before committing:  git diff -- "
              f"{args.catalog.as_posix()}")

    if not args.report and not args.merge and not args.out:
        sys.stdout.write(fragment)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
