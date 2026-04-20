"""Tests for EMCCDCameraBackend (M3d)."""
from __future__ import annotations

import numpy as np
import pytest

from yaqumo_shot_graph.backends.camera_mock import EMCCDCameraBackend
from yaqumo_shot_graph.ir.nodes import (
    AcquireEMCCD,
    AnalogRamp,
    ClassifyOccupancy,
    GateBlock,
    MeasureAncilla,
)
from yaqumo_shot_graph.ir.types import AtomSpecies, LatencyProfile


def test_construct_deterministic_with_seed() -> None:
    a = EMCCDCameraBackend(n_sites=100, rng_seed=123)
    b = EMCCDCameraBackend(n_sites=100, rng_seed=123)
    frame_a = a.simulate_frame(exposure_ms=10.0)
    frame_b = b.simulate_frame(exposure_ms=10.0)
    assert np.array_equal(frame_a, frame_b)


def test_validate_support_camera_only() -> None:
    bk = EMCCDCameraBackend()
    acquire = AcquireEMCCD(name="img", exposure_ms=5.0)
    ramp = AnalogRamp(
        name="r", channel="ao0", start_v=0.0, end_v=1.0, ramp_ms=1.0,
    )
    assert bk.validate_support(acquire)
    assert not bk.validate_support(ramp)


def test_emit_acquire_emccd() -> None:
    bk = EMCCDCameraBackend(n_sites=256)
    node = AcquireEMCCD(name="img", exposure_ms=5.0, dma_overhead_ms=3.0)
    cmds = list(bk.emit(node))
    assert len(cmds) == 1
    cmd = cmds[0]
    assert cmd.op == "capture_frame"
    assert cmd.payload["exposure_ms"] == 5.0
    assert cmd.payload["n_sites"] == 256
    assert cmd.source_node == "img"


def test_emit_classify_occupancy() -> None:
    bk = EMCCDCameraBackend()
    node = ClassifyOccupancy(name="cls", threshold=0.7)
    cmds = list(bk.emit(node))
    assert len(cmds) == 1
    assert cmds[0].op == "threshold"
    assert cmds[0].payload["threshold"] == 0.7


def test_emit_measure_ancilla() -> None:
    bk = EMCCDCameraBackend()
    node = MeasureAncilla(name="m0", species=AtomSpecies.YB174, output_bit="b0")
    cmds = list(bk.emit(node))
    assert len(cmds) == 1
    cmd = cmds[0]
    assert cmd.op == "measure"
    assert cmd.payload["species"] == "Yb174"
    assert cmd.payload["output_bit"] == "b0"


def test_simulate_frame_shape_and_fill() -> None:
    n = 100
    fill = 0.6
    bk = EMCCDCameraBackend(n_sites=n, rng_seed=7, fill_fraction=fill)
    frame = bk.simulate_frame(exposure_ms=5.0)
    assert frame.shape == (n,)
    assert frame.dtype == bool
    mean_fill = float(frame.mean())
    assert abs(mean_fill - fill) <= 0.2 * fill + 0.05


def test_latency_profile_feedback() -> None:
    bk = EMCCDCameraBackend()
    prof = bk.latency_profile()
    assert isinstance(prof, LatencyProfile)
    assert prof.feedback_ms >= 10.0


def test_emit_rejects_unsupported() -> None:
    bk = EMCCDCameraBackend()
    gate = GateBlock(name="g", species=AtomSpecies.YB171, gate_name="Rx")
    with pytest.raises(ValueError):
        list(bk.emit(gate))
