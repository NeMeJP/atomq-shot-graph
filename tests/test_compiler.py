"""M2 exit criterion: dual-isotope graph compiles into >=4 backend streams."""
from __future__ import annotations

from collections.abc import Iterable

import pytest

from yaqumo_shot_graph import ShotGraph, nodes
from yaqumo_shot_graph.backends.base import (
    Backend,
    BackendCommand,
    BackendRegistry,
)
from yaqumo_shot_graph.ir.nodes import IRNode
from yaqumo_shot_graph.ir.types import AtomSpecies, DeviceClass, LatencyProfile
from yaqumo_shot_graph.scheduler.compiler import (
    _STUB_BACKEND_IDS,
    _StubBackend,
    compile_graph,
    default_registry,
)


def build_dual_isotope_demo() -> ShotGraph:
    """Mirror of tests/test_ir.py::build_dual_isotope_demo -- same 9 nodes."""
    g = ShotGraph()
    g.add(nodes.LoadAtoms(name="load", species=AtomSpecies.YB171, count=100))
    g.add(nodes.AcquireEMCCD(name="image_1", exposure_ms=5.0))
    g.add(nodes.ClassifyOccupancy(name="classify_1"))
    g.add(nodes.AODMovePlan(name="rearrange", algorithm="sqrt_t"))
    g.add(nodes.DDSSetProfile(
        name="aod_update", ftw=0x40000000, asf=0x2000, profile_index=0,
    ))
    g.add(nodes.GateBlock(
        name="rydberg_gate", species=AtomSpecies.YB171, gate_name="cz",
    ))
    g.add(nodes.MeasureAncilla(
        name="mcm", species=AtomSpecies.YB174, output_bit="m",
    ))
    g.add(nodes.BranchIf(
        name="feedforward",
        condition="m == 1",
        true_branch=("correction",),
    ))
    g.add(nodes.GateBlock(
        name="correction", species=AtomSpecies.YB171, gate_name="x_correction",
    ))
    return g


def test_default_registry_covers_all_device_classes() -> None:
    reg = default_registry()
    for dc in DeviceClass:
        assert dc in reg, f"default registry missing backend for {dc.value}"


def test_compile_dual_isotope_demo_groups_by_backend() -> None:
    g = build_dual_isotope_demo()
    streams = compile_graph(g)
    exercised = {node.device_class for node in g.nodes()}
    expected_ids = {default_registry().for_device(dc).backend_id for dc in exercised}
    assert set(streams.keys()) == expected_ids


def test_compile_reaches_four_streams_with_optical_delay() -> None:
    """Augment the demo so compile output hits >= 4 distinct streams."""
    g = build_dual_isotope_demo()
    g.add(nodes.OpticalDelay(name="delay_line", delay_ps=120.0))
    streams = compile_graph(g)
    assert len(streams) >= 4
    assert "nidaqmx" in streams
    assert "camera" in streams
    assert "ad9910" in streams
    assert "optical_delay" in streams


def test_every_command_traces_to_source_node() -> None:
    g = build_dual_isotope_demo()
    streams = compile_graph(g)
    node_names = {n.name for n in g.nodes()}
    total = 0
    for cmds in streams.values():
        for cmd in cmds:
            assert cmd.source_node, "command missing source_node traceability"
            assert cmd.source_node in node_names
            total += 1
    assert total == len(list(build_dual_isotope_demo().nodes()))


def test_topological_order_preserved_within_each_stream() -> None:
    g = build_dual_isotope_demo()
    topo_index = {n.name: i for i, n in enumerate(g.nodes())}
    streams = compile_graph(g)
    for backend_id, cmds in streams.items():
        indices = [topo_index[c.source_node] for c in cmds]
        assert indices == sorted(indices), (
            f"stream {backend_id!r} not in topological order: {indices}"
        )


def test_custom_backend_overrides_default() -> None:
    """Registering a custom backend for a device class must win over stubs."""

    class _LoggingNIDAQ(Backend):
        def __init__(self) -> None:
            self.backend_id = "ni_daq_custom"
            self.supported_device_classes = frozenset({DeviceClass.NI_DAQ})

        def emit(self, node: IRNode) -> Iterable[BackendCommand]:
            yield BackendCommand(
                backend_id=self.backend_id,
                op="custom",
                payload={"marker": "overridden", "name": node.name},
                source_node=node.name,
            )

        def latency_profile(self) -> LatencyProfile:
            return LatencyProfile(electronic_ns=42.0)

    registry = BackendRegistry()
    registry.register(_LoggingNIDAQ())
    # Fill remaining device classes so the demo can compile end-to-end.
    for dc, bid in _STUB_BACKEND_IDS.items():
        if dc is DeviceClass.NI_DAQ:
            continue
        registry.register(_StubBackend(bid, frozenset({dc})))

    g = build_dual_isotope_demo()
    streams = compile_graph(g, registry)
    assert "ni_daq_custom" in streams
    assert "nidaqmx" not in streams
    for cmd in streams["ni_daq_custom"]:
        assert cmd.op == "custom"
        assert cmd.payload["marker"] == "overridden"


def test_missing_backend_raises_value_error() -> None:
    """An empty registry must cause compile_graph to raise ValueError."""
    g = build_dual_isotope_demo()
    empty = BackendRegistry()
    with pytest.raises(ValueError, match="no backend registered for device class"):
        compile_graph(g, empty)


def test_compile_with_explicit_default_registry_matches_implicit() -> None:
    g = build_dual_isotope_demo()
    implicit = compile_graph(g)
    explicit = compile_graph(g, default_registry())
    assert set(implicit.keys()) == set(explicit.keys())
    for key in implicit:
        assert len(implicit[key]) == len(explicit[key])


def test_command_payload_carries_timing_domain() -> None:
    g = build_dual_isotope_demo()
    streams = compile_graph(g)
    seen_domains: set[str] = set()
    for cmds in streams.values():
        for cmd in cmds:
            assert "timing_domain" in cmd.payload
            seen_domains.add(cmd.payload["timing_domain"])
    # Demo exercises both electronic and feedback timing domains.
    assert {"electronic", "feedback"} <= seen_domains
