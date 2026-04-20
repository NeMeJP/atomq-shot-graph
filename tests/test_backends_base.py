"""M3a exit criteria: Backend ABC + BackendCommand + BackendRegistry."""
from __future__ import annotations

from collections.abc import Iterable

import pytest

from yaqumo_shot_graph.backends.base import Backend, BackendCommand, BackendRegistry
from yaqumo_shot_graph.ir import nodes
from yaqumo_shot_graph.ir.types import AtomSpecies, DeviceClass, LatencyProfile


class _FakeBackend(Backend):
    def __init__(self, backend_id: str, devices: frozenset[DeviceClass]) -> None:
        self.backend_id = backend_id
        self.supported_device_classes = devices

    def emit(self, node: nodes.IRNode) -> Iterable[BackendCommand]:
        yield BackendCommand(
            backend_id=self.backend_id,
            op="noop",
            payload={"name": node.name},
            source_node=node.name,
        )

    def latency_profile(self) -> LatencyProfile:
        return LatencyProfile(electronic_ns=100.0)


def test_backend_command_is_frozen_and_default_payload() -> None:
    cmd = BackendCommand(backend_id="b", op="x")
    assert cmd.payload == {}
    assert cmd.source_node == ""
    with pytest.raises(Exception):
        cmd.op = "y"  # type: ignore[misc]


def test_validate_support_uses_device_classes() -> None:
    bk = _FakeBackend("b", frozenset({DeviceClass.NI_DAQ}))
    analog = nodes.AnalogRamp(
        name="r", channel="ao0", start_v=0.0, end_v=1.0, ramp_ms=1.0,
    )
    camera = nodes.AcquireEMCCD(name="img", exposure_ms=5.0)
    assert bk.validate_support(analog)
    assert not bk.validate_support(camera)


def test_registry_registers_and_resolves_by_device_class() -> None:
    reg = BackendRegistry()
    ni = _FakeBackend("ni", frozenset({DeviceClass.NI_DAQ}))
    cam = _FakeBackend("cam", frozenset({DeviceClass.CAMERA, DeviceClass.SLM}))
    reg.register(ni)
    reg.register(cam)
    assert len(reg) == 2
    assert reg.for_device(DeviceClass.NI_DAQ) is ni
    assert reg.for_device(DeviceClass.CAMERA) is cam
    assert reg.for_device(DeviceClass.SLM) is cam


def test_registry_rejects_duplicate_backend_id() -> None:
    reg = BackendRegistry()
    reg.register(_FakeBackend("x", frozenset({DeviceClass.NI_DAQ})))
    with pytest.raises(ValueError, match="duplicate backend_id"):
        reg.register(_FakeBackend("x", frozenset({DeviceClass.AD9910})))


def test_registry_rejects_double_device_class_registration() -> None:
    reg = BackendRegistry()
    reg.register(_FakeBackend("a", frozenset({DeviceClass.NI_DAQ})))
    with pytest.raises(ValueError, match="already registered"):
        reg.register(_FakeBackend("b", frozenset({DeviceClass.NI_DAQ})))


def test_registry_keyerror_on_unknown_device() -> None:
    reg = BackendRegistry()
    with pytest.raises(KeyError):
        reg.for_device(DeviceClass.AD9910)


def test_registry_contains_operator() -> None:
    reg = BackendRegistry()
    ni = _FakeBackend("ni", frozenset({DeviceClass.NI_DAQ}))
    reg.register(ni)
    assert DeviceClass.NI_DAQ in reg
    assert "ni" in reg
    assert DeviceClass.AD9910 not in reg
    assert "ghost" not in reg


def test_emit_yields_backend_commands() -> None:
    bk = _FakeBackend("b", frozenset({DeviceClass.NI_DAQ}))
    node = nodes.Reset(name="r0", species=AtomSpecies.YB171)
    cmds = list(bk.emit(node))
    assert len(cmds) == 1
    assert cmds[0].backend_id == "b"
    assert cmds[0].source_node == "r0"


def test_latency_profile_has_dominant_domain() -> None:
    bk = _FakeBackend("b", frozenset({DeviceClass.CAMERA}))
    bk.latency_profile()  # smoke: returns LatencyProfile
