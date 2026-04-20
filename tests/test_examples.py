"""Smoke tests for examples/ scripts.

Guarantees both demo scripts run top-to-bottom on a fresh clone and
produce the key stdout markers a recruiter-facing demo should contain.
The scripts use jupytext percent format and are driven via
``runpy.run_path`` with ``run_name="__main__"`` so the ``if __name__ ==
"__main__"`` guard triggers the full demo.
"""
from __future__ import annotations

import re
import runpy
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = REPO_ROOT / "examples"
EXAMPLE_01 = EXAMPLES / "01_dual_isotope_feedback.py"
EXAMPLE_02 = EXAMPLES / "02_rearrangement_scaling.py"


def _run_as_main(path: Path) -> None:
    """Execute a script as if launched via ``python path``."""
    runpy.run_path(str(path), run_name="__main__")


def test_example_01_imports_and_runs(capsys: pytest.CaptureFixture[str]) -> None:
    """Example 01 executes top-to-bottom without raising."""
    _run_as_main(EXAMPLE_01)
    out = capsys.readouterr().out
    assert out, "example 01 produced no stdout"


def test_example_02_imports_and_runs(capsys: pytest.CaptureFixture[str]) -> None:
    """Example 02 executes top-to-bottom without raising."""
    _run_as_main(EXAMPLE_02)
    out = capsys.readouterr().out
    assert out, "example 02 produced no stdout"


def test_example_01_produces_feedback_table(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Demo headline: latency table must show feedback as the dominant domain."""
    _run_as_main(EXAMPLE_01)
    out = capsys.readouterr().out
    assert "DOMINANT" in out
    # inner-loop table labels feedback explicitly
    assert "feedback" in out.lower()


def test_example_01_produces_openqasm_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Demo must show OpenQASM 3 export as proof of IR translatability."""
    _run_as_main(EXAMPLE_01)
    out = capsys.readouterr().out
    assert "OPENQASM 3.0" in out


def test_example_02_hungarian_slower_at_large_n(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """At N=5000, Hungarian planner must cost more than sqrt_t planner."""
    _run_as_main(EXAMPLE_02)
    out = capsys.readouterr().out
    # Parse the n_sites=5000 row (last row of the scan table)
    row = re.search(
        r"^\s*5000\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*$",
        out,
        flags=re.MULTILINE,
    )
    assert row is not None, f"could not find n=5000 row in output:\n{out}"
    hungarian_ms = float(row.group(1))
    sqrt_t_ms = float(row.group(2))
    assert hungarian_ms > sqrt_t_ms, (
        f"expected hungarian ({hungarian_ms}) > sqrt_t ({sqrt_t_ms}) at N=5000"
    )
