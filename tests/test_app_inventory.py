#!/usr/bin/env python3
"""Tests for scripts/app_inventory.py.

The headline acceptance criterion is a size limit, so it is asserted directly: the
synthetic 10-screen app under tests/apps/ must summarise in under 2 KB. Everything
else here exists to stop the tool meeting that limit by simply losing information
that matters -- the screen order, the variable literals, the collision list.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "scripts" / "app_inventory.py"
APP = ROOT / "tests" / "apps" / "ten-screen-app"
SRC = APP / "src"

BUDGET = 2048

# The fixture's declared editor order. Deliberately not alphabetical and not the
# order the files are read in, so honouring it is observable.
EXPECTED_ORDER = [
    "scrSplash", "scrHome", "scrRequestList", "scrRequestDetail", "scrNewRequest",
    "scrApprovals", "scrAttachments", "scrMyProfile", "scrSettings", "scrHelp",
]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
    )


def summary(*args: str) -> str:
    proc = run(str(APP), *args)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


class ToolExistsTests(unittest.TestCase):
    def test_tool_is_present(self):
        self.assertTrue(TOOL.is_file(), f"missing {TOOL}")

    def test_fixture_is_a_ten_screen_app(self):
        """A fixture that shrank would make the budget test meaningless."""
        self.assertTrue(SRC.is_dir(), f"missing {SRC}")
        screens = set()
        controls = 0
        for path in SRC.rglob("*.pa.yaml"):
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            screens |= set(doc.get("Screens") or {})
            controls += path.read_text(encoding="utf-8").count("Control:")
        self.assertEqual(len(screens), 10, f"expected 10 screens, got {sorted(screens)}")
        self.assertGreaterEqual(controls, 100,
                                "fixture is too small to exercise the byte budget")


class BudgetTests(unittest.TestCase):
    """The acceptance criterion: a 10-screen app fits on a page."""

    def test_ten_screen_app_summarises_under_2kb(self):
        size = len(summary().encode("utf-8"))
        self.assertLess(size, BUDGET, f"summary is {size} bytes, over the {BUDGET} budget")

    def test_summary_is_far_smaller_than_the_source(self):
        source = sum(p.stat().st_size for p in SRC.rglob("*.pa.yaml"))
        self.assertLess(len(summary().encode("utf-8")) * 10, source,
                        "the tool exists to save context; it is not saving much")

    def test_it_does_not_silently_overflow(self):
        """An impossible budget is reported, not quietly exceeded."""
        out = summary("--max-bytes", "200")
        self.assertIn("OVER BUDGET", out)

    def test_a_generous_budget_buys_more_detail(self):
        """The tier is chosen by fit, so more room must yield individual controls."""
        tight, loose = summary(), summary("--max-bytes", "20000")
        self.assertNotIn("lblSplashTitle", tight)
        self.assertIn("lblSplashTitle", loose)
        self.assertIn("[detail: every control", loose)

    def test_the_detail_level_is_stated(self):
        self.assertIn("[detail:", summary())


class ContentTests(unittest.TestCase):
    """What the page must still contain after all that summarising."""

    @classmethod
    def setUpClass(cls):
        cls.out = summary()

    def test_every_screen_is_named(self):
        for screen in EXPECTED_ORDER:
            self.assertIn(screen, self.out)

    def test_screens_follow_editorstate_screensorder(self):
        self.assertIn("EditorState.ScreensOrder", self.out)
        positions = [self.out.index(f"\n  {s} ") for s in EXPECTED_ORDER]
        self.assertEqual(positions, sorted(positions),
                         "screens are not in EditorState.ScreensOrder order")

    def test_order_falls_back_and_says_so(self):
        """An export with no ScreensOrder must not pretend it had one."""
        out = run(str(SRC / "scrHome.pa.yaml")).stdout
        self.assertIn("no EditorState.ScreensOrder", out)

    def test_control_types_keep_their_versions(self):
        """Extending an app means matching the versions the app already uses."""
        for ctype in ("Label@2.5.1", "Classic/Button@2.2.0", "GroupContainer@1.5.0"):
            self.assertIn(ctype, self.out)

    def test_container_variant_is_reported(self):
        self.assertIn("[ManualLayout]", self.out)

    def test_nesting_depth_is_reported(self):
        self.assertIn("d3", self.out)

    def test_onstart_literals_are_shown(self):
        for expected in ('varThemePrimary=ColorValue("#005AB6")',
                         "varThemeText=RGBA(24,28,35,1)",
                         'varAppTitle="Field Service Requests"',
                         "varPageSize=25",
                         "varIsAdmin=false"):
            self.assertIn(expected, self.out)

    def test_non_literal_onstart_values_are_not_guessed(self):
        """User().Email is not a literal, so no value is claimed for it."""
        self.assertIn("varUserEmail=~expr", self.out)
        self.assertNotIn("varUserEmail=User", self.out)

    def test_collections_are_reported_with_their_setter(self):
        self.assertIn("colSites=ClearCollect(~)", self.out)
        self.assertIn("colRecent=Collect(~)", self.out)

    def test_data_sources_with_their_type(self):
        self.assertIn("Requests[Table]", self.out)
        self.assertIn("GenerateDocument[Actions]", self.out)

    def test_component_definitions_are_listed(self):
        self.assertIn("cmpPageHeader", self.out)
        self.assertIn("cmpEmptyState", self.out)

    def test_property_values_are_never_dumped(self):
        """Property dumps are the bulk of an export and the thing to leave out."""
        for leaked in ("Icon.CheckBadge", "HintText", "Notify", "RGBA(244"):
            self.assertNotIn(leaked, self.out)


class CollisionListTests(unittest.TestCase):
    def test_names_flag_lists_every_screen_and_control(self):
        names = set(summary("--names").split())
        self.assertTrue(set(EXPECTED_ORDER) <= names, "screen names missing")
        # A name that only exists three levels down: proves the walk recurses.
        self.assertIn("btnTileOpen", names)
        self.assertIn("lblRow1Title", names)

    def test_names_are_unique_and_sorted(self):
        listed = summary("--names").split()
        self.assertEqual(len(listed), len(set(listed)))
        self.assertEqual(listed, sorted(listed, key=str.lower))

    def test_the_page_says_how_to_get_the_full_list(self):
        self.assertIn("--names", summary())

    def test_collision_risk_is_spelled_out(self):
        self.assertIn("_1", summary())


class JsonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(summary("--json"))

    def test_json_is_not_budgeted(self):
        self.assertGreater(len(json.dumps(self.data)), BUDGET)

    def test_screens_in_editor_order_with_controls(self):
        self.assertEqual([s["name"] for s in self.data["screens"]], EXPECTED_ORDER)
        self.assertEqual(self.data["screens_order_source"], "EditorState.ScreensOrder")

    def test_controls_carry_type_variant_and_depth(self):
        home = next(s for s in self.data["screens"] if s["name"] == "scrHome")
        by_name = {c["name"]: c for c in home["controls"]}
        self.assertEqual(by_name["grpTiles"]["type"], "GroupContainer@1.5.0")
        self.assertEqual(by_name["grpTiles"]["variant"], "ManualLayout")
        self.assertEqual(by_name["grpTiles"]["depth"], 1)
        self.assertEqual(by_name["btnTileOpen"]["depth"], 3)
        self.assertEqual(home["max_depth"], 3)

    def test_onstart_literals_and_non_literals(self):
        by_name = {v["name"]: v for v in self.data["onstart"]}
        self.assertEqual(by_name["varPageSize"]["literal"], "25")
        self.assertIsNone(by_name["varUserEmail"]["literal"])
        self.assertEqual(by_name["colSites"]["kind"], "ClearCollect")

    def test_totals_match_the_screens(self):
        counted = sum(len(s["controls"]) for s in self.data["screens"])
        self.assertEqual(sum(t["count"] for t in self.data["types"]), counted)


class MsappTests(unittest.TestCase):
    """An .msapp is the format a user actually has on disk."""

    def _packed(self):
        tmp = Path(tempfile.mkdtemp()) / "demo.msapp"
        with zipfile.ZipFile(tmp, "w") as archive:
            for path in sorted(SRC.rglob("*.pa.yaml")):
                archive.writestr("src/" + path.relative_to(SRC).as_posix(),
                                 path.read_text(encoding="utf-8"))
            # Everything outside src/ is build output, not source. It must be ignored.
            archive.writestr("Controls/1.json", "{}")
            archive.writestr("Other/stray.pa.yaml",
                             "Screens:\n  scrStray:\n    Children: []\n")
        return tmp

    def test_msapp_reads_only_the_src_folder(self):
        proc = run(str(self._packed()))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("10 screens", proc.stdout)
        self.assertNotIn("scrStray", proc.stdout)

    def test_msapp_matches_the_unpacked_folder(self):
        packed = json.loads(run(str(self._packed()), "--json").stdout)
        folder = json.loads(run(str(APP), "--json").stdout)
        self.assertEqual([s["name"] for s in packed["screens"]],
                         [s["name"] for s in folder["screens"]])
        self.assertEqual(packed["names_in_use"], folder["names_in_use"])

    def test_a_zip_without_sources_is_reported(self):
        tmp = Path(tempfile.mkdtemp()) / "empty.msapp"
        with zipfile.ZipFile(tmp, "w") as archive:
            archive.writestr("Controls/1.json", "{}")
        proc = run(str(tmp))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no src/**/*.pa.yaml", proc.stderr)


class FailureTests(unittest.TestCase):
    def test_missing_source_exits_1(self):
        proc = run("no/such/folder")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no such file or directory", proc.stderr)

    def test_unparseable_file_is_reported_not_fatal(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "broken.pa.yaml").write_text("Screens:\n  - [unclosed\n", encoding="utf-8")
        (tmp / "ok.pa.yaml").write_text(
            "Screens:\n  scrOk:\n    Children:\n      - lblOk:\n"
            "          Control: Label@2.5.1\n", encoding="utf-8")
        proc = run(str(tmp))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("scrOk", proc.stdout)
        self.assertIn("broken.pa.yaml", proc.stdout)


if __name__ == "__main__":
    unittest.main()
