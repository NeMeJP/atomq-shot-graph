"""Tests for SLMBackend (M3d)."""
from __future__ import annotations

import numpy as np
import pytest

from yaqumo_shot_graph.backends.slm_mock import SLMBackend
from yaqumo_shot_graph.ir.nodes import AcquireEMCCD, CalibrationStep
from yaqumo_shot_graph.ir.types import DeviceClass


def test_default_resolution_and_frame_rate() -> None:
    bk = SLMBackend()
    assert bk._resolution == (1272, 1024)
    assert bk._frame_rate_hz == 60.0


def test_validate_support_slm_only() -> None:
    bk = SLMBackend()
    cal = CalibrationStep(
        name="cal", routine="slm_flat", device_class=DeviceClass.SLM, reference_standard="ref", acceptance_criterion="ok",
    )
    acquire = AcquireEMCCD(name="img", exposure_ms=5.0)
    assert bk.validate_support(cal)
    assert not bk.validate_support(acquire)


def test_emit_calibration_uploads_phase_mask() -> None:
    bk = SLMBackend()
    cal = CalibrationStep(
        name="cal", routine="slm_flat", device_class=DeviceClass.SLM, reference_standard="ref", acceptance_criterion="ok",
    )
    cmds = list(bk.emit(cal))
    assert len(cmds) == 1
    cmd = cmds[0]
    assert cmd.op == "upload_phase_mask"
    assert cmd.payload["routine"] == "slm_flat"
    assert cmd.payload["resolution"] == (1272, 1024)
    assert cmd.source_node == "cal"


def test_emit_rejects_non_slm_routine() -> None:
    bk = SLMBackend()
    cal = CalibrationStep(
        name="cal", routine="other_cal", device_class=DeviceClass.SLM, reference_standard="ref", acceptance_criterion="ok",
    )
    with pytest.raises(ValueError, match="slm_"):
        list(bk.emit(cal))


def test_latency_profile_one_frame() -> None:
    bk = SLMBackend(frame_rate_hz=60.0)
    prof = bk.latency_profile()
    assert prof.feedback_ms == pytest.approx(1000.0 / 60.0, rel=1e-6)


def test_gerchberg_saxton_returns_complex_phase() -> None:
    bk = SLMBackend()
    target = np.ones((8, 8))
    out = bk.gerchberg_saxton_step(target, iterations=2)
    assert out.shape == target.shape
    assert np.issubdtype(out.dtype, np.floating) or np.issubdtype(
        out.dtype, np.complexfloating
    )
