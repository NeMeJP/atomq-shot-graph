"""Mock closed-loop rearrangement-feedback simulation.

Models the EMCCD -> classify -> path-plan -> AOD-move loop identified in
internal design notes section 6 item 3 as the critical-path bottleneck of
neutral-atom shot cycles. The pedagogical claim embedded here is that
path-planning dominates the loop budget at large N, and the sqrt(N)
planner wins over Hungarian-style O(N^2) assignment for realistic
array sizes (100-1000 traps).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

PathPlanningAlgorithm = Literal["hungarian", "sqrt_t"]

_IMAGE_ACQUISITION_MS = 15.0
_CLASSIFY_MS = 2.0
_HUNGARIAN_COEF = 0.1 / 1000.0
_SQRT_T_COEF = 0.1
_AOD_UPDATE_PER_MOVE_MS = 0.001


@dataclass(frozen=True)
class FeedbackStageReport:
    """Per-stage ms breakdown of one rearrangement feedback loop iteration."""

    n_sites: int
    fill_fraction: float
    algorithm: str
    image_acquisition_ms: float
    classify_ms: float
    path_planning_ms: float
    aod_update_ms: float
    n_moves: int

    @property
    def total_ms(self) -> float:
        return (
            self.image_acquisition_ms
            + self.classify_ms
            + self.path_planning_ms
            + self.aod_update_ms
        )

    def format_table(self) -> str:
        """Pretty 2-column per-stage table."""
        total = self.total_ms
        rows = [
            ("image acquisition (EMCCD)", self.image_acquisition_ms),
            ("classify (thresholding)", self.classify_ms),
            (f"path planning ({self.algorithm})", self.path_planning_ms),
            (f"AOD update ({self.n_moves} moves)", self.aod_update_ms),
        ]
        header = f"{'Feedback stage':<34} | {'ms':>8}"
        sep = f"{'-' * 34}-+-{'-' * 8}"
        lines: list[str] = [header, sep]
        for label, ms in rows:
            lines.append(f"{label:<34} | {ms:>8.3f}")
        lines.append(sep)
        lines.append(f"{'Total feedback loop':<34} | {total:>8.3f}")
        lines.append(
            f"  (n_sites={self.n_sites}, fill={self.fill_fraction:.2f}, "
            f"alg={self.algorithm})"
        )
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.format_table()


def _path_planning_ms(n_sites: int, algorithm: PathPlanningAlgorithm) -> float:
    if algorithm == "hungarian":
        return float(_HUNGARIAN_COEF * float(n_sites) ** 2)
    if algorithm == "sqrt_t":
        return float(_SQRT_T_COEF * float(n_sites) ** 0.5)
    raise ValueError(
        f"unknown path-planning algorithm {algorithm!r}; "
        f"expected 'hungarian' or 'sqrt_t'"
    )


def simulate_feedback_loop(
    n_sites: int,
    fill_fraction: float,
    rng_seed: int,
    algorithm: PathPlanningAlgorithm,
) -> FeedbackStageReport:
    """Simulate one pass of the image -> classify -> plan -> AOD feedback loop."""
    if n_sites < 1:
        raise ValueError(f"n_sites must be >= 1, got {n_sites}")
    if not 0.0 <= fill_fraction <= 1.0:
        raise ValueError(
            f"fill_fraction must be in [0.0, 1.0], got {fill_fraction}"
        )

    rng = np.random.default_rng(rng_seed)
    occupancy = rng.random(n_sites) < fill_fraction
    n_moves = int(np.count_nonzero(~occupancy))

    path_planning_ms = _path_planning_ms(n_sites, algorithm)
    aod_update_ms = _AOD_UPDATE_PER_MOVE_MS * float(n_moves)

    return FeedbackStageReport(
        n_sites=n_sites,
        fill_fraction=fill_fraction,
        algorithm=algorithm,
        image_acquisition_ms=_IMAGE_ACQUISITION_MS,
        classify_ms=_CLASSIFY_MS,
        path_planning_ms=path_planning_ms,
        aod_update_ms=aod_update_ms,
        n_moves=n_moves,
    )


__all__ = [
    "FeedbackStageReport",
    "PathPlanningAlgorithm",
    "simulate_feedback_loop",
]
