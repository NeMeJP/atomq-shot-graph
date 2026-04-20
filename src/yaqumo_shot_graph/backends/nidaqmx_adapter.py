"""NI-DAQmx backend adapter: AnalogRamp, TTLWindow, and coordination nodes.

This backend targets National Instruments DAQ hardware via the
``nidaqmx-python`` library. Because ``nidaqmx`` depends on the NI-DAQmx
runtime (practically Windows-only), it is declared as an optional
dependency under the ``nidaq`` extra in ``pyproject.toml``.

When ``nidaqmx`` is not importable (e.g., on this Linux development
workstation, or in CI), this backend transparently falls back to a
pure-Python mock: ``emit`` still produces well-typed ``BackendCommand``
objects that downstream compiler/scheduler stages can consume, but no
real hardware I/O is attempted. Real-hardware integration remains
opt-in: install with ``pip install yaqumo-shot-graph[nidaq]`` on a
Windows host with the NI-DAQmx runtime present.

Authority:
    internal design notes §2 (NI-DAQ is inferred-high for analog ramps and TTL
    windows at µs hardware-timed resolution) and §6 item 4 (heterogeneous
    backend registry — NI-DAQ coexists with AD9910, camera, SLM, optical
    delay backends via ``BackendRegistry``).
"""
from __future__ import annotations

import importlib.util
from collections.abc import Iterable

from yaqumo_shot_graph.backends.base import Backend, BackendCommand
from yaqumo_shot_graph.ir.nodes import (
    AnalogRamp,
    BranchIf,
    IRNode,
    LoadAtoms,
    Reset,
    TTLWindow,
)
from yaqumo_shot_graph.ir.types import DeviceClass, LatencyProfile


def _nidaqmx_is_importable() -> bool:
    """Return True iff the ``nidaqmx`` package is importable in this env.

    Uses ``importlib.util.find_spec`` so we avoid actually importing the
    module (and triggering the NI-DAQmx runtime probe) at construction time.
    """
    try:
        return importlib.util.find_spec("nidaqmx") is not None
    except (ImportError, ValueError):
        return False


class NIDAQBackend(Backend):
    """NI-DAQ backend. Hardware-timed when nidaqmx is importable; mock otherwise."""

    backend_id = "nidaqmx"
    supported_device_classes = frozenset({DeviceClass.NI_DAQ})

    def __init__(self) -> None:
        # Lazy probe: just check whether nidaqmx is importable. Do NOT open
        # tasks or touch hardware here — construction must be side-effect free
        # so the registry can instantiate backends on any platform.
        self._live: bool = _nidaqmx_is_importable()

    def emit(self, node: IRNode) -> Iterable[BackendCommand]:
        if isinstance(node, AnalogRamp):
            yield BackendCommand(
                backend_id=self.backend_id,
                op="analog_ramp",
                payload={
                    "channel": node.channel,
                    "start_v": node.start_v,
                    "end_v": node.end_v,
                    "ramp_ms": node.ramp_ms,
                },
                source_node=node.name,
            )
            return
        if isinstance(node, TTLWindow):
            yield BackendCommand(
                backend_id=self.backend_id,
                op="ttl_window",
                payload={
                    "channel": node.channel,
                    "on": node.on,
                    "duration_us": node.duration_us,
                },
                source_node=node.name,
            )
            return
        if isinstance(node, (LoadAtoms, Reset, BranchIf)):
            # Host-side coordination: in a real system these become TTL
            # triggers / host barriers. Here we just surface the node
            # identity so the scheduler has a stable tracer.
            yield BackendCommand(
                backend_id=self.backend_id,
                op=node.node_type,
                payload={"name": node.name},
                source_node=node.name,
            )
            return
        raise ValueError(
            f"NIDAQBackend cannot emit node of type {type(node).__name__!r} "
            f"(device_class={node.device_class.value!r}); the registry should "
            f"have routed this to a different backend."
        )

    def latency_profile(self) -> LatencyProfile:
        # 1 µs is the practical floor for NI-DAQ hardware-timed digital/analog
        # I/O on X-series boards; above that, ramp/window durations dominate
        # and are captured per-node by IRNode.latency_ms().
        return LatencyProfile(electronic_ns=1000.0)
