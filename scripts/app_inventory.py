#!/usr/bin/env python3
"""One-page inventory of an app that already exists.

Extending a real app means knowing what is already in it: which screens exist (so
`Navigate()` points somewhere real), which names are taken (so Studio does not
silently rename the new screen to `_1`), which control versions the app itself
uses, and which theme variables `App.OnStart` already defines.

Pasting the export into a conversation to find that out costs thousands of tokens
and buries the five facts that matter. This tool answers those questions in about
a page.

    python scripts/app_inventory.py SRC [SRC...] [--json] [--names] [--max-bytes N]

SRC is a folder of `.pa.yaml` files (the `Src\\` folder of an unpacked app), a single
`.pa.yaml`, or an `.msapp` (unzipped in memory, `src/**/*.pa.yaml` only).

THE POINT IS THE BUDGET. The default text output is capped at 2048 bytes. When the
app is too big to describe fully in that space, the tool drops to a coarser level of
detail rather than overflowing, and says which level it used on the last line. It is
not a pretty-printer for the source -- if you need everything, `--json` and `--names`
are unbudgeted.

What it reports, and what it does NOT:

  * Screen names, in `EditorState.ScreensOrder` order when the export has one.
  * Per screen: the controls, and how deeply they nest. Never property values --
    those are the bulk of an export and almost never what you need.
  * `Set(...)` / `Collect(...)` / `ClearCollect(...)` targets in `App.OnStart`, with
    the value when the value is a literal and `~expr` when it is not. A guessed
    evaluation of a formula would be worse than no value at all.
  * `DataSources:` entries with their `Type:`.
  * `ComponentDefinitions:` names.
  * A collision list: every screen and control name already in use.

Exit codes:  0 ok  |  1 nothing could be read

Requires PyYAML.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import zipfile
from collections import Counter, OrderedDict
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: PyYAML is not installed. Run: pip install pyyaml", file=sys.stderr)
    raise SystemExit(1)

# Studio writes `.pa.yaml`; hand-kept exports and this repo's own examples are often
# plain `.yaml`.
SOURCE_SUFFIXES = (".pa.yaml", ".yaml", ".yml")

# Inside an .msapp the sources live under `src/`. Studio uses a backslash path on
# Windows; zipfile normalises to forward slashes, but be forgiving anyway.
MSAPP_SRC_RE = re.compile(r"(?:^|/)src/.*\.pa\.yaml$", re.IGNORECASE)

DEFAULT_MAX_BYTES = 2048

# A value that is a constant. Anything else is reported as `~expr`: this tool reads
# YAML, it does not evaluate Power Fx, and a half-evaluated formula would be a lie.
LITERAL_RE = re.compile(
    r"""^(?:
          "(?:[^"\\]|\\.)*"            # "text"
        | '(?:[^'\\]|\\.)*'            # 'text'
        | -?\d+(?:\.\d+)?              # 42, -1.5
        | true | false                 # booleans, either case (handled by re.I)
        | Blank\(\)
        | ColorValue\(\s*"[^"]*"\s*\)  # ColorValue("#005ab6")
        | RGBA\(\s*[\d.\s,]+\)         # RGBA(0, 127, 250, 1)
        | Color\.[A-Za-z]+             # Color.White
        )$""",
    re.VERBOSE | re.IGNORECASE,
)

SETTERS = ("Set", "Collect", "ClearCollect")

# Used only by the most compressed tier of the collision list, where exact names no
# longer fit. Two conventions show up in real apps: a Hungarian prefix (`lblTitle`,
# `btnGo`) and Studio's own auto-names (`Label3`, `Rectangle12`).
HUNGARIAN_RE = re.compile(r"^([a-z]{2,4})(?=[A-Z])")
TRAILING_DIGITS_RE = re.compile(r"[0-9_]+$")

# An app whose controls are mostly Studio auto-names has almost as many prefixes as
# names, so even the prefix list needs a ceiling.
STEM_CAP = 10


class SourceError(Exception):
    """A source could not be read at all."""


# ------------------------------------------------------------------- source collection


def _msapp_documents(path: Path):
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
                yield name, io.TextIOWrapper(handle, encoding="utf-8-sig").read()


def _documents_for_file(path: Path):
    if path.name.lower().endswith(".msapp"):
        return list(_msapp_documents(path))
    try:
        return [(path.as_posix(), path.read_text(encoding="utf-8-sig"))]
    except OSError as exc:
        raise SourceError(f"{path}: cannot read ({exc})") from exc


def collect_sources(paths):
    """Resolve CLI arguments into an ordered list of (label, text) documents."""
    documents, problems = [], []
    for raw in paths:
        path = Path(raw)
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


# -------------------------------------------------------------------------- App.OnStart


def _split_args(text: str):
    """Split a Power Fx argument list on top-level commas.

    Written by hand rather than with a regex because the commas that matter are the
    ones NOT inside nested calls, brackets or strings -- exactly what a regex cannot
    see. `Set(v, RGBA(0, 1, 2, 3))` has two arguments, not five.
    """
    args, depth, quote, start = [], 0, None, 0
    for index, char in enumerate(text):
        if quote:
            if char == quote and text[index - 1: index] != "\\":
                quote = None
            continue
        if char in "\"'":
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            args.append(text[start:index])
            start = index + 1
    args.append(text[start:])
    return [a.strip() for a in args]


def _call_body(text: str, open_paren: int):
    """Return (body, index-after-close) for the call whose '(' is at open_paren."""
    depth, quote = 0, None
    for index in range(open_paren, len(text)):
        char = text[index]
        if quote:
            if char == quote and text[index - 1: index] != "\\":
                quote = None
            continue
        if char in "\"'":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[open_paren + 1:index], index + 1
    return None, len(text)


def parse_onstart(formula: str):
    """[(kind, name, value)] for every Set/Collect/ClearCollect in an OnStart formula.

    Scans the whole formula, so a Set() nested inside If() or ForAll() is still found.
    `value` is the literal when the second argument is a constant, else None.
    """
    if not formula:
        return []
    found, seen = [], set()
    for match in re.finditer(r"\b(Set|ClearCollect|Collect)\s*\(", formula):
        kind = match.group(1)
        body, _ = _call_body(formula, match.end() - 1)
        if body is None:
            continue
        args = _split_args(body)
        name = args[0].strip()
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name) or (kind, name) in seen:
            continue
        seen.add((kind, name))
        rest = args[1].strip() if len(args) > 1 else ""
        value = rest if LITERAL_RE.match(rest) else None
        found.append((kind, name, value))
    # Longest match wins: `ClearCollect` also matches the `Collect` pattern, so the
    # same collection can arrive twice. Keep the first (ClearCollect is scanned first
    # only by accident of ordering, so dedupe explicitly on the name).
    deduped, names = [], set()
    for kind, name, value in found:
        if name in names:
            continue
        names.add(name)
        deduped.append((kind, name, value))
    return deduped


# ------------------------------------------------------------------------- the walk


def _walk(children, depth, out):
    """Append (name, type, variant, depth) for every control, depth first."""
    if not isinstance(children, list):
        return
    for item in children:
        if not isinstance(item, dict):
            continue
        for name, body in item.items():
            if not isinstance(body, dict):
                continue
            out.append((str(name), str(body.get("Control") or "?"),
                        body.get("Variant"), depth))
            _walk(body.get("Children"), depth + 1, out)


class Inventory:
    def __init__(self):
        self.screens = OrderedDict()      # screen name -> [(name, type, variant, depth)]
        self.screens_order = []
        self.onstart = []
        self.datasources = OrderedDict()  # name -> Type
        self.components = []
        self.files = 0
        self.duplicate_screens = []

    # -- building ---------------------------------------------------------------

    def add_document(self, document):
        if not isinstance(document, dict):
            return
        self.files += 1

        app = document.get("App")
        if isinstance(app, dict):
            props = app.get("Properties")
            if isinstance(props, dict):
                self.onstart.extend(parse_onstart(str(props.get("OnStart") or "")))

        screens = document.get("Screens")
        if isinstance(screens, dict):
            for name, node in screens.items():
                name = str(name)
                if name in self.screens:
                    self.duplicate_screens.append(name)
                    continue
                controls = []
                if isinstance(node, dict):
                    _walk(node.get("Children"), 1, controls)
                self.screens[name] = controls

        editor = document.get("EditorState")
        if isinstance(editor, dict):
            order = editor.get("ScreensOrder")
            if isinstance(order, list):
                self.screens_order.extend(str(s) for s in order)

        sources = document.get("DataSources")
        if isinstance(sources, dict):
            for name, node in sources.items():
                kind = node.get("Type") if isinstance(node, dict) else None
                self.datasources.setdefault(str(name), str(kind or "?"))

        components = document.get("ComponentDefinitions")
        if isinstance(components, dict):
            for name in components:
                if str(name) not in self.components:
                    self.components.append(str(name))

    # -- derived ----------------------------------------------------------------

    @property
    def ordered_screens(self):
        """Screen names in EditorState.ScreensOrder order, then any not listed there."""
        ordered = [s for s in self.screens_order if s in self.screens]
        ordered += [s for s in self.screens if s not in ordered]
        return ordered

    @property
    def has_order(self):
        return any(s in self.screens for s in self.screens_order)

    def type_counts(self):
        counts = Counter()
        for controls in self.screens.values():
            for _name, ctype, variant, _depth in controls:
                counts[(ctype, variant)] += 1
        return counts

    def control_total(self):
        return sum(len(c) for c in self.screens.values())

    def names_in_use(self):
        names = set(self.screens)
        for controls in self.screens.values():
            names |= {name for name, _t, _v, _d in controls}
        return sorted(names, key=str.lower)


def build(documents):
    inventory = Inventory()
    problems = []
    for label, text in documents:
        try:
            document = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            problems.append(f"{label}: will not parse as YAML ({exc.__class__.__name__})")
            continue
        inventory.add_document(document)
    return inventory, problems


# ------------------------------------------------------------------------ rendering


def short_type(ctype: str) -> str:
    """`Classic/Button@2.2.0` -> `Classic/Button`."""
    return ctype.split("@", 1)[0]


def base_type(ctype: str) -> str:
    """`Classic/Button@2.2.0` -> `Button`.

    Only for the per-screen count line, where the full ids already appear once in the
    TYPES section and repeating `Classic/` ten times buys nothing.
    """
    return short_type(ctype).rsplit("/", 1)[-1]


def tighten(value: str) -> str:
    """Drop the spaces inside a literal: `RGBA(24, 28, 35, 1)` -> `RGBA(24,28,35,1)`."""
    return re.sub(r",\s+", ",", value)


def wrap(items, width=88, indent="  ", cont=None):
    """Pack space-separated items into lines. Cheaper per byte than one item a line.

    `cont` is the indent for continuation lines. It defaults to two spaces rather than
    repeating `indent`, so a long `TYPES: ...` run does not pay for the label again on
    every line -- at a 2 KB budget that repetition is real money.
    """
    if cont is None:
        cont = "  "
    lines, current, filled = [], indent, False
    for item in items:
        if filled and len(current) + len(item) > width:
            lines.append(current.rstrip())
            current, filled = cont, False
        current += item + " "
        filled = True
    if filled:
        lines.append(current.rstrip())
    return lines


def stem(name: str) -> str:
    """The family a name belongs to: `lblTitle` -> `lbl`, `Rectangle12` -> `Rectangle`."""
    match = HUNGARIAN_RE.match(name)
    if match:
        return match.group(1)
    return TRAILING_DIGITS_RE.sub("", name)[:12] or name[:12]


def stem_counts(names):
    counts = Counter()
    for name in names:
        counts[stem(name) + "*"] += 1
    return counts


def _screen_block(inventory, name, tier):
    """The per-screen lines at a given detail tier. Tier 3 is richest, 0 is counts."""
    controls = inventory.screens[name]
    depth = max((d for _n, _t, _v, d in controls), default=0)
    head = f"  {name}  {len(controls)}c d{depth}"
    if not controls:
        return [head + "  (empty)"]

    if tier >= 3:
        lines = [head]
        for cname, ctype, variant, cdepth in controls:
            mark = "." * (cdepth - 1)
            suffix = f"[{variant}]" if variant else ""
            lines.append(f"    {mark}{cname} {short_type(ctype)}{suffix}")
        return lines

    if tier == 2:
        grouped = OrderedDict()
        for cname, ctype, _variant, _d in controls:
            grouped.setdefault(short_type(ctype), []).append(cname)
        lines = [head]
        for ctype, cnames in grouped.items():
            lines += wrap(cnames, indent=f"    {ctype}: ")
        return lines

    if tier == 1:
        return [head] + wrap([n for n, _t, _v, _d in controls], indent="    ")

    counts = Counter(base_type(t) for _n, t, _v, _d in controls)
    return wrap([f"{t}x{c}" for t, c in counts.most_common()],
                indent=head + "  ", cont="      ")


def _names_block(inventory, tier):
    names = inventory.names_in_use()
    if tier >= 1:
        return ["NAMES IN USE (a collision is silently renamed to _1 on paste):"] + wrap(names)
    counts = stem_counts(names)
    top = counts.most_common(STEM_CAP)
    rendered = [f"{prefix}x{n}" for prefix, n in top]
    if len(counts) > len(top):
        rendered.append(f"+{len(counts) - len(top)}more")
    return (
        ["NAME PREFIXES (a collision is silently renamed to _1 on paste):"]
        + wrap(rendered)
        + [f"  ({len(names)} names; --names lists them all)"]
    )


def _fixed_sections(inventory, label, problems):
    """The parts that are small enough to never need summarising."""
    total = inventory.control_total()
    types = inventory.type_counts()
    lines = [
        f"APP INVENTORY  {label}  ({inventory.files} source file(s))",
        f"{len(inventory.screens)} screens | {total} controls | {len(types)} types | "
        f"{len(inventory.datasources)} data sources | {len(inventory.components)} components",
    ]

    if types:
        rendered = []
        for (ctype, variant), count in types.most_common():
            rendered.append(f"{ctype}{f'[{variant}]' if variant else ''}x{count}")
        lines += wrap(rendered, indent="TYPES: ")

    if inventory.onstart:
        rendered = []
        for kind, name, value in inventory.onstart:
            if kind == "Set":
                rendered.append(f"{name}={tighten(value) if value is not None else '~expr'}")
            else:
                rendered.append(f"{name}={kind}(~)")
        lines += wrap(rendered, indent="ONSTART: ")
    else:
        lines.append("ONSTART: (no Set/Collect found)")

    if inventory.datasources:
        lines += wrap([f"{n}[{t}]" for n, t in inventory.datasources.items()],
                      indent="DATASOURCES: ")
    if inventory.components:
        lines += wrap(inventory.components, indent="COMPONENTS: ")
    for problem in problems:
        lines.append(f"! {problem}")
    for name in sorted(set(inventory.duplicate_screens)):
        lines.append(f"! screen {name!r} is defined in more than one file; first kept")
    return lines


# Richest first. Each rung is (screen detail tier, collision-list tier).
TIER_LADDER = [(3, 1), (2, 1), (1, 1), (0, 1), (0, 0)]

TIER_NAMES = {3: "every control", 2: "controls grouped by type", 1: "control names",
              0: "control counts"}


def render(inventory, label, problems, max_bytes=DEFAULT_MAX_BYTES):
    """Render the richest tier that fits the budget. Never overflows silently."""
    order_note = ("EditorState.ScreensOrder" if inventory.has_order
                  else "file order -- no EditorState.ScreensOrder in this export")
    best = None
    for screen_tier, names_tier in TIER_LADDER:
        lines = list(_fixed_sections(inventory, label, problems))
        lines.append(f"SCREENS ({order_note}):")
        for name in inventory.ordered_screens:
            lines += _screen_block(inventory, name, screen_tier)
        lines += _names_block(inventory, names_tier)
        note = f"[detail: {TIER_NAMES[screen_tier]}"
        if names_tier == 0:
            note += ", name prefixes only"
        note += f"; {max_bytes}B budget; full data: --json, --names]"
        lines.append(note)
        text = "\n".join(lines) + "\n"
        best = text
        if len(text.encode("utf-8")) <= max_bytes:
            return text
    # Even the coarsest tier overflowed -- that takes hundreds of screens. Say so
    # rather than printing something that claims to be a one-page summary.
    return best.rstrip("\n") + (
        f"\n[OVER BUDGET: {len(best.encode('utf-8'))}B > {max_bytes}B even at the "
        "coarsest detail. Raise --max-bytes or inventory fewer files.]\n"
    )


def render_names(inventory):
    return "\n".join(wrap(inventory.names_in_use(), indent="", cont="")) + "\n"


def as_json(inventory, label, problems):
    return {
        "version": 1,
        "source": label,
        "files": inventory.files,
        "screens_order_source": ("EditorState.ScreensOrder" if inventory.has_order
                                 else "file order"),
        "screens": [
            {
                "name": name,
                "control_count": len(inventory.screens[name]),
                "max_depth": max((d for _n, _t, _v, d in inventory.screens[name]),
                                 default=0),
                "controls": [
                    {"name": cname, "type": ctype, "variant": variant, "depth": depth}
                    for cname, ctype, variant, depth in inventory.screens[name]
                ],
            }
            for name in inventory.ordered_screens
        ],
        "types": [
            {"type": ctype, "variant": variant, "count": count}
            for (ctype, variant), count in inventory.type_counts().most_common()
        ],
        "onstart": [
            {"kind": kind, "name": name, "literal": value}
            for kind, name, value in inventory.onstart
        ],
        "data_sources": [{"name": n, "type": t} for n, t in inventory.datasources.items()],
        "components": list(inventory.components),
        "names_in_use": inventory.names_in_use(),
        "problems": problems,
    }


# ---------------------------------------------------------------------------- main


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="app_inventory.py",
        description="One-page inventory of an existing Power Apps canvas app, so a "
                    "new screen can be written against it without pasting the whole "
                    "export into the conversation.",
    )
    parser.add_argument("sources", nargs="+", metavar="SRC",
                        help="folder of .pa.yaml, a single .pa.yaml, or an .msapp")
    parser.add_argument("--json", action="store_true",
                        help="emit the full inventory as JSON (not budgeted)")
    parser.add_argument("--names", action="store_true",
                        help="emit only the collision list, complete (not budgeted)")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                        help=f"byte budget for the text summary (default {DEFAULT_MAX_BYTES})")
    args = parser.parse_args(argv)

    if not args.json:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass

    documents, problems = collect_sources(args.sources)
    if not documents:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        if not problems:
            print("ERROR: nothing to read", file=sys.stderr)
        return 1

    inventory, parse_problems = build(documents)
    problems = problems + parse_problems
    label = Path(args.sources[0]).name or args.sources[0]

    if args.json:
        print(json.dumps(as_json(inventory, label, problems), indent=2))
    elif args.names:
        sys.stdout.write(render_names(inventory))
    else:
        sys.stdout.write(render(inventory, label, problems, args.max_bytes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
