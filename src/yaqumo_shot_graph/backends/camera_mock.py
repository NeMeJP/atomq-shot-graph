"""EMCCD camera mock (Andor iXon-897-equivalent).

Models exposure_ms, DMA transfer, per-site thresholding. 10-50 ms total latency.
section 6 item 3 (image-feedback dominates neutral-atom shot-cycle latency).
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import numpy.typing as npt

from yaqumo_shot_graph.backends.base import Backend, BackendCommand
from yaqumo_shot_graph.ir.nodes import (
    AcquireEMCCD,
    ClassifyOccupancy,
    IRNode,
    MeasureAncilla,
)
from yaqumo_shot_graph.ir.types import DeviceClass, LatencyProfile


class EMCCDCameraBackend(Backend):
    """Andor iXon-897-class EMCCD camera mock.

    Emits backend commands for AcquireEMCCD / ClassifyOccupancy / MeasureAncilla.
    Provides a deterministic simulate_frame for downstream sim layers.
    """

    backend_id = "camera_emccd"
    supported_device_classes = frozenset({DeviceClass.CAMERA})

    def __init__(
        self,
        n_sites: int = 100,
        rng_seed: int = 42,
        dark_count_rate: float = 0.02,
        fill_fraction: float = 0.6,
    ) -> None:
        self._n_sites = n_sites
        self._rng_seed = rng_seed
        self._dark_count_rate = dark_count_rate
        self._fill_fraction = fill_fraction
        self._rng = np.random.default_rng(rng_seed)

    def emit(self, node: IRNode) -> Iterable[BackendCommand]:
        if isinstance(node, AcquireEMCCD):
            return [
                BackendCommand(
                    backend_id=self.backend_id,
                    op="capture_frame",
                    payload={
                        "exposure_ms": node.exposure_ms,
                        "dma_overhead_ms": node.dma_overhead_ms,
                        "n_sites": self._n_sites,
                    },
                    source_node=node.name,
                )
            ]
        if isinstance(node, ClassifyOccupancy):
            return [
                BackendCommand(
                    backend_id=self.backend_id,
                    op="threshold",
                    payload={"threshold": node.threshold},
                    source_node=node.name,
                )
            ]
        if isinstance(node, MeasureAncilla):
            return [
                BackendCommand(
                    backend_id=self.backend_id,
                    op="measure",
                    payload={
                        "species": node.species.value,
                    "exposure_ms": node.exposure_ms,
                    "dma_overhead_ms": node.dma_overhead_ms,
                        "output_bit": node.output_bit,
                    },
                    source_node=node.name,
                )
            ]
        raise ValueError(
            f"{type(self).__name__} cannot emit for node type "
            f"{type(node).__name__}"
        )

    def latency_profile(self) -> LatencyProfile:
        return LatencyProfile(feedback_ms=15.0)

    def simulate_frame(self, exposure_ms: float) -> npt.NDArray[Any]:
        """Return (n_sites,) boolean occupancy array (deterministic)."""
        if exposure_ms <= 0:
            raise ValueError("exposure_ms must be positive")
        true_fill = self._rng.random(self._n_sites) < self._fill_fraction
        dark_lambda = self._dark_count_rate * exposure_ms / 1000.0
        dark_counts = self._rng.poisson(lam=dark_lambda, size=self._n_sites)
        return np.asarray(true_fill | (dark_counts > 0), dtype=bool)
