"""Latency-budget bar chart + Hungarian-vs-sqrt_t scaling (imports demo builds)."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import importlib.util
spec = importlib.util.spec_from_file_location(
    "demo", Path(__file__).parent / "01_dual_isotope_feedback.py",
)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)

from yaqumo_shot_graph.ir.types import TimingDomain  # noqa: E402
from yaqumo_shot_graph.sim import latency_budget  # noqa: E402
from yaqumo_shot_graph.sim.feedback import simulate_feedback_loop  # noqa: E402

DOMAIN_COLOR = {
    TimingDomain.ELECTRONIC: "#3b82f6",
    TimingDomain.OPTICAL:    "#10b981",
    TimingDomain.FEEDBACK:   "#ef4444",
}

def plot_latency(path: str) -> None:
    full = latency_budget(demo.build_dual_isotope_graph())
    inner = latency_budget(demo.build_inner_loop_graph())

    domains = list(TimingDomain)
    full_vals = [full.per_domain_ms[d] for d in domains]
    inner_vals = [inner.per_domain_ms[d] for d in domains]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    labels = [d.value for d in domains]
    colors = [DOMAIN_COLOR[d] for d in domains]

    for ax, vals, title in [
        (axes[0], full_vals, f"Full shot (with 200 ms MOT load)\nTotal: {full.total_ms:.2f} ms"),
        (axes[1], inner_vals, f"Inner gate-path-shot loop (no MOT)\nTotal: {inner.total_ms:.2f} ms"),
    ]:
        bars = ax.bar(labels, vals, color=colors, edgecolor="#111", linewidth=1.2)
        ax.set_ylabel("Latency (ms)")
        ax.set_title(title, fontsize=11, pad=12)
        ax.set_yscale("symlog", linthresh=0.01)
        for bar, v in zip(bars, vals):
            ax.annotate(f"{v:.2f} ms",
                        xy=(bar.get_x() + bar.get_width()/2, v),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=9, fontweight="bold")
        ax.grid(axis="y", alpha=0.3, linestyle="--")

    fig.suptitle("yaqumo-shot-graph: timing-domain budget",
                 fontsize=14, y=1.02, fontweight="bold")
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    print(f"saved: {path}")

def plot_scaling(path: str) -> None:
    Ns = [10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
    hung_ms, sqrt_ms = [], []
    for n in Ns:
        h = simulate_feedback_loop(n_sites=n, fill_fraction=0.6, rng_seed=42, algorithm="hungarian")
        s = simulate_feedback_loop(n_sites=n, fill_fraction=0.6, rng_seed=42, algorithm="sqrt_t")
        hung_ms.append(h.path_planning_ms)
        sqrt_ms.append(s.path_planning_ms)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.loglog(Ns, hung_ms, "o-", color="#ef4444", linewidth=2, markersize=8, label="Hungarian  O(N²)")
    ax.loglog(Ns, sqrt_ms, "o-", color="#10b981", linewidth=2, markersize=8, label="√N planner  (Kim/Endres family)")
    ax.axhline(50, color="#64748b", linestyle=":", linewidth=1.5, alpha=0.7)
    ax.text(Ns[-1]*0.9, 55, "50 ms nominal coherence budget", ha="right", fontsize=9, color="#64748b")

    ax.set_xlabel("Array size  N (sites)", fontsize=11)
    ax.set_ylabel("Path-planning latency  (ms)", fontsize=11)
    ax.set_title("Rearrangement planner scaling\n(image+classify+AOD constant; planning is the knob)",
                 fontsize=13, pad=15)
    ax.legend(loc="upper left", fontsize=10, frameon=True)
    ax.grid(True, which="both", alpha=0.3, linestyle="--")
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    print(f"saved: {path}")

if __name__ == "__main__":
    plot_latency("docs/images/latency_budget.png")
    plot_scaling("docs/images/scaling.png")
