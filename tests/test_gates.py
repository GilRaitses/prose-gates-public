#!/usr/bin/env python3
"""Fixture tests for check_gates.py. Stdlib only. Run: python3 tests/test_gates.py"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from check_gates import (  # noqa: E402
    RANGE_FIX,
    apply_range_fixes,
    check_file,
)

FIXTURES = ROOT / "fixtures"
MANIFEST = FIXTURES / "cases.tsv"
NEW_GATES = {
    "HEDGE",
    "OPENER",
    "POINTER",
    "FRAME",
    "PROMISE",
    "HYPE",
    "ARROW",
    "SEMICOLON",
    "RANGE",
}


def load_cases() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for i, raw in enumerate(MANIFEST.read_text(encoding="utf-8").splitlines()):
        if i == 0 or not raw.strip():
            continue
        gate, verdict, sentence = raw.split("\t", 2)
        rows.append((gate, verdict, sentence))
    return rows


def gates_for(path: Path) -> set[str]:
    return {g for g, _sev, _ln, _sn in check_file(path, strict=True)}


def write_temp(suffix: str, text: str) -> Path:
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=suffix,
        delete=False,
    )
    handle.write(text)
    handle.close()
    return Path(handle.name)


class FixtureCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_cases()

    def test_manifest_has_fail_and_pass_per_new_gate(self) -> None:
        by_gate: dict[str, set[str]] = {}
        for gate, verdict, _sentence in self.cases:
            by_gate.setdefault(gate, set()).add(verdict)
        for gate in NEW_GATES:
            self.assertEqual(
                by_gate.get(gate),
                {"fail", "pass"},
                f"{gate} needs one failing and one passing sentence",
            )

    def test_each_case(self) -> None:
        for gate, verdict, sentence in self.cases:
            with self.subTest(gate=gate, verdict=verdict):
                path = write_temp(".txt", sentence + "\n")
                try:
                    found = gates_for(path)
                finally:
                    path.unlink(missing_ok=True)
                if verdict == "fail":
                    self.assertIn(gate, found, f"{gate} should fail on: {sentence}")
                else:
                    self.assertNotIn(gate, found, f"{gate} should pass on: {sentence}")

    def test_passing_file_is_clean(self) -> None:
        found = check_file(FIXTURES / "passing.txt", strict=True)
        self.assertEqual(found, [], f"passing.txt should be clean, got {found}")

    def test_failing_file_flags_every_listed_gate(self) -> None:
        found = {g for g, _sev, _ln, _sn in check_file(FIXTURES / "failing.txt", strict=True)}
        expected = {g for g, v, _s in self.cases if v == "fail"}
        self.assertTrue(expected <= found, f"missing {expected - found}")


class BibliographySkip(unittest.TestCase):
    def test_tex_body_hype_flags_and_bib_is_skipped(self) -> None:
        hits = check_file(FIXTURES / "hype_bib.tex", strict=True)
        hype = [(ln, sn) for g, _sev, ln, sn in hits if g == "HYPE"]
        self.assertEqual(len(hype), 1, hype)
        self.assertIn("research landscape", hype[0][1])
        self.assertNotIn("tonal space", hype[0][1])

    def test_tex_bib_only_landscape_is_clean_for_hype(self) -> None:
        hits = check_file(FIXTURES / "hype_bib_pass.tex", strict=True)
        self.assertEqual([g for g, *_ in hits if g == "HYPE"], [])

    def test_markdown_references_are_skipped(self) -> None:
        hits = check_file(FIXTURES / "hype_refs.md", strict=True)
        hype = [(ln, sn) for g, _sev, ln, sn in hits if g == "HYPE"]
        self.assertEqual(len(hype), 1, hype)
        self.assertIn("research landscape", hype[0][1])
        self.assertNotIn("tonal space", hype[0][1])

    def test_markdown_references_only_landscape_is_clean_for_hype(self) -> None:
        hits = check_file(FIXTURES / "hype_refs_pass.md", strict=True)
        self.assertEqual([g for g, *_ in hits if g == "HYPE"], [])

    def test_tex_references_subsection_is_skipped(self) -> None:
        hits = check_file(FIXTURES / "hype_tex_section.tex", strict=True)
        hype = [(ln, sn) for g, _sev, ln, sn in hits if g == "HYPE"]
        self.assertEqual(len(hype), 1, hype)
        self.assertIn("research landscape", hype[0][1])
        self.assertNotIn("tonal space", hype[0][1])

    def test_tex_references_subsection_only_landscape_is_clean_for_hype(self) -> None:
        hits = check_file(FIXTURES / "hype_tex_section_pass.tex", strict=True)
        self.assertEqual([g for g, *_ in hits if g == "HYPE"], [])


class RangeFix(unittest.TestCase):
    def test_fix_rewrites_to_en_dash_percent(self) -> None:
        text = "Accuracy sat in the 60 to 70% band and the 80 to 90 percent band.\n"
        fixed, n = apply_range_fixes(text)
        self.assertEqual(n, 2)
        self.assertEqual(
            fixed,
            "Accuracy sat in the 60\u201370% band and the 80\u201390% band.\n",
        )
        self.assertIsNone(RANGE_FIX.search(fixed))
        path = write_temp(".txt", fixed)
        try:
            found = gates_for(path)
        finally:
            path.unlink(missing_ok=True)
        self.assertNotIn("RANGE", found)
        self.assertNotIn("G2", found)


if __name__ == "__main__":
    unittest.main(verbosity=2)
