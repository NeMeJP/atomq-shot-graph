"""M3c exit criteria: AD9910 backend + bit-exact FTW/ASF encoding + SPI model."""
from __future__ import annotations

import pytest

from yaqumo_shot_graph.backends.ad9910 import (
    ASF_MAX,
    AD9910Backend,
    AD9910Register,
    SPITransaction,
    amplitude_to_asf,
    freq_to_ftw,
)
from yaqumo_shot_graph.backends.base import BackendCommand
from yaqumo_shot_graph.ir import nodes
from yaqumo_shot_graph.ir.types import AtomSpecies, LatencyProfile


def test_freq_to_ftw_known_value() -> None:
    expected = round(100e6 * (1 << 32) / 1e9)
    assert freq_to_ftw(100e6, 1e9) == expected
    assert freq_to_ftw(0.0, 1e9) == 0
    near_nyquist = 0.4 * 1e9
    ftw = freq_to_ftw(near_nyquist, 1e9)
    assert 0 <= ftw < (1 << 32)
    assert freq_to_ftw(250e6, 1e9) == 0x40000000


def test_freq_to_ftw_range_enforced() -> None:
    with pytest.raises(ValueError):
        freq_to_ftw(-1.0, 1e9)
    with pytest.raises(ValueError):
        freq_to_ftw(600e6, 1e9)
    with pytest.raises(ValueError):
        freq_to_ftw(500e6, 1e9)
    with pytest.raises(ValueError):
        freq_to_ftw(100e6, 0.0)


def test_amplitude_to_asf_extremes() -> None:
    assert amplitude_to_asf(0.0) == 0
    assert amplitude_to_asf(1.0) == ASF_MAX
    assert amplitude_to_asf(1.0) == 0x3FFF
    mid = amplitude_to_asf(0.5)
    assert abs(mid - 0x2000) <= 1
    with pytest.raises(ValueError):
        amplitude_to_asf(-0.1)
    with pytest.raises(ValueError):
        amplitude_to_asf(1.5)


def test_spi_transaction_to_wire_instruction_byte() -> None:
    write = SPITransaction(
        register=int(AD9910Register.FTW),
        data=bytes([0, 1, 2, 3]),
        is_write=True,
    )
    wire = write.to_wire()
    assert wire[0] & 0x80 == 0
    assert wire[0] & 0x1F == 0x07
    read = SPITransaction(
        register=int(AD9910Register.ASF),
        data=bytes(),
        is_write=False,
    )
    assert read.instruction_byte() & 0x80 == 0x80
    assert read.instruction_byte() & 0x1F == 0x09


def test_spi_transaction_payload_roundtrip() -> None:
    data = bytes(range(8))
    spi = SPITransaction(
        register=int(AD9910Register.STP3),
        data=data,
        is_write=True,
    )
    wire = spi.to_wire()
    assert wire[0] == (int(AD9910Register.STP3) & 0x1F)
    assert wire[1:] == data
    assert len(wire) == 9


def _make_backend() -> AD9910Backend:
    return AD9910Backend(f_sysclk_hz=1e9)


def test_backend_emit_dds_set_profile() -> None:
    bk = _make_backend()
    node = nodes.DDSSetProfile(
        name="dds0",
        ftw=freq_to_ftw(80e6, 1e9),
        asf=amplitude_to_asf(0.75),
        profile_index=3,
    )
    cmds = list(bk.emit(node))
    assert len(cmds) >= 1
    spi_cmds = [c for c in cmds if c.op == "spi_write"]
    assert len(spi_cmds) == 1
    payload = spi_cmds[0].payload
    assert 0 <= payload["ftw"] < (1 << 32)
    assert 0 <= payload["asf"] <= 0x3FFF
    assert payload["profile_index"] == 3
    assert "bytes" in payload
    assert payload["register"] == "STP3"
    assert all(isinstance(c, BackendCommand) for c in cmds)


def test_backend_emit_gate_block() -> None:
    bk = _make_backend()
    gate = nodes.GateBlock(
        name="cz0",
        species=AtomSpecies.YB171,
        gate_name="CZ",
    )
    cmds = list(bk.emit(gate))
    assert len(cmds) == 1
    assert cmds[0].op == "dds_gate_pulse"
    assert cmds[0].payload["species"] == AtomSpecies.YB171.value
    assert cmds[0].payload["gate_name"] == "CZ"


def test_backend_emit_aod_move_plan() -> None:
    bk = _make_backend()
    plan = nodes.AODMovePlan(name="rearr", algorithm="hungarian")
    cmds = list(bk.emit(plan))
    assert len(cmds) == 1
    assert cmds[0].op == "aod_ramp_sequence"
    assert cmds[0].payload["algorithm"] == "hungarian"


def test_backend_rejects_unsupported_node() -> None:
    bk = _make_backend()
    cam = nodes.AcquireEMCCD(name="img", exposure_ms=5.0)
    with pytest.raises(ValueError):
        list(bk.emit(cam))


def test_backend_latency_profile_electronic() -> None:
    bk = _make_backend()
    prof = bk.latency_profile()
    assert isinstance(prof, LatencyProfile)
    assert prof.electronic_ns > 0.0
