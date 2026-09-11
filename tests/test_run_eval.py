#!/usr/bin/env python3
"""Tests for scripts/run_eval.py -- the eval scorer.

The scorer's job is to be believable: a green table has to mean something, and a
red one has to point at the right thing. So these tests are mostly negative --
they feed it output that is wrong in one specific way and assert that the row
which should go red is the one that does.

Assertions are on **check ids and exit codes only**, never on message wording.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts" / "run_eval.py"
EVALS = ROOT / "tests" / "evals"
EXAMPLES = ROOT / "skills" / "power-app-yaml" / "assets" / "examples"

REQUIRED_CASES = {
    "app-shell", "multi-section-form", "card-grid",
    "shell-with-form", "impossible-effects",
}


def run(*args: str):
    """Run the scorer with --json and return (exit_code, payload, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(RUNNER), *args, "--json"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - failure path
        raise AssertionError(
            f"--json did not emit valid JSON (exit {proc.returncode}).\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        ) from exc
    return proc.returncode, payload, proc.stderr


def rows_of(payload, index=0):
    return {r["check"]: r["result"] for r in payload["results"][index]["rows"]}


class TempOutput:
    """A .pa.yaml on disk for the duration of a test."""

    def __init__(self, body: str):
        self.body = textwrap.dedent(body).lstrip("\n")

    def __enter__(self):
        self._dir = tempfile.TemporaryDirectory()
        path = Path(self._dir.name) / "out.pa.yaml"
        path.write_text(self.body, encoding="utf-8")
        return path

    def __exit__(self, *exc):
        self._dir.cleanup()


# --------------------------------------------------------------- the case fixtures


class CaseFixtureTests(unittest.TestCase):
    """The cases themselves, before anything is scored against them."""

    def test_the_five_required_cases_exist(self):
        found = {d.name for d in EVALS.iterdir()
                 if (d / "expectations.yaml").is_file()}
        self.assertTrue(REQUIRED_CASES <= found,
                        f"missing case(s): {sorted(REQUIRED_CASES - found)}")

    def test_every_case_has_all_three_files(self):
        for directory in sorted(EVALS.iterdir()):
            if not directory.is_dir():
                continue
            with self.subTest(case=directory.name):
                for name in ("mockup.html", "expectations.yaml", "notes.md"):
                    self.assertTrue((directory / name).is_file(),
                                    f"{directory.name}/{name} is missing")

    def test_mockups_are_self_contained(self):
        """A case that needs the network scores differently on a machine without it."""
        import re
        external = re.compile(
            r"""(?:src|href)\s*=\s*["'](?:https?:)?//""", re.IGNORECASE)
        at_import = re.compile(r"@import\s+(?:url\()?['\"]?(?:https?:)?//",
                               re.IGNORECASE)
        for directory in sorted(EVALS.iterdir()):
            mockup = directory / "mockup.html"
            if not mockup.is_file():
                continue
            with self.subTest(case=directory.name):
                text = mockup.read_text(encoding="utf-8")
                self.assertIsNone(external.search(text),
                                  "mockup pulls an external asset")
                self.assertIsNone(at_import.search(text),
                                  "mockup @imports a remote stylesheet")

    def test_the_hard_case_uses_only_catalogued_impossible_effects(self):
        """impossible-effects must assert ids that controls.yaml actually lists --
        otherwise the case is testing an effect this repo has no position on."""
        import yaml
        catalog = yaml.safe_load(
            (ROOT / "skills" / "power-app-yaml" / "references" / "controls.yaml")
            .read_text(encoding="utf-8-sig"))
        known = {e["id"] for e in catalog.get("impossible_css") or []}
        spec = yaml.safe_load(
            (EVALS / "impossible-effects" / "expectations.yaml")
            .read_text(encoding="utf-8-sig"))
        asserted = {e["id"] for e in spec["limitations"]["declared"]}
        self.assertTrue(asserted <= known,
                        f"not in controls.yaml's impossible_css: {sorted(asserted - known)}")
        self.assertTrue(asserted, "the hard case asserts no limitations at all")


# ------------------------------------------------------------------ the self-check


class SelfCheckTests(unittest.TestCase):
    """Bare `run_eval.py` -- the acceptance criterion, as an assertion."""

    def test_scores_the_bundled_examples_without_crashing(self):
        code, payload, stderr = run()
        self.assertIn(code, (0, 1), f"crashed (exit {code}): {stderr}")
        scored = {r["case"] for r in payload["results"]}
        self.assertEqual(scored, {"app-shell", "multi-section-form", "card-grid"})

    def test_the_self_check_passes(self):
        code, payload, _ = run()
        bad = [(r["case"], c)
               for r in payload["results"]
               for c, v in ((row["check"], row["result"]) for row in r["rows"])
               if v in ("FAIL", "XPASS")]
        self.assertEqual(bad, [], f"unexpected results: {bad}")
        self.assertEqual(code, 0)

    def test_each_reference_run_is_marked_as_a_reference(self):
        """A reference is hand-written, not model output. If the report stopped
        saying so, the self-check would read as evidence about the skill."""
        _, payload, _ = run()
        for result in payload["results"]:
            self.assertTrue(result["reference"], result["case"])

    def test_declared_deviations_are_reported_as_xfail_not_pass(self):
        _, payload, _ = run()
        app_shell = next(r for r in payload["results"] if r["case"] == "app-shell")
        rows = {row["check"]: row["result"] for row in app_shell["rows"]}
        self.assertEqual(rows["lint.verdict"], "XFAIL")
        self.assertEqual(rows["lint.warnings"], "XFAIL")
        self.assertEqual(rows["catalog.unverified-properties"], "XFAIL")
        # The reason has to travel with the row -- a waiver nobody can read is
        # indistinguishable from a bug.
        note = next(row["note"] for row in app_shell["rows"]
                    if row["check"] == "lint.verdict")
        self.assertIn("known:", note)

    def test_a_waiver_never_applies_to_a_file_given_on_the_command_line(self):
        """The app-shell reference scores XFAIL in self-check mode. The same file
        passed explicitly must score FAIL -- waivers describe the bundled
        reference, not whatever a user just generated."""
        code, payload, _ = run(str(EXAMPLES / "example-app-shell.yaml"),
                               "--case", str(EVALS / "app-shell"))
        self.assertEqual(code, 1)
        self.assertEqual(rows_of(payload)["lint.verdict"], "FAIL")
        self.assertFalse(payload["results"][0]["reference"])


# --------------------------------------------------------------- negative scoring


class NegativeScoringTests(unittest.TestCase):
    """One wrong thing at a time; assert the right row goes red."""

    MINIMAL = """
        Screens:
          Home:
            Properties:
              Fill: =RGBA(244, 244, 246, 1)
            Children:
              - lblOnly:
                  Control: Label@2.5.1
                  Properties:
                    Text: ="Hello"
                    X: =0
                    Y: =0
                    Width: =200
                    Height: =40
    """

    def test_an_abbreviated_screen_fails_on_control_count(self):
        with TempOutput(self.MINIMAL) as path:
            code, payload, _ = run(str(path), "--case", str(EVALS / "card-grid"))
        rows = rows_of(payload)
        self.assertEqual(code, 1)
        self.assertEqual(rows["controls.total"], "FAIL")
        self.assertEqual(rows["output.parses"], "PASS")

    def test_a_control_outside_the_canvas_fails_on_geometry(self):
        with TempOutput("""
            Screens:
              Home:
                Properties:
                  Fill: =RGBA(244, 244, 246, 1)
                Children:
                  - lblWide:
                      Control: Label@2.5.1
                      Properties:
                        Text: ="Off the edge"
                        X: =1300
                        Y: =0
                        Width: =400
                        Height: =40
        """) as path:
            _, payload, _ = run(str(path), "--case", str(EVALS / "shell-with-form"))
        self.assertEqual(rows_of(payload)["geometry.in-bounds"], "FAIL")

    def test_a_taller_screen_moves_its_own_bounds(self):
        """A screen that declares Height: =2000 may legitimately place a control at
        Y 1900. The same control on a 768px screen may not."""
        body = """
            Screens:
              Home:
                Properties:
                  Fill: =RGBA(244, 244, 246, 1)
                  Height: =2000
                Children:
                  - lblLow:
                      Control: Label@2.5.1
                      Properties:
                        Text: ="Far down"
                        X: =0
                        Y: =1900
                        Width: =200
                        Height: =40
        """
        with TempOutput(body) as path:
            _, tall, _ = run(str(path), "--case", str(EVALS / "multi-section-form"))
        self.assertEqual(rows_of(tall)["geometry.in-bounds"], "PASS")

        short = "\n".join(ln for ln in body.splitlines()
                          if ln.strip() != "Height: =2000")
        with TempOutput(short) as path:
            _, short, _ = run(str(path), "--case", str(EVALS / "multi-section-form"))
        self.assertEqual(rows_of(short)["geometry.in-bounds"], "FAIL")

    def test_a_dangling_navigate_fails_but_a_commented_one_does_not(self):
        dangling = """
            Screens:
              Home:
                Properties:
                  Fill: =RGBA(244, 244, 246, 1)
                Children:
                  - btnGo:
                      Control: Classic/Button@2.2.0
                      Properties:
                        Text: ="Go"
                        OnSelect: =Navigate('Nowhere', ScreenTransition.Fade)
                        X: =0
                        Y: =0
                        Width: =200
                        Height: =40
        """
        with TempOutput(dangling) as path:
            _, payload, _ = run(str(path), "--case", str(EVALS / "shell-with-form"))
        self.assertEqual(rows_of(payload)["navigation.targets-resolve"], "FAIL")

        commented = dangling.replace(
            "ScreenTransition.Fade)",
            "ScreenTransition.Fade)  # placeholder - not a screen in this file")
        with TempOutput(commented) as path:
            _, payload, _ = run(str(path), "--case", str(EVALS / "shell-with-form"))
        self.assertEqual(rows_of(payload)["navigation.targets-resolve"], "PASS")

    def test_a_forbidden_control_type_fails(self):
        with TempOutput("""
            Screens:
              Home:
                Properties:
                  Fill: =RGBA(244, 244, 246, 1)
                Children:
                  - galRows:  # UNVERIFIED - Gallery is not in the catalog
                      Control: Gallery
                      Properties:
                        X: =0
                        Y: =0
                        Width: =600
                        Height: =400
        """) as path:
            _, payload, _ = run(str(path), "--case", str(EVALS / "card-grid"))
        self.assertEqual(rows_of(payload)["controls.forbidden:Gallery"], "FAIL")

    def test_a_file_that_does_not_parse_is_one_failure_not_fifteen(self):
        with TempOutput("Screens:\n  Home:\n   Properties:\n  \tFill: =1\n") as path:
            code, payload, _ = run(str(path), "--case", str(EVALS / "app-shell"))
        rows = rows_of(payload)
        self.assertEqual(code, 1)
        self.assertEqual(rows["output.parses"], "FAIL")
        self.assertEqual(
            [r for r in rows.values() if r == "FAIL"], ["FAIL"],
            "a file that will not parse should produce exactly one FAIL row; "
            "everything downstream is UNPROVEN, not failed")
        self.assertEqual(rows["controls.total"], "UNPROVEN")


class LimitationScoringTests(unittest.TestCase):
    """The hard case: the three ways to get an impossible effect wrong."""

    HEAD = """
        Screens:
          NotificationSettings:
            Properties:
              Fill: =RGBA(244, 244, 246, 1)
            Children:
    """

    CARD = """
              - grpCard:
                  Control: GroupContainer@1.5.0
                  Variant: ManualLayout
                  Properties:
                    Fill: =RGBA(255, 255, 255, 1)
                    X: =383
                    Y: =240
                    Width: =600
                    Height: =200
    """

    def _score(self, body):
        with TempOutput(body) as path:
            return run(str(path), "--case", str(EVALS / "impossible-effects"))

    def test_faking_the_effect_is_named_as_faking(self):
        _, payload, _ = self._score(self.HEAD + """
              - grpCard:
                  Control: GroupContainer@1.5.0
                  Variant: ManualLayout
                  Properties:
                    Fill: =RGBA(255, 255, 255, 1)
                    BoxShadow: ="0 8px 24px"
                    X: =383
                    Y: =240
                    Width: =600
                    Height: =200
        """)
        rows = rows_of(payload)
        self.assertEqual(rows["limitations.no-invented-property"], "FAIL")
        # And the lint layer sees it too, from the other direction.
        self.assertEqual(rows["catalog.unverified-properties"], "FAIL")

    def test_silence_fails_every_declaration_row(self):
        _, payload, _ = self._score(self.HEAD + self.CARD)
        rows = rows_of(payload)
        declared = [v for k, v in rows.items() if k.startswith("limitations.declared:")]
        self.assertTrue(declared, "the case declares no limitations")
        self.assertTrue(all(v == "FAIL" for v in declared), declared)

    def test_naming_an_effect_in_a_comment_passes_that_row(self):
        _, payload, _ = self._score(self.HEAD + """
              - grpCard:
                  # The mockup's box-shadow has no confirmed Power Fx equivalent.
                  Control: GroupContainer@1.5.0
                  Variant: ManualLayout
                  Properties:
                    Fill: =RGBA(255, 255, 255, 1)
                    X: =383
                    Y: =240
                    Width: =600
                    Height: =200
        """)
        rows = rows_of(payload)
        self.assertEqual(rows["limitations.declared:box-shadow"], "PASS")
        self.assertEqual(rows["limitations.declared:backdrop-blur"], "FAIL")

    def test_dropping_the_substitute_scores_differently_from_offering_it(self):
        _, without, _ = self._score(self.HEAD + self.CARD)
        self.assertEqual(rows_of(without)["limitations.substitute-offered"], "FAIL")

        _, with_rect, _ = self._score(self.HEAD + self.CARD + """
              - recLeftBorder:
                  Control: Rectangle@2.3.0
                  Properties:
                    Fill: =RGBA(0, 127, 250, 1)
                    X: =383
                    Y: =180
                    Width: =4
                    Height: =48
        """)
        self.assertEqual(rows_of(with_rect)["limitations.substitute-offered"], "PASS")


# ------------------------------------------------------------------------- CLI


class CliTests(unittest.TestCase):

    def test_an_output_without_a_case_is_a_usage_error(self):
        proc = subprocess.run(
            [sys.executable, str(RUNNER), str(EXAMPLES / "example-form.yaml")],
            capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(proc.returncode, 2)

    def test_a_missing_output_file_exits_2(self):
        proc = subprocess.run(
            [sys.executable, str(RUNNER), "no-such-file.pa.yaml",
             "--case", str(EVALS / "app-shell")],
            capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(proc.returncode, 2)

    def test_list_names_every_case(self):
        proc = subprocess.run(
            [sys.executable, str(RUNNER), "--list"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
        self.assertEqual(proc.returncode, 0)
        for name in REQUIRED_CASES:
            self.assertIn(name, proc.stdout)

    def test_a_case_with_a_reasonless_waiver_is_rejected(self):
        """A known deviation without a stated reason is indistinguishable from a
        bug, so the scorer refuses the case rather than scoring it."""
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "broken"
            case.mkdir()
            (case / "expectations.yaml").write_text(textwrap.dedent("""
                case: broken
                lint:
                  max_errors: 0
                reference:
                  output: ../whatever.yaml
                  known_deviations:
                    - check: lint.errors
            """).lstrip(), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(RUNNER), str(EXAMPLES / "example-form.yaml"),
                 "--case", str(case)],
                capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("reason", proc.stderr.lower())

    def test_text_output_states_the_reference_is_not_model_generated(self):
        """The single most misreadable thing about this harness. If the disclaimer
        goes missing, a green self-check starts looking like evidence."""
        proc = subprocess.run(
            [sys.executable, str(RUNNER)],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
        self.assertIn("not model-generated", proc.stdout)
        self.assertIn("says nothing about the skill", proc.stdout)


if __name__ == "__main__":
    unittest.main()
