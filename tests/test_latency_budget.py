"""Tests for M4 sim.latency_budget."""
from __future__ import annotations

import pytest

from yaqumo_shot_graph import ShotGraph, nodes
from yaqumo_shot_graph.ir.types import AtomSpecies, TimingDomain
from yaqumo_shot_graph.scheduler.compiler import compile_graph, default_registry
from yaqumo_shot_graph.sim.latency_budget import (
    LatencyBudget,
    latency_budget,
    latency_budget_from_streams,
)

from tests.test_ir import build_dual_isotope_demo


def _dual_isotope_without_load() -> ShotGraph:
    """Rebuild the dual-isotope demo with the 200 ms MOT load stripped.

    LoadAtoms is realistic but is MOT setup, not the gate-path-shot inner
    loop the demo is selling. Verify FEEDBACK still dominates ELECTRONIC
    for the remaining 8 nodes.
    """
    g = ShotGraph()
    g.add(nodes.AcquireEMCCD(name="image_1", exposure_ms=5.0))
    g.add(nodes.ClassifyOccupancy(name="classify_1"))
    g.add(nodes.AODMovePlan(name="rearrange", algorithm="sqrt_t"))
    g.add(nodes.DDSSetProfile(
        name="aod_update", ftw=0x40000000, asf=0x2000, profile_index=0,
    ))
    g.add(nodes.GateBlock(
        name="rydberg_gate", species=AtomSpecies.YB171, gate_name="cz",
    ))
    g.add(nodes.MeasureAncilla(name="mcm", species=AtomSpecies.YB174, output_bit="m"))
    g.add(nodes.BranchIf(
        name="feedforward",
        condition="m == 1",
        true_branch=("correction",),
    ))
    g.add(nodes.GateBlock(
        name="correction", species=AtomSpecies.YB171, gate_name="x_correction",
    ))
    return g


def test_dual_isotope_feedback_dominates_electronic_minus_load() -> None:
    """Headline property: after MOT load, feedback-domain cost >> electronic."""
    g = _dual_isotope_without_load()
    budget = latency_budget(g)

    feedback_ms = budget.per_domain_ms[TimingDomain.FEEDBACK]
    electronic_ms = budget.per_domain_ms[TimingDomain.ELECTRONIC]

    assert feedback_ms > electronic_ms, (
        f"expected FEEDBACK ({feedback_ms:.3f} ms) > ELECTRONIC "
        f"({electronic_ms:.3f} ms) after excluding LoadAtoms"
    )
    assert budget.dominant_domain is TimingDomain.FEEDBACK


def test_latency_budget_has_all_three_domains() -> None:
    g = build_dual_isotope_demo()
    budget = latency_budget(g)
    assert set(budget.per_domain_ms.keys()) == set(TimingDomain)


def test_per_node_ms_is_topologically_ordered() -> None:
    g = build_dual_isotope_demo()
    budget = latency_budget(g)
    expected_names = [n.name for n in g.nodes()]
    actual_names = [row[0] for row in budget.per_node_ms]
    assert actual_names == expected_names


def test_total_ms_equals_sum_of_domains() -> None:
    g = build_dual_isotope_demo()
    budget = latency_budget(g)
    assert budget.total_ms == pytest.approx(sum(budget.per_domain_ms.values()))
    assert budget.total_ms == pytest.approx(
        sum(ms for _, _, ms in budget.per_node_ms)
    )


def test_dominant_domain_for_feedback_heavy_graph() -> None:
    """Camera + classify + MCM only -> dominant is FEEDBACK."""
    g = ShotGraph()
    g.add(nodes.AcquireEMCCD(name="img", exposure_ms=10.0))
    g.add(nodes.ClassifyOccupancy(name="cls"))
    g.add(nodes.MeasureAncilla(name="mcm"))

    budget = latency_budget(g)
    assert budget.dominant_domain is TimingDomain.FEEDBACK
    assert budget.per_domain_ms[TimingDomain.ELECTRONIC] == pytest.approx(0.0)
    assert budget.per_domain_ms[TimingDomain.FEEDBACK] > 0.0


def test_format_table_contains_dominant_marker() -> None:
    g = build_dual_isotope_demo()
    budget = latency_budget(g)
    table = budget.format_table()
    assert "DOMINANT" in table
    marked_rows = [line for line in table.splitlines() if "DOMINANT" in line]
    assert len(marked_rows) == 1
    assert budget.dominant_domain.value in marked_rows[0]


def test_format_table_is_deterministic() -> None:
    g = build_dual_isotope_demo()
    budget = latency_budget(g)
    assert budget.format_table() == budget.format_table()
    assert str(budget) == budget.format_table()


def test_latency_budget_from_streams_matches_backend_ids() -> None:
    g = build_dual_isotope_demo()
    registry = default_registry()
    streams = compile_graph(g, registry=registry)
    view = latency_budget_from_streams(streams, registry)

    assert set(view.per_backend_command_count.keys()) == set(streams.keys())
    assert set(view.per_backend_ms.keys()) == set(streams.keys())
    assert set(view.per_backend_profile.keys()) == set(streams.keys())
    for backend_id, commands in streams.items():
        assert view.per_backend_command_count[backend_id] == len(commands)
    # Stub backends declare zero latency, so total_ms is zero under the stubs.
    assert view.total_ms == pytest.approx(0.0)


def test_latency_budget_is_immutable() -> None:
    g = build_dual_isotope_demo()
    budget = latency_budget(g)
    with pytest.raises(Exception):
        budget.per_domain_ms = {}  # type: ignore[misc]
    assert isinstance(budget, LatencyBudget)


def test_empty_graph_has_zero_total() -> None:
    g = ShotGraph()
    budget = latency_budget(g)
    assert budget.total_ms == 0.0
    assert budget.per_node_ms == ()
    assert set(budget.per_domain_ms.keys()) == set(TimingDomain)
