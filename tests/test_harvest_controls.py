#!/usr/bin/env python3
"""Tests for scripts/harvest_controls.py.

The acceptance criteria for the harvester are unusual enough to be worth stating as
tests rather than prose:

  * harvesting the bundled examples reproduces exactly the control types already in
    the catalog, with zero conflicts;
  * `--merge` against an unchanged catalog leaves the file byte-identical;
  * the absence caveat is present in the report, and nothing the tool writes can be
    read as a negative result.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
HARVESTER = ROOT / "scripts" / "harvest_controls.py"
CATALOG = ROOT / "skills" / "power-app-yaml" / "references" / "controls.yaml"
EXAMPLES = ROOT / "skills" / "power-app-yaml" / "assets" / "examples"

# Frozen so a date-stamped `source:` line cannot make a test flaky.
DATE = "2026-01-01"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HARVESTER), *args],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
    )


class HarvestExamplesTests(unittest.TestCase):
    """The bundled examples are the fixture: real, paste-tested screens."""

    @classmethod
    def setUpClass(cls):
        cls.proc = run(str(EXAMPLES), "--date", DATE)
        assert cls.proc.returncode == 0, cls.proc.stderr
        cls.fragment = yaml.safe_load(cls.proc.stdout)
        cls.catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))

    def test_fragment_is_valid_yaml_with_controls(self):
        self.assertIsInstance(self.fragment, dict)
        self.assertTrue(self.fragment["controls"])

    def test_reproduces_the_catalogued_control_types(self):
        """Every type the examples use is already catalogued, and all 8 are found."""
        harvested = {e["type"] for e in self.fragment["controls"]}
        catalogued = {e["type"] for e in self.catalog["controls"]}
        self.assertEqual(len(harvested), 8, f"expected 8 types, got {sorted(harvested)}")
        self.assertEqual(harvested - catalogued, set(),
                         "harvest found a control type the catalog does not have")

    def test_every_entry_is_marked_studio_export_with_a_source(self):
        for entry in self.fragment["controls"]:
            self.assertEqual(entry["evidence"], "studio-export", entry["type"])
            self.assertIn("harvested", entry["source"], entry["type"])
            self.assertIn(DATE, entry["source"], entry["type"])

    def test_never_writes_properties_unverified(self):
        """The absence caveat, enforced: no negative claim may be generated."""
        for entry in self.fragment["controls"]:
            self.assertEqual(entry["properties_unverified"], [], entry["type"])

    def test_universal_properties_are_left_to_the_catalog(self):
        universal = set(self.catalog["universal_properties"])
        for entry in self.fragment["controls"]:
            self.assertEqual(set(entry["properties_confirmed"]) & universal, set(),
                             entry["type"])

    def test_group_container_records_children_and_variant(self):
        entry = next(e for e in self.fragment["controls"]
                     if e["type"] == "GroupContainer@1.5.0")
        self.assertTrue(entry["accepts_children"])
        self.assertEqual(entry["variant"], "ManualLayout")

    def test_leaf_controls_are_marked_as_children_not_seen(self):
        entry = next(e for e in self.fragment["controls"] if e["type"] == "Label@2.5.1")
        self.assertFalse(entry["accepts_children"])
        self.assertIn("absence is not evidence", self.proc.stdout)


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proc = run(str(EXAMPLES), "--report", "--date", DATE)
        assert cls.proc.returncode == 0, cls.proc.stderr
        cls.out = cls.proc.stdout

    def test_report_states_the_absence_caveat(self):
        self.assertIn("ABSENCE CAVEAT", self.out)
        self.assertIn("NOT evidence that the control lacks it", self.out)

    def test_absence_section_is_labelled_untested_not_unsupported(self):
        self.assertIn("NEVER EXERCISED", self.out)
        self.assertIn("NOT unsupported", self.out)

    def test_reports_what_the_catalog_has_that_the_export_never_uses(self):
        # Classic/Radio is catalogued but appears in none of the bundled examples.
        self.assertIn("Classic/Radio@2.3.0", self.out)

    def test_holds_back_a_property_the_catalog_flags_unverified(self):
        # FontWeight is used on Classic/Button by example-app-shell.yaml, but the
        # catalog explicitly flags it unverified there. Positive evidence that must
        # still not be auto-promoted.
        self.assertIn("HELD BACK", self.out)
        self.assertIn("FontWeight", self.out)


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.catalog = self.tmp / "controls.yaml"
        shutil.copy2(CATALOG, self.catalog)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_merge_against_an_unchanged_catalog_is_byte_identical(self):
        before = self.catalog.read_bytes()
        proc = run(str(EXAMPLES), "--merge", "--catalog", str(self.catalog),
                   "--date", DATE)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("no changes", proc.stdout)
        self.assertEqual(self.catalog.read_bytes(), before,
                         "a no-op merge rewrote the catalog")

    def test_merge_over_the_examples_reports_zero_conflicts(self):
        proc = run(str(EXAMPLES), "--merge", "--catalog", str(self.catalog),
                   "--date", DATE)
        self.assertIn("0 conflicts.", proc.stdout)

    def _write_export(self, body: str) -> Path:
        path = self.tmp / "export"
        path.mkdir(exist_ok=True)
        (path / "Home.pa.yaml").write_text(body, encoding="utf-8")
        return path

    def test_merge_adds_a_new_control_and_new_properties(self):
        export = self._write_export(
            "Screens:\n"
            "  Home:\n"
            "    Children:\n"
            "      - tgl:\n"
            "          Control: Toggle@2.1.0\n"
            "          Properties:\n"
            "            TrueText: =\"On\"\n"
            "      - lbl:\n"
            "          Control: Label@2.5.1\n"
            "          Properties:\n"
            "            LineHeight: =1.2\n"
        )
        proc = run(str(export), "--merge", "--catalog", str(self.catalog),
                   "--date", DATE)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        merged = yaml.safe_load(self.catalog.read_text(encoding="utf-8"))
        by_type = {e["type"]: e for e in merged["controls"]}

        self.assertIn("Toggle@2.1.0", by_type)
        self.assertEqual(by_type["Toggle@2.1.0"]["evidence"], "studio-export")
        self.assertIn("LineHeight", by_type["Label@2.5.1"]["properties_confirmed"])

    def test_merge_preserves_comments_notes_and_evidence(self):
        original = self.catalog.read_text(encoding="utf-8")
        export = self._write_export(
            "Screens:\n"
            "  Home:\n"
            "    Children:\n"
            "      - lbl:\n"
            "          Control: Label@2.5.1\n"
            "          Properties:\n"
            "            LineHeight: =1.2\n"
        )
        run(str(export), "--merge", "--catalog", str(self.catalog), "--date", DATE)
        merged_text = self.catalog.read_text(encoding="utf-8")
        merged = yaml.safe_load(merged_text)
        label = next(e for e in merged["controls"] if e["type"] == "Label@2.5.1")

        self.assertIn("THE ABSENCE CAVEAT", merged_text,
                      "the top-level caveat comment was lost")
        self.assertIn("FontWeight confirmed on Label only", label["notes"],
                      "a hand-written notes field was overwritten")
        self.assertEqual(label["evidence"], "studio-tested",
                         "a studio-tested entry was downgraded")
        # The hand-written order survives; the harvested name is appended.
        self.assertEqual(label["properties_confirmed"][:6],
                         yaml.safe_load(original)["controls"][0]["properties_confirmed"])

    def test_merge_never_promotes_a_property_flagged_unverified(self):
        export = self._write_export(
            "Screens:\n"
            "  Home:\n"
            "    Children:\n"
            "      - btn:\n"
            "          Control: Classic/Button@2.2.0\n"
            "          Properties:\n"
            "            FontWeight: =FontWeight.Bold\n"
        )
        run(str(export), "--merge", "--catalog", str(self.catalog), "--date", DATE)
        merged = yaml.safe_load(self.catalog.read_text(encoding="utf-8"))
        button = next(e for e in merged["controls"]
                      if e["type"] == "Classic/Button@2.2.0")
        self.assertNotIn("FontWeight", button["properties_confirmed"])
        self.assertIn("FontWeight", button["properties_unverified"])

    def test_conflicts_are_reported_and_left_alone(self):
        export = self._write_export(
            "Screens:\n"
            "  Home:\n"
            "    Children:\n"
            "      - btn:\n"
            "          Control: Classic/Button@9.9.9\n"
            "          Properties:\n"
            "            Text: =\"x\"\n"
            "      - grp:\n"
            "          Control: GroupContainer@1.5.0\n"
            "          Variant: AutoLayout\n"
            "          Properties:\n"
            "            Fill: =RGBA(0, 0, 0, 1)\n"
        )
        before = self.catalog.read_bytes()
        proc = run(str(export), "--merge", "--catalog", str(self.catalog),
                   "--date", DATE)
        self.assertEqual(proc.returncode, 2, "conflicts must exit 2")
        self.assertIn("conflict: version", proc.stdout)
        self.assertIn("conflict: variant", proc.stdout)
        self.assertEqual(self.catalog.read_bytes(), before,
                         "a conflicting harvest must not be auto-resolved")

    def test_merge_is_idempotent(self):
        export = self._write_export(
            "Screens:\n"
            "  Home:\n"
            "    Children:\n"
            "      - tgl:\n"
            "          Control: Toggle@2.1.0\n"
            "          Properties:\n"
            "            TrueText: =\"On\"\n"
        )
        run(str(export), "--merge", "--catalog", str(self.catalog), "--date", DATE)
        once = self.catalog.read_bytes()
        run(str(export), "--merge", "--catalog", str(self.catalog), "--date", DATE)
        self.assertEqual(self.catalog.read_bytes(), once)


class MsappTests(unittest.TestCase):
    def test_reads_pa_yaml_out_of_an_msapp_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "Demo.msapp"
            with zipfile.ZipFile(archive, "w") as zf:
                # App.pa.yaml holds no control instances and must be skipped, not fail.
                zf.writestr("Src/App.pa.yaml", "App:\n  Properties:\n    OnStart: =1\n")
                zf.writestr(
                    "Src/Home.pa.yaml",
                    "Screens:\n  Home:\n    Children:\n      - lbl:\n"
                    "          Control: Label@2.5.1\n          Properties:\n"
                    "            Text: =\"hi\"\n",
                )
                zf.writestr(
                    "Src/Component/Card.pa.yaml",
                    "ComponentDefinitions:\n  Card:\n    DefinitionType: CanvasComponent\n"
                    "    Children:\n      - rect:\n          Control: Rectangle@2.3.0\n"
                    "          Properties:\n            Fill: =RGBA(0, 0, 0, 1)\n",
                )
                zf.writestr("Controls/1.json", "{}")
            proc = run(str(archive), "--date", DATE)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            fragment = yaml.safe_load(proc.stdout)
        types = {e["type"] for e in fragment["controls"]}
        self.assertEqual(types, {"Label@2.5.1", "Rectangle@2.3.0"})


class UsageTests(unittest.TestCase):
    def test_missing_source_is_an_error_not_a_crash(self):
        proc = run("no/such/path")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no readable source documents", proc.stderr)

    def test_help_carries_the_absence_caveat(self):
        proc = run("--help")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("ABSENCE CAVEAT", proc.stdout)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
