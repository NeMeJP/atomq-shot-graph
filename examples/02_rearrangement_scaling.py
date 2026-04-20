# %% [markdown]
# # Rearrangement planner scaling — Hungarian vs √N
#
# Companion to `01_dual_isotope_feedback.py`. Shows how path-planning cost
# scales with array size for two planners used in neutral-atom
# rearrangement feedback loops:
#
# - **`hungarian`** — classical assignment, O(N²). Correct but collapses at
#   large N.
# - **`sqrt_t`** — O(√N)-ish planner family (Kim/Endres-style). The
#   production answer for 10³–10⁴-site arrays.
#
# path of the neutral-atom shot cycle).

# %%
from __future__ import annotations

from yaqumo_shot_graph.sim.feedback import (
    FeedbackStageReport,
    simulate_feedback_loop,
)

# %% [markdown]
# ## Scan


# %%
SCAN_SIZES: tuple[int, ...] = (10, 50, 100, 500, 1000, 5000)


def run_scan(
    sizes: tuple[int, ...] = SCAN_SIZES,
    fill_fraction: float = 0.6,
    rng_seed: int = 42,
) -> list[tuple[int, FeedbackStageReport, FeedbackStageReport]]:
    """Return [(n, hungarian_report, sqrt_t_report), ...] for each size."""
    rows: list[tuple[int, FeedbackStageReport, FeedbackStageReport]] = []
    for n in sizes:
        hung = simulate_feedback_loop(
            n_sites=n,
            fill_fraction=fill_fraction,
            rng_seed=rng_seed,
            algorithm="hungarian",
        )
        sqrt_t = simulate_feedback_loop(
            n_sites=n,
            fill_fraction=fill_fraction,
            rng_seed=rng_seed,
            algorithm="sqrt_t",
        )
        rows.append((n, hung, sqrt_t))
    return rows


def print_scan_table(
    rows: list[tuple[int, FeedbackStageReport, FeedbackStageReport]],
) -> None:
    header = f"{'n_sites':>8} | {'hungarian_ms':>14} | {'sqrt_t_ms':>12}"
    sep = f"{'-' * 8}-+-{'-' * 14}-+-{'-' * 12}"
    print(header)
    print(sep)
    for n, hung, sqrt_t in rows:
        print(
            f"{n:>8} | {hung.path_planning_ms:>14.3f} | "
            f"{sqrt_t.path_planning_ms:>12.3f}"
        )


# %% [markdown]
# ## Why Hungarian is impractical at large N
#
# Hungarian assignment is O(N³) in the worst case and O(N²) with modern
# refinements. At N = 5000 sites the planner alone is >1 s per shot, which
# kills the rearrangement loop before you even add image acquisition,
# classification, and AOD updates. Production stacks use greedy √N-style
# planners (Kim/Endres-family) that trade optimality for tractable latency
# — correct-enough paths at sub-millisecond cost, 10⁴ sites in reach.


# %%
def main() -> None:
    rows = run_scan()
    print_scan_table(rows)


if __name__ == "__main__":
    main()
