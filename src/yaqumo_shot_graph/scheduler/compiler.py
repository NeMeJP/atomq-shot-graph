"""M2 compiler: ShotGraph to per-backend command streams.

Walks IR in topological order, dispatches each node to the backend registered
for its DeviceClass, groups resulting BackendCommand objects by backend_id
preserving emission order.

Stub backends: default_registry() returns a BackendRegistry populated with
one stub backend per DeviceClass. These stubs exist so the M6 demo notebook
and the M4 latency-budget sim can execute end-to-end without waiting on the
concrete M3b-e adapters (NI-DAQ, AD9910, camera/SLM, optical delay,
Arduino lock). Each stub emits a single opaque BackendCommand per node that
echoes the node name and timing domain -- enough for traceability and
stream-grouping tests, but nothing physics-real. Replace with concrete
backends as M3b-e land.
"""
from __future__ import annotations

from collections.abc import Iterable

from yaqumo_shot_graph.backends.base import (
    Backend,
    BackendCommand,
    BackendRegistry,
)
from yaqumo_shot_graph.ir.graph import ShotGraph
from yaqumo_shot_graph.ir.nodes import IRNode
from yaqumo_shot_graph.ir.types import DeviceClass, LatencyProfile


class _StubBackend(Backend):
    """Minimal backend that emits a traceable no-op command per node.

    Used only by default_registry() to keep downstream milestones (M4 sim,
    M6 demo) unblocked while the concrete backends are under construction.
    """

    def __init__(
        self,
        backend_id: str,
        device_classes: frozenset[DeviceClass],
    ) -> None:
        self.backend_id = backend_id
        self.supported_device_classes = device_classes

    def emit(self, node: IRNode) -> Iterable[BackendCommand]:
        if not self.validate_support(node):
            msg = (
                f"backend {self.backend_id!r} does not support device class "
                f"{node.device_class.value!r}"
            )
            raise ValueError(msg)
        op = getattr(node, "node_type", type(node).__name__)
        payload = {
            "name": node.name,
            "timing_domain": node.timing_domain.value,
        }
        yield BackendCommand(
            backend_id=self.backend_id,
            op=op,
            payload=payload,
            source_node=node.name,
        )

    def latency_profile(self) -> LatencyProfile:
        # Stubs contribute no latency -- sim.latency_budget (M4) uses IR
        # node latencies directly until real backends provide profiles.
        return LatencyProfile()


_STUB_BACKEND_IDS: dict[DeviceClass, str] = {
    DeviceClass.NI_DAQ: "nidaqmx",
    DeviceClass.AD9910: "ad9910",
    DeviceClass.CAMERA: "camera",
    DeviceClass.SLM: "slm",
    DeviceClass.OPTICAL_DELAY: "optical_delay",
    DeviceClass.ARDUINO_LOCK: "arduino_lock",
    DeviceClass.FPGA_CTRL: "fpga_ctrl",
}


def default_registry() -> BackendRegistry:
    """Return a registry with one stub backend per DeviceClass.

    Each stub owns exactly one device class so M3b-e can swap in concrete
    backends one at a time without touching the others.
    """
    registry = BackendRegistry()
    for device_class, backend_id in _STUB_BACKEND_IDS.items():
        registry.register(
            _StubBackend(backend_id, frozenset({device_class}))
        )
    return registry


def compile_graph(
    graph: ShotGraph,
    registry: BackendRegistry | None = None,
) -> dict[str, list[BackendCommand]]:
    """Compile a shot graph into per-backend command streams.

    Parameters
    ----------
    graph:
        A validated ShotGraph. Nodes are iterated in topological order.
    registry:
        Backend registry mapping DeviceClass to Backend. Defaults to
        default_registry() (stub backends covering all device classes).

    Returns
    -------
    dict[str, list[BackendCommand]]
        Mapping from backend_id to commands in emission order. Only
        backends that actually emitted commands appear as keys.

    Raises
    ------
    ValueError
        If a node device_class has no registered backend.
    """
    if registry is None:
        registry = default_registry()

    streams: dict[str, list[BackendCommand]] = {}
    for node in graph.nodes():
        try:
            backend = registry.for_device(node.device_class)
        except KeyError as exc:
            msg = (
                f"no backend registered for device class "
                f"{node.device_class.value!r} (required by node {node.name!r})"
            )
            raise ValueError(msg) from exc
        for cmd in backend.emit(node):
            streams.setdefault(cmd.backend_id, []).append(cmd)
    return streams


__all__ = ["compile_graph", "default_registry"]
