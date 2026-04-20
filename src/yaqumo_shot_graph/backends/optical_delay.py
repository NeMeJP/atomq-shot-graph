"""Optical delay stub: non-electronic timing domain.

Represents motorized delay lines + CPA pulse coordination (Ohmori ultrafast).
Also accepts ``GateBlock(gate_mechanism='optical')`` because those gates live
in the optical domain.

Real lab setups use motorized translation stages (Thorlabs, PI, Aerotech)
driven over serial/USB; here we only capture the topology.

Envelope defaults:
  - max_delay_ps = 100_000 (100 ns) covers the ~60 ns coordination gap cited
    in arXiv:1910.05292 Suppl. p. 10 plus typical stage travel.
  - stage_settle_ms = 50 ms tracks typical Thorlabs DDS series settle time.

"""
from __future__ import annotations

from collections.abc import Iterable

from yaqumo_shot_graph.backends.base import Backend, BackendCommand
from yaqumo_shot_graph.ir.nodes import GateBlock, IRNode, OpticalDelay
from yaqumo_shot_graph.ir.types import DeviceClass, LatencyProfile


class OpticalDelayBackend(Backend):
    """Stub backend for the optical timing domain."""

    backend_id = "optical_delay"
    supported_device_classes = frozenset({DeviceClass.OPTICAL_DELAY})

    def __init__(
        self,
        min_delay_ps: float = 0.0,
        max_delay_ps: float = 100_000.0,
        stage_settle_ms_default: float = 50.0,
    ) -> None:
        self.min_delay_ps = min_delay_ps
        self.max_delay_ps = max_delay_ps
        self.stage_settle_ms_default = stage_settle_ms_default

    def emit(self, node: IRNode) -> Iterable[BackendCommand]:
        if isinstance(node, OpticalDelay):
            if not (self.min_delay_ps <= node.delay_ps <= self.max_delay_ps):
                raise ValueError(
                    f"OpticalDelay delay_ps={node.delay_ps} out of range "
                    f"[{self.min_delay_ps}, {self.max_delay_ps}] ps."
                )
            yield BackendCommand(
                backend_id=self.backend_id,
                op="move_stage",
                payload={"delay_ps": node.delay_ps, "stage_settle_ms": node.stage_settle_ms},
                source_node=node.name,
            )
            yield BackendCommand(
                backend_id=self.backend_id,
                op="pulse_ready_marker",
                payload={"timing_domain": "optical"},
                source_node=node.name,
            )
            return

        if isinstance(node, GateBlock) and node.gate_mechanism == "optical":
            yield BackendCommand(
                backend_id=self.backend_id,
                op="optical_gate",
                payload={
                    "gate_name": node.gate_name,
                    "species": node.species.value,
                    "note": "CPA-pulse driven; timing lives outside the electronic sequencer",
                },
                source_node=node.name,
            )
            return

        raise ValueError(
            f"OpticalDelayBackend handles OpticalDelay and GateBlock(gate_mechanism='optical'); "
            f"got {type(node).__name__}"
            + (f"(gate_mechanism={node.gate_mechanism!r})" if isinstance(node, GateBlock) else "")
        )

    def latency_profile(self) -> LatencyProfile:
        """Stage-settle default contributes to the feedback domain.

        Stage motion is classical and slow; the ps-fs optical delay itself
        is a separate contribution. We expose the stage cost (the dominant
        one for the sim layer) so ``sim.latency_budget`` does not lie by
        reporting zero.
        """
        # Stage motion is classical-mechanical but physically OPTICAL-adjacent
        # (positions an optical element). design requirement: attribute to
        # the optical_ms bucket, not feedback_ms.
        return LatencyProfile(optical_ms=self.stage_settle_ms_default)

    def stage_settle_profile(self, node: OpticalDelay) -> LatencyProfile:
        """Node-specific stage settle cost in the optical_ms domain."""
        return LatencyProfile(optical_ms=node.stage_settle_ms)


__all__ = ["OpticalDelayBackend"]
