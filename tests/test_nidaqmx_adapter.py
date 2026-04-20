"""M3b exit criteria: NI-DAQ backend adapter.

The adapter must construct on any platform (nidaqmx may not be importable
on Linux / CI), emit correctly-typed BackendCommand objects for the NI-DAQ
device class, and reject nodes that belong to other backends.
"""
from __future__ import annotations

import pytest

from yaqumo_shot_graph.backends.nidaqmx_adapter import NIDAQBackend
from yaqumo_shot_graph.ir.nodes import (
    AcquireEMCCD,
    AnalogRamp,
    BranchIf,
    GateBlock,
    LoadAtoms,
    Reset,
    TTLWindow,
)
from yaqumo_shot_graph.ir.types import AtomSpecies, DeviceClass, LatencyProfile


def test_construct_without_nidaqmx_installed() -> None:
    # nidaqmx is Windows-only and not installed in this venv, so _live is False.
    bk = NIDAQBackend()
    assert bk._live is False
    assert bk.backend_id == "nidaqmx"
    assert bk.supported_device_classes == frozenset({DeviceClass.NI_DAQ})


def test_validate_support_ni_daq_only() -> None:
    bk = NIDAQBackend()
    ramp = AnalogRamp(
        name="ramp", channel="ao0", start_v=0.0, end_v=1.0, ramp_ms=1.0,
    )
    cam = AcquireEMCCD(name="img", exposure_ms=5.0)
    assert bk.validate_support(ramp) is True
    assert bk.validate_support(cam) is False


def test_emit_analog_ramp() -> None:
    bk = NIDAQBackend()
    ramp = AnalogRamp(
        name="r0", channel="ao1", start_v=-0.5, end_v=2.5, ramp_ms=10.0,
    )
    cmds = list(bk.emit(ramp))
    assert len(cmds) == 1
    cmd = cmds[0]
    assert cmd.backend_id == "nidaqmx"
    assert cmd.op == "analog_ramp"
    assert cmd.source_node == "r0"
    assert cmd.payload == {
        "channel": "ao1",
        "start_v": -0.5,
        "end_v": 2.5,
        "ramp_ms": 10.0,
    }


def test_emit_ttl_window() -> None:
    bk = NIDAQBackend()
    ttl = TTLWindow(name="t0", channel="do3", on=True, duration_us=50.0)
    cmds = list(bk.emit(ttl))
    assert len(cmds) == 1
    cmd = cmds[0]
    assert cmd.backend_id == "nidaqmx"
    assert cmd.op == "ttl_window"
    assert cmd.source_node == "t0"
    assert cmd.payload == {"channel": "do3", "on": True, "duration_us": 50.0}


def test_emit_raises_on_unsupported_node() -> None:
    bk = NIDAQBackend()
    # GateBlock is AD9910 territory, not NI-DAQ.
    gate = GateBlock(name="g", species=AtomSpecies.YB171, gate_name="Rx")
    with pytest.raises(ValueError, match="cannot emit"):
        list(bk.emit(gate))


def test_latency_profile_returns_electronic_ns() -> None:
    bk = NIDAQBackend()
    prof = bk.latency_profile()
    assert isinstance(prof, LatencyProfile)
    assert prof.electronic_ns > 0
    # 1 µs floor — see hardware-timed I/O comment in the adapter.
    assert prof.electronic_ns == pytest.approx(1000.0)


def test_emit_load_atoms_and_reset_and_branchif() -> None:
    bk = NIDAQBackend()
    load = LoadAtoms(name="load0", species=AtomSpecies.YB171, count=100)
    reset = Reset(name="reset0", species=AtomSpecies.YB171)
    branch = BranchIf(
        name="br0",
        condition="m==1",
        true_branch=("g1",),
        false_branch=("g2",),
    )

    load_cmds = list(bk.emit(load))
    reset_cmds = list(bk.emit(reset))
    branch_cmds = list(bk.emit(branch))

    assert len(load_cmds) == 1
    assert load_cmds[0].op == "load_atoms"
    assert load_cmds[0].payload == {"name": "load0"}
    assert load_cmds[0].source_node == "load0"
    assert load_cmds[0].backend_id == "nidaqmx"

    assert len(reset_cmds) == 1
    assert reset_cmds[0].op == "reset"
    assert reset_cmds[0].payload == {"name": "reset0"}

    assert len(branch_cmds) == 1
    assert branch_cmds[0].op == "branch_if"
    assert branch_cmds[0].payload == {"name": "br0"}
