#!/usr/bin/env python3
"""Fixture-driven tests for scripts/pa_lint.py.

Each fixture under tests/fixtures/{valid,invalid}/ is a small .pa.yaml paired with a
<name>.expected.json sidecar naming the layer and check id that must fire.

Assertions are on **check ids and exit codes only** -- never on message wording -- so
rephrasing a diagnostic does not break the suite.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINTER = ROOT / "scripts" / "pa_lint.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
EXAMPLES = ROOT / "skills" / "power-app-yaml" / "assets" / "examples"


def run_linter(*args: str) -> tuple[int, dict, str]:
    """Run the linter and return (exit_code, parsed_json, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(LINTER), *args, "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - failure path
        raise AssertionError(
            f"--json did not emit valid JSON (exit {proc.returncode}).\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        ) from exc
    return proc.returncode, payload, proc.stderr


def fixture_pairs() -> list[tuple[Path, dict]]:
    pairs = []
    for yaml_path in sorted(FIXTURES.rglob("*.pa.yaml")):
        sidecar = yaml_path.with_name(yaml_path.name.replace(".pa.yaml", ".expected.json"))
        if not sidecar.is_file():
            raise AssertionError(f"fixture {yaml_path.name} has no .expected.json sidecar")
        pairs.append((yaml_path, json.loads(sidecar.read_text(encoding="utf-8"))))
    return pairs


def finding_ids(file_report: dict) -> set[tuple[str, str]]:
    return {(f["layer"], f["check"]) for f in file_report["findings"]}


def expected_ids(expected: dict) -> set[tuple[str, str]]:
    return {(f["layer"], f["check"]) for f in expected["expected_findings"]}


class TestLinterExists(unittest.TestCase):
    def test_linter_script_is_present(self):
        self.assertTrue(LINTER.is_file(), f"missing {LINTER}")

    def test_every_fixture_has_a_sidecar(self):
        self.assertGreaterEqual(len(fixture_pairs()), 10, "expected at least 10 fixtures")


class TestFixtures(unittest.TestCase):
    """Every fixture must produce exactly the findings its sidecar declares."""

    def test_fixtures_produce_expected_findings(self):
        for yaml_path, expected in fixture_pairs():
            with self.subTest(fixture=yaml_path.name):
                code, payload, stderr = run_linter(str(yaml_path))
                self.assertEqual(len(payload["files"]), 1, "one file in, one report out")
                report = payload["files"][0]

                self.assertEqual(
                    finding_ids(report),
                    expected_ids(expected),
                    f"\n{yaml_path.name}: {expected['description']}"
                    f"\n  got:      {sorted(finding_ids(report))}"
                    f"\n  expected: {sorted(expected_ids(expected))}",
                )
                self.assertEqual(code, expected["expected_exit_code"], yaml_path.name)
                self.assertEqual(
                    report["verdict_code"], expected["expected_verdict_code"], yaml_path.name
                )
                self.assertEqual(stderr.strip(), "", "linter must not leak a traceback")


class TestLayerShortCircuit(unittest.TestCase):
    """A layer that makes later layers meaningless must stop the run."""

    def test_parse_error_suppresses_later_layers(self):
        _, payload, _ = run_linter(str(FIXTURES / "invalid" / "broken-yaml.pa.yaml"))
        layers = {f["layer"] for f in payload["files"][0]["findings"]}
        self.assertEqual(layers, {"L0"})

    def test_schema_error_suppresses_catalog_and_convention_layers(self):
        _, payload, _ = run_linter(str(FIXTURES / "invalid" / "missing-equals.pa.yaml"))
        layers = {f["layer"] for f in payload["files"][0]["findings"]}
        self.assertEqual(layers, {"L1"})


class TestFindingShape(unittest.TestCase):
    def test_schema_findings_carry_a_yaml_path(self):
        _, payload, _ = run_linter(str(FIXTURES / "invalid" / "missing-equals.pa.yaml"))
        finding = payload["files"][0]["findings"][0]
        self.assertTrue(finding["path"].startswith("Screens.Home.Children["))
        self.assertTrue(finding["path"].endswith("Properties.Text"))

    def test_parse_error_reports_line_and_column(self):
        _, payload, _ = run_linter(str(FIXTURES / "invalid" / "broken-yaml.pa.yaml"))
        finding = payload["files"][0]["findings"][0]
        self.assertIsInstance(finding["line"], int)
        self.assertIsInstance(finding["column"], int)

    def test_severity_maps_errors_to_l0_l1_and_warnings_to_l2_l3(self):
        for name, layer, severity in [
            ("missing-equals.pa.yaml", "L1", "error"),
            ("invented-control-type.pa.yaml", "L2", "warning"),
        ]:
            with self.subTest(fixture=name):
                _, payload, _ = run_linter(str(FIXTURES / "invalid" / name))
                match = [f for f in payload["files"][0]["findings"] if f["layer"] == layer]
                self.assertTrue(match)
                self.assertEqual(match[0]["severity"], severity)


class TestIsolatedTestSnippet(unittest.TestCase):
    """Acceptance criterion: an L2 warning ships a ready-to-paste test snippet."""

    def _l2_snippet(self, fixture_name: str) -> str:
        _, payload, _ = run_linter(str(FIXTURES / "invalid" / fixture_name))
        l2 = [f for f in payload["files"][0]["findings"] if f["layer"] == "L2"]
        self.assertTrue(l2, "expected an L2 finding")
        snippet = l2[0]["snippet"]
        self.assertIsInstance(snippet, str)
        return snippet

    def test_unverified_control_snippet_is_a_full_screens_wrapper(self):
        snippet = self._l2_snippet("invented-control-type.pa.yaml")
        self.assertIn("Screens:", snippet)
        self.assertIn("SuperGrid@1.0.0", snippet)

    def test_snippet_parses_and_contains_exactly_one_control(self):
        import yaml  # local import keeps the rest of the suite dependency-free

        snippet = self._l2_snippet("invented-control-type.pa.yaml")
        doc = yaml.safe_load(snippet)
        screens = doc["Screens"]
        self.assertEqual(len(screens), 1)
        children = next(iter(screens.values()))["Children"]
        self.assertEqual(len(children), 1, "snippet must isolate a single control")

    def test_unverified_property_snippet_isolates_that_property(self):
        import yaml

        snippet = self._l2_snippet("invented-property.pa.yaml")
        doc = yaml.safe_load(snippet)
        children = next(iter(doc["Screens"].values()))["Children"]
        props = next(iter(children[0].values()))["Properties"]
        self.assertIn("BoxShadow", props)


class TestBundledExamples(unittest.TestCase):
    """Acceptance criterion: the three shipped examples must lint at exit 0."""

    def test_all_bundled_examples_exit_zero(self):
        examples = sorted(EXAMPLES.glob("*.yaml"))
        self.assertEqual(len(examples), 3, "expected three bundled examples")
        code, payload, stderr = run_linter(*[str(p) for p in examples])
        self.assertEqual(stderr.strip(), "")
        self.assertEqual(code, 0, "bundled examples must not produce blocking errors")
        for report in payload["files"]:
            with self.subTest(example=Path(report["path"]).name):
                blocking = [f for f in report["findings"] if f["severity"] == "error"]
                self.assertEqual(blocking, [], "no L0/L1 errors in a shipped example")


class TestDegradedWithoutJsonschema(unittest.TestCase):
    """Without jsonschema the L1 layer cannot run, so the linter must not claim the
    file is safe -- it has not checked the layer that catches PA1001."""

    def _run_without_jsonschema(self, fixture: Path, *extra: str):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as stub_dir:
            # A module that raises on import, simulating an environment where the
            # optional dependency is absent.
            Path(stub_dir, "jsonschema.py").write_text(
                'raise ImportError("simulated missing dependency")\n', encoding="utf-8"
            )
            env = dict(os.environ, PYTHONPATH=stub_dir)
            proc = subprocess.run(
                [sys.executable, str(LINTER), str(fixture), *extra],
                capture_output=True, text=True, encoding="utf-8",
                cwd=str(ROOT), env=env,
            )
        return proc

    def test_does_not_crash_without_jsonschema(self):
        proc = self._run_without_jsonschema(FIXTURES / "invalid" / "missing-equals.pa.yaml")
        self.assertNotIn("Traceback", proc.stderr)

    def test_says_the_schema_layer_was_skipped(self):
        proc = self._run_without_jsonschema(FIXTURES / "invalid" / "missing-equals.pa.yaml")
        self.assertIn("jsonschema", proc.stdout)

    def test_never_reports_safe_to_paste_when_the_schema_layer_was_skipped(self):
        proc = self._run_without_jsonschema(FIXTURES / "invalid" / "missing-equals.pa.yaml")
        self.assertNotIn("SAFE TO PASTE", proc.stdout)

    def test_a_clean_file_is_also_unproven_not_safe(self):
        proc = self._run_without_jsonschema(FIXTURES / "valid" / "clean-screen.pa.yaml")
        self.assertNotIn("SAFE TO PASTE", proc.stdout)

    def test_catalog_layers_still_run(self):
        proc = self._run_without_jsonschema(FIXTURES / "invalid" / "invented-control-type.pa.yaml")
        self.assertIn("L2.unverified-control-type", proc.stdout)

    def test_strict_refuses_to_pass_an_unproven_file(self):
        proc = self._run_without_jsonschema(
            FIXTURES / "valid" / "clean-screen.pa.yaml", "--strict"
        )
        self.assertEqual(proc.returncode, 2)


class TestExitCodes(unittest.TestCase):
    def test_strict_turns_warnings_into_exit_2(self):
        target = str(FIXTURES / "invalid" / "navigate-missing-screen.pa.yaml")
        proc = subprocess.run(
            [sys.executable, str(LINTER), target, "--strict"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 2)

    def test_strict_does_not_downgrade_a_real_error(self):
        target = str(FIXTURES / "invalid" / "missing-equals.pa.yaml")
        proc = subprocess.run(
            [sys.executable, str(LINTER), target, "--strict"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 1)

    def test_clean_file_is_exit_zero_even_with_strict(self):
        target = str(FIXTURES / "valid" / "clean-screen.pa.yaml")
        proc = subprocess.run(
            [sys.executable, str(LINTER), target, "--strict"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 0)


class TestHumanOutput(unittest.TestCase):
    def _run_text(self, *args: str) -> tuple[int, str]:
        proc = subprocess.run(
            [sys.executable, str(LINTER), *args],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        )
        return proc.returncode, proc.stdout

    def test_verdict_line_is_present_for_each_outcome(self):
        for fixture, fragment in [
            (FIXTURES / "valid" / "clean-screen.pa.yaml", "VERDICT: SAFE TO PASTE"),
            (FIXTURES / "invalid" / "missing-equals.pa.yaml", "VERDICT: WILL FAIL"),
            (FIXTURES / "invalid" / "navigate-missing-screen.pa.yaml", "VERDICT: PASTES, BUT"),
        ]:
            with self.subTest(fixture=fixture.name):
                _, out = self._run_text(str(fixture))
                self.assertIn(fragment, out)

    def test_quiet_prints_only_the_verdict(self):
        _, out = self._run_text(str(FIXTURES / "invalid" / "navigate-missing-screen.pa.yaml"), "--quiet")
        lines = [ln for ln in out.splitlines() if ln.strip()]
        self.assertTrue(all(ln.startswith("VERDICT:") for ln in lines), out)

    def test_no_raw_jsonschema_traceback_leaks(self):
        _, out = self._run_text(str(FIXTURES / "invalid" / "missing-equals.pa.yaml"))
        self.assertNotIn("Traceback", out)
        self.assertNotIn("is not valid under any of the given schemas", out)


if __name__ == "__main__":
    unittest.main()
