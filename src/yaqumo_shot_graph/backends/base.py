"""Backend ABC + BackendCommand + BackendRegistry.

"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any

from yaqumo_shot_graph.ir.nodes import IRNode
from yaqumo_shot_graph.ir.types import DeviceClass, LatencyProfile


@dataclass(frozen=True)
class BackendCommand:
    """Opaque backend-specific command payload emitted by the compiler.

    ``op`` is the backend's vocabulary; ``payload`` holds structured arguments;
    ``source_node`` traces back to the IR node that generated this command.
    """

    backend_id: str
    op: str
    payload: dict[str, Any] = field(default_factory=dict)
    source_node: str = ""


class Backend(ABC):
    """Abstract backend. Declares supported DeviceClass(es) and emits commands.

    Concrete subclasses must set ``backend_id`` and ``supported_device_classes``
    class attributes (or instance attributes in ``__init__``).
    """

    backend_id: str
    supported_device_classes: frozenset[DeviceClass]

    @abstractmethod
    def emit(self, node: IRNode) -> Iterable[BackendCommand]:
        """Translate a single IR node to zero or more backend commands.

        Raise ``ValueError`` if the node is not supported.
        """

    def validate_support(self, node: IRNode) -> bool:
        """True iff this backend handles the node's device class."""
        return node.device_class in self.supported_device_classes

    @abstractmethod
    def latency_profile(self) -> LatencyProfile:
        """Backend's latency contribution. Consumed by sim.latency_budget."""


class BackendRegistry:
    """DeviceClass → Backend lookup. Populated at application bootstrap."""

    def __init__(self) -> None:
        self._by_device: dict[DeviceClass, Backend] = {}
        self._by_id: dict[str, Backend] = {}

    def register(self, backend: Backend) -> None:
        if backend.backend_id in self._by_id:
            raise ValueError(f"duplicate backend_id: {backend.backend_id!r}")
        for device_class in backend.supported_device_classes:
            if device_class in self._by_device:
                raise ValueError(
                    f"device class {device_class.value!r} already registered by "
                    f"{self._by_device[device_class].backend_id!r}"
                )
            self._by_device[device_class] = backend
        self._by_id[backend.backend_id] = backend

    def for_device(self, device_class: DeviceClass) -> Backend:
        if device_class not in self._by_device:
            raise KeyError(
                f"no backend registered for device class {device_class.value!r}"
            )
        return self._by_device[device_class]

    def by_id(self, backend_id: str) -> Backend:
        if backend_id not in self._by_id:
            raise KeyError(f"no backend with id {backend_id!r}")
        return self._by_id[backend_id]

    def __len__(self) -> int:
        return len(self._by_id)

    def __iter__(self) -> Iterator[Backend]:
        return iter(self._by_id.values())

    def __contains__(self, item: object) -> bool:
        if isinstance(item, DeviceClass):
            return item in self._by_device
        if isinstance(item, str):
            return item in self._by_id
        return False
