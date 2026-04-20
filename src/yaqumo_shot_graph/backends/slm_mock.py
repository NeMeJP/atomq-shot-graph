"""SLM mock (Hamamatsu X15213-style phase-only LCOS).

One-frame-period upload latency at configurable frame rate. Ships a
pedagogical Gerchberg-Saxton stub; real-lab GS is GPU-accelerated on full
1272x1024 frames and is out of scope for this mock.

"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import numpy.typing as npt

from yaqumo_shot_graph.backends.base import Backend, BackendCommand
from yaqumo_shot_graph.ir.nodes import CalibrationStep, IRNode
from yaqumo_shot_graph.ir.types import DeviceClass, LatencyProfile


class SLMBackend(Backend):
    """Hamamatsu X15213-class phase-only LCOS SLM mock."""

    backend_id = "slm_hamamatsu"
    supported_device_classes = frozenset({DeviceClass.SLM})

    def __init__(
        self,
        resolution: tuple[int, int] = (1272, 1024),
        frame_rate_hz: float = 60.0,
    ) -> None:
        if frame_rate_hz <= 0:
            raise ValueError("frame_rate_hz must be positive")
        self._resolution = resolution
        self._frame_rate_hz = frame_rate_hz

    def emit(self, node: IRNode) -> Iterable[BackendCommand]:
        if not isinstance(node, CalibrationStep):
            raise ValueError(
                f"{type(self).__name__} only emits for CalibrationStep, "
                f"got {type(node).__name__}"
            )
        if not node.routine.startswith("slm_"):
            raise ValueError(
                f"SLM routine must start with slm_; got {node.routine!r}"
            )
        return [
            BackendCommand(
                backend_id=self.backend_id,
                op="upload_phase_mask",
                payload={
                    "routine": node.routine,
                    "resolution": self._resolution,
                },
                source_node=node.name,
            )
        ]

    def latency_profile(self) -> LatencyProfile:
        return LatencyProfile(feedback_ms=1000.0 / self._frame_rate_hz)

    def gerchberg_saxton_step(
        self,
        target_intensity: npt.NDArray[Any],
        iterations: int = 1,
    ) -> npt.NDArray[Any]:
        """Illustrative Gerchberg-Saxton phase-retrieval stub.

        Tiny FFT-based GS pass. NOT a real solver: real-lab GS runs on GPUs
        with amplitude constraints, source-plane apodization, and
        convergence monitoring over hundreds of iterations. Stub only.
        """
        if target_intensity.ndim == 0:
            raise ValueError("target_intensity must be at least 1-D")
        if iterations < 1:
            raise ValueError("iterations must be >= 1")

        target_amp = np.sqrt(np.asarray(target_intensity, dtype=float))
        field: npt.NDArray[Any] = target_amp.astype(np.complex128)
        for _ in range(iterations):
            if field.ndim == 2:
                far = np.fft.fft2(field)
            else:
                far = np.fft.fft(field)
            # Far-field: enforce target amplitude, keep only the projected phase.
            far_phase = target_amp * np.exp(1j * np.angle(far))
            if field.ndim == 2:
                near = np.fft.ifft2(far_phase)
            else:
                near = np.fft.ifft(far_phase)
            near_phase = np.angle(near)
            # Phase-only Hamamatsu X15213-style LCOS: uniform illumination
            # constraint in the near field (amplitude cannot be modulated).
            # Target amplitude is enforced only in the far field.
            field = np.exp(1j * near_phase).astype(np.complex128)
        return np.asarray(np.angle(field), dtype=float)
