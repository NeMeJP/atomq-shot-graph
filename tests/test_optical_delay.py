"""M3e exit criteria: OpticalDelayBackend stub."""
from __future__ import annotations

import pytest

from yaqumo_shot_graph.backends.optical_delay import OpticalDelayBackend
from yaqumo_shot_graph.ir.nodes import (
    AnalogRamp,
    GateBlock,
    OpticalDelay,
)
from yaqumo_shot_graph.ir.types import AtomSpecies


def test_validate_support_optical_delay_only() -> None:
    bk = OpticalDelayBackend()
    optical = OpticalDelay(name="od", delay_ps=100.0)
    analog = AnalogRamp(
        name="r", channel="ao0", start_v=0.0, end_v=1.0, ramp_ms=1.0,
    )
    assert bk.validate_support(optical)
    assert not bk.validate_support(analog)


def test_emit_move_stage_and_pulse_ready_marker() -> None:
    bk = OpticalDelayBackend()
    node = OpticalDelay(name="od0", delay_ps=250.0, stage_settle_ms=40.0)
    cmds = list(bk.emit(node))
    assert len(cmds) == 2
    ops = [c.op for c in cmds]
    assert ops == ["move_stage", "pulse_ready_marker"]
    assert all(c.source_node == "od0" for c in cmds)
    assert all(c.backend_id == "optical_delay" for c in cmds)
    assert cmds[0].payload == {"delay_ps": 250.0, "stage_settle_ms": 40.0}


def test_emit_pulse_ready_marker_tags_optical_domain() -> None:
    bk = OpticalDelayBackend()
    node = OpticalDelay(name="od1", delay_ps=10.0)
    cmds = list(bk.emit(node))
    marker = cmds[1]
    assert marker.op == "pulse_ready_marker"
    assert marker.payload == {"timing_domain": "optical"}


def test_emit_rejects_out_of_range() -> None:
    bk = OpticalDelayBackend(max_delay_ps=10_000.0)
    node = OpticalDelay(name="od_big", delay_ps=50_000.0)
    with pytest.raises(ValueError, match="out of range"):
        list(bk.emit(node))


def test_emit_rejects_unsupported_node() -> None:
    bk = OpticalDelayBackend()
    gate = GateBlock(name="g", species=AtomSpecies.YB171, gate_name="cz")
    with pytest.raises(ValueError, match="OpticalDelayBackend handles"):
        list(bk.emit(gate))


def test_latency_profile_reports_stage_settle_default() -> None:
    bk = OpticalDelayBackend()
    profile = bk.latency_profile()
    # R2 fix: stage motion attributed to optical_ms, not feedback_ms
    assert profile.optical_ms == 50.0
    assert profile.feedback_ms == 0.0
    assert profile.total_ms() == 50.0


def test_stage_settle_profile_tracks_node() -> None:
    bk = OpticalDelayBackend()
    node = OpticalDelay(name="od", delay_ps=100.0, stage_settle_ms=30.0)
    profile = bk.stage_settle_profile(node)
    assert profile.optical_ms == 30.0


def test_custom_envelope_accepted() -> None:
    bk = OpticalDelayBackend(max_delay_ps=10000.0)
    node = OpticalDelay(name="od_long", delay_ps=5000.0)
    cmds = list(bk.emit(node))
    assert len(cmds) == 2
    assert cmds[0].payload["delay_ps"] == 5000.0
