"""Tests for M4 sim.feedback (rearrangement-loop simulation)."""
from __future__ import annotations

import pytest

from yaqumo_shot_graph.sim.feedback import (
    FeedbackStageReport,
    simulate_feedback_loop,
)


def test_deterministic_with_seed() -> None:
    a = simulate_feedback_loop(
        n_sites=200, fill_fraction=0.6, rng_seed=42, algorithm="sqrt_t",
    )
    b = simulate_feedback_loop(
        n_sites=200, fill_fraction=0.6, rng_seed=42, algorithm="sqrt_t",
    )
    assert a == b
    c = simulate_feedback_loop(
        n_sites=200, fill_fraction=0.6, rng_seed=43, algorithm="sqrt_t",
    )
    assert isinstance(c, FeedbackStageReport)


def test_hungarian_grows_faster_than_sqrt_t_for_large_n() -> None:
    """Pedagogical claim: at N=1000, hungarian planner >> sqrt_t planner."""
    n = 1000
    hungarian = simulate_feedback_loop(
        n_sites=n, fill_fraction=0.5, rng_seed=0, algorithm="hungarian",
    )
    sqrt_t = simulate_feedback_loop(
        n_sites=n, fill_fraction=0.5, rng_seed=0, algorithm="sqrt_t",
    )
    assert hungarian.path_planning_ms > 10.0 * sqrt_t.path_planning_ms
    assert hungarian.total_ms > sqrt_t.total_ms


def test_n_moves_reflects_vacancies() -> None:
    """At fill 0.5, roughly half the sites are vacant -> n_moves ~= n/2."""
    n = 2000
    report = simulate_feedback_loop(
        n_sites=n, fill_fraction=0.5, rng_seed=123, algorithm="sqrt_t",
    )
    expected = n * 0.5
    assert report.n_moves == pytest.approx(expected, rel=0.05)


def test_total_ms_components_sum() -> None:
    report = simulate_feedback_loop(
        n_sites=100, fill_fraction=0.7, rng_seed=7, algorithm="sqrt_t",
    )
    expected = (
        report.image_acquisition_ms
        + report.classify_ms
        + report.path_planning_ms
        + report.aod_update_ms
    )
    assert report.total_ms == pytest.approx(expected)


def test_format_table_has_all_stages() -> None:
    report = simulate_feedback_loop(
        n_sites=50, fill_fraction=0.6, rng_seed=1, algorithm="sqrt_t",
    )
    table = report.format_table()
    lowered = table.lower()
    assert "image" in lowered
    assert "classify" in lowered
    assert "plan" in lowered
    assert "aod" in lowered
    assert report.algorithm in table
    assert str(report) == report.format_table()
    assert report.format_table() == report.format_table()


def test_invalid_algorithm_raises() -> None:
    with pytest.raises(ValueError, match="unknown path-planning algorithm"):
        simulate_feedback_loop(
            n_sites=10,
            fill_fraction=0.5,
            rng_seed=0,
            algorithm="greedy",  # type: ignore[arg-type]
        )


def test_invalid_n_sites_raises() -> None:
    with pytest.raises(ValueError, match="n_sites"):
        simulate_feedback_loop(
            n_sites=0, fill_fraction=0.5, rng_seed=0, algorithm="sqrt_t",
        )


def test_invalid_fill_fraction_raises() -> None:
    with pytest.raises(ValueError, match="fill_fraction"):
        simulate_feedback_loop(
            n_sites=10, fill_fraction=1.5, rng_seed=0, algorithm="sqrt_t",
        )


def test_fill_fraction_zero_yields_all_moves() -> None:
    n = 64
    report = simulate_feedback_loop(
        n_sites=n, fill_fraction=0.0, rng_seed=5, algorithm="sqrt_t",
    )
    assert report.n_moves == n


def test_fill_fraction_one_yields_zero_moves() -> None:
    report = simulate_feedback_loop(
        n_sites=64, fill_fraction=1.0, rng_seed=5, algorithm="sqrt_t",
    )
    assert report.n_moves == 0
    assert report.aod_update_ms == pytest.approx(0.0)
