"""IR -> Pasqal Pulser Sequence export (M5b).

This is a read-only export layer, not a Yaqumo runtime. Pulser is Pasqal's
cloud SDK for neutral-atom QPUs -- useful as an export format to prove IR
translatability, but the real Yaqumo runtime lives closer to NI-DAQ / AD9910.

not a backend) and PLAN.md non-goals.
"""
from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Any

from yaqumo_shot_graph.ir.nodes import (
    GateBlock,
    LoadAtoms,
    OpticalDelay,
)

if TYPE_CHECKING:
    from yaqumo_shot_graph.ir.graph import ShotGraph

logger = logging.getLogger(__name__)

_DEFAULT_GATE_DURATION_NS: int = 100
_DEFAULT_GATE_AMPLITUDE: float = 10.0
_DEFAULT_GATE_DETUNING: float = 0.0
_DEFAULT_GATE_PHASE: float = 0.0

_RYDBERG_CHANNEL_NAME: str = "rydberg_global"
_RYDBERG_CHANNEL_ID: str = "rydberg_global"


def to_pulser_sequence(graph: "ShotGraph") -> Any:
    """Translate a ShotGraph into a pulser.Sequence (read-only export).

    Raises:
        ImportError: if the optional pulser package is not installed.
        ValueError: if the graph has no LoadAtoms node.
    """
    try:
        import pulser
        from pulser.devices import DigitalAnalogDevice
    except ImportError as exc:
        raise ImportError(
            "Pulser export requires `pip install pulser`"
        ) from exc

    load_nodes: list[LoadAtoms] = [n for n in graph.nodes() if isinstance(n, LoadAtoms)]
    if not load_nodes:
        raise ValueError("ShotGraph has no LoadAtoms node; cannot build Pulser Register")

    atom_count: int = load_nodes[0].count
    rows, cols = _square_ish_layout(atom_count)
    spacing: float = float(DigitalAnalogDevice.min_atom_distance)
    register = pulser.Register.rectangle(rows, cols, spacing=spacing, prefix="q")

    seq = pulser.Sequence(register, DigitalAnalogDevice)

    channel_declared: bool = False

    for node in graph.nodes():
        if isinstance(node, LoadAtoms):
            continue

        if isinstance(node, GateBlock):
            if not channel_declared:
                seq.declare_channel(_RYDBERG_CHANNEL_NAME, _RYDBERG_CHANNEL_ID)
                channel_declared = True
            pulse = pulser.Pulse.ConstantPulse(
                _DEFAULT_GATE_DURATION_NS,
                _DEFAULT_GATE_AMPLITUDE,
                _DEFAULT_GATE_DETUNING,
                _DEFAULT_GATE_PHASE,
            )
            seq.add(pulse, _RYDBERG_CHANNEL_NAME)
            continue

        if isinstance(node, OpticalDelay):
            if not channel_declared:
                seq.declare_channel(_RYDBERG_CHANNEL_NAME, _RYDBERG_CHANNEL_ID)
                channel_declared = True
            delay_ns: int = max(1, int(node.stage_settle_ms * 1_000_000))
            seq.delay(delay_ns, _RYDBERG_CHANNEL_NAME)
            continue

        logger.debug(
            "pulser export: skipping node %r (%s) -- not representable in Pulser",
            node.name,
            type(node).__name__,
        )

    return seq


def _square_ish_layout(count: int) -> tuple[int, int]:
    """Pick (rows, cols) such that rows*cols >= count, square-ish."""
    if count <= 0:
        raise ValueError(f"atom count must be positive, got {count}")
    rows: int = max(1, int(math.isqrt(count)))
    cols: int = math.ceil(count / rows)
    return rows, cols


__all__ = ["to_pulser_sequence"]
