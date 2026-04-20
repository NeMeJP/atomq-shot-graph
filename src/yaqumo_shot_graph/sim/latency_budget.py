"""Latency-budget aggregation over a compiled shot-graph.

non-collapsible), section 6 item 3 (image-feedback dominates the neutral-atom
shot cycle). The demo notebook uses this module to print the 3-column table
that proves the thesis: FEEDBACK is the critical path, not RF pulse timing.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from yaqumo_shot_graph.backends.base import BackendCommand, BackendRegistry
from yaqumo_shot_graph.ir.graph import ShotGraph
from yaqumo_shot_graph.ir.types import LatencyProfile, TimingDomain


@dataclass(frozen=True)
class LatencyBudget:
    """Per-domain and per-node latency breakdown of a ShotGraph.

    Produced by ``latency_budget``. Consumed by the M6 demo notebook to
    print the 3-column headline table (Domain | Total ms | % of shot).
    """

    per_domain_ms: dict[TimingDomain, float]
    per_node_ms: tuple[tuple[str, TimingDomain, float], ...]

    @property
    def total_ms(self) -> float:
        return sum(self.per_domain_ms.values())

    @property
    def dominant_domain(self) -> TimingDomain:
        return max(
            self.per_domain_ms.items(),
            key=lambda kv: (kv[1], kv[0].value),
        )[0]

    def format_table(self) -> str:
        """Pretty 3-column table suitable for print() in the demo notebook."""
        total = self.total_ms
        dominant = self.dominant_domain if total > 0 else None

        header = f"{'Timing domain':<16} | {'Total ms':>10} | {'% shot':>9}"
        sep = f"{'-' * 16}-+-{'-' * 10}-+-{'-' * 9}"
        lines: list[str] = [header, sep]

        for domain in (
            TimingDomain.ELECTRONIC,
            TimingDomain.OPTICAL,
            TimingDomain.FEEDBACK,
        ):
            ms = self.per_domain_ms.get(domain, 0.0)
            pct = (100.0 * ms / total) if total > 0 else 0.0
            row = f"{domain.value:<16} | {ms:>10.2f} | {pct:>8.1f}%"
            if domain is dominant and total > 0:
                if domain is TimingDomain.FEEDBACK:
                    row = f"{row}  <- DOMINANT (classical feedback loop)"
                else:
                    row = f"{row}  <- DOMINANT"
            lines.append(row)

        lines.append(sep)
        footer_pct = 100.0 if total > 0 else 0.0
        lines.append(
            f"{'Total shot cycle':<16} | {total:>10.2f} | {footer_pct:>8.1f}%"
        )
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.format_table()


@dataclass(frozen=True)
class BackendLatencyView:
    """Per-backend command count + declared-latency view."""

    per_backend_ms: dict[str, float] = field(default_factory=dict)
    per_backend_command_count: dict[str, int] = field(default_factory=dict)
    per_backend_profile: dict[str, LatencyProfile] = field(default_factory=dict)

    @property
    def total_ms(self) -> float:
        return sum(self.per_backend_ms.values())


def latency_budget(graph: ShotGraph) -> LatencyBudget:
    """Aggregate per-timing-domain latency over a ShotGraph in topo order."""
    per_domain: dict[TimingDomain, float] = {domain: 0.0 for domain in TimingDomain}
    per_node: list[tuple[str, TimingDomain, float]] = []

    for node in graph.nodes():
        ms = float(node.latency_ms())
        per_domain[node.timing_domain] += ms
        per_node.append((node.name, node.timing_domain, ms))

    return LatencyBudget(
        per_domain_ms=per_domain,
        per_node_ms=tuple(per_node),
    )


def latency_budget_from_streams(
    streams: dict[str, list[BackendCommand]],
    registry: BackendRegistry,
) -> BackendLatencyView:
    """Aggregate per-backend command counts and declared latency profiles."""
    per_backend_ms: dict[str, float] = {}
    per_backend_count: dict[str, int] = {}
    per_backend_profile: dict[str, LatencyProfile] = {}

    for backend_id, commands in streams.items():
        n = len(commands)
        per_backend_count[backend_id] = n
        try:
            backend = registry.by_id(backend_id)
        except KeyError:
            per_backend_ms[backend_id] = 0.0
            per_backend_profile[backend_id] = LatencyProfile()
            continue
        profile = backend.latency_profile()
        per_backend_profile[backend_id] = profile
        per_backend_ms[backend_id] = profile.total_ms() * n

    return BackendLatencyView(
        per_backend_ms=per_backend_ms,
        per_backend_command_count=per_backend_count,
        per_backend_profile=per_backend_profile,
    )


__all__ = [
    "LatencyBudget",
    "BackendLatencyView",
    "latency_budget",
    "latency_budget_from_streams",
]
