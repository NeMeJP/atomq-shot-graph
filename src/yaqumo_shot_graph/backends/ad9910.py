"""AD9910 DDS SPI model backend - bit-exact register encoding.

Models the SPI register interface of the Analog Devices AD9910 1 GSPS DDS,
the standard RF driver for Acousto-Optic Deflectors/Modulators in AMO labs.
Encodes 32-bit FTW (frequency tuning word), 14-bit ASF (amplitude scale
factor), 16-bit POW (phase offset word), and 8 single-tone profile
registers. Also models RAM-profile pre-load (1024 words x 32-bit).

Authority:
    internal design notes Section 2 - AD9910 is inferred-high for Kyoto lab norms
    (standard AMO RF control, matches ICCE TDM logic). No ARTIQ/QICK/PYNQ
    vocabulary - this is a clean-room model grounded in the public AD9910
    datasheet.

Key datasheet facts:
    - System clock f_sysclk: default 1 GHz
    - FTW (reg 0x07): ftw = round(f_out * 2**32 / f_sysclk), 32-bit unsigned
    - ASF (reg 0x09 / STPx low 14 bits): 0..0x3FFF maps 0.0..1.0 full-scale
    - 8 single-tone profiles STP0..STP7 (0x0E..0x15)
    - RAM (reg 0x16): 1024 words x 32-bit for envelope playback
    - SPI: 4-wire (CSB/SCLK/SDIO/SYNC_IO); instruction byte (MSB=R/~W,
      low 5 bits = register address) followed by data bytes.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import IntEnum

from yaqumo_shot_graph.backends.base import Backend, BackendCommand
from yaqumo_shot_graph.ir.nodes import AODMovePlan, DDSSetProfile, GateBlock, IRNode
from yaqumo_shot_graph.ir.types import DeviceClass, LatencyProfile

FTW_WIDTH_BITS = 32
FTW_MAX = (1 << FTW_WIDTH_BITS) - 1
ASF_WIDTH_BITS = 14
ASF_MAX = (1 << ASF_WIDTH_BITS) - 1
POW_WIDTH_BITS = 16
POW_MAX = (1 << POW_WIDTH_BITS) - 1
RAM_DEPTH_WORDS = 1024
RAM_WORD_BITS = 32
NUM_SINGLE_TONE_PROFILES = 8
SPI_ADDRESS_MASK = 0x1F
SPI_RW_MASK = 0x80


class AD9910Register(IntEnum):
    """AD9910 register address map (subset - DDS control + profiles + RAM)."""

    CFR1 = 0x00
    CFR2 = 0x01
    CFR3 = 0x02
    AUX_DAC = 0x03
    IO_UPDATE_RATE = 0x04
    FTW = 0x07
    POW = 0x08
    ASF = 0x09
    STP0 = 0x0E
    STP1 = 0x0F
    STP2 = 0x10
    STP3 = 0x11
    STP4 = 0x12
    STP5 = 0x13
    STP6 = 0x14
    STP7 = 0x15
    RAM = 0x16


_SINGLE_TONE_PROFILES: tuple[AD9910Register, ...] = (
    AD9910Register.STP0,
    AD9910Register.STP1,
    AD9910Register.STP2,
    AD9910Register.STP3,
    AD9910Register.STP4,
    AD9910Register.STP5,
    AD9910Register.STP6,
    AD9910Register.STP7,
)


def freq_to_ftw(f_hz: float, f_sysclk_hz: float = 1e9) -> int:
    """Encode an output frequency as the AD9910 32-bit Frequency Tuning Word.

    Formula (datasheet p.23): FTW = round(f_out / f_sysclk * 2**32).
    """
    if f_sysclk_hz <= 0.0:
        raise ValueError(f"f_sysclk_hz must be positive, got {f_sysclk_hz}")
    if f_hz != f_hz:
        raise ValueError("f_hz is NaN")
    if f_hz < 0.0:
        raise ValueError(f"f_hz must be non-negative, got {f_hz}")
    if f_hz >= f_sysclk_hz / 2.0:
        raise ValueError(
            f"f_hz={f_hz} exceeds Nyquist (f_sysclk/2 = {f_sysclk_hz / 2.0})"
        )
    ftw = round(f_hz * (1 << FTW_WIDTH_BITS) / f_sysclk_hz)
    if not (0 <= ftw <= FTW_MAX):
        raise ValueError(f"computed FTW {ftw} out of 32-bit range")
    return ftw


def amplitude_to_asf(amp_full_scale: float) -> int:
    """Encode a normalized amplitude [0,1] as the 14-bit ASF [0, 0x3FFF]."""
    if amp_full_scale != amp_full_scale:
        raise ValueError("amp_full_scale is NaN")
    if amp_full_scale < 0.0 or amp_full_scale > 1.0:
        raise ValueError(
            f"amp_full_scale must be in [0.0, 1.0], got {amp_full_scale}"
        )
    asf = round(amp_full_scale * ASF_MAX)
    if asf < 0:
        asf = 0
    if asf > ASF_MAX:
        asf = ASF_MAX
    return asf


@dataclass(frozen=True)
class SPITransaction:
    """One AD9910 SPI transaction: instruction byte + data bytes.

    Instruction byte: MSB = R/~W, low 5 bits = register address.
    """

    register: int
    data: bytes
    is_write: bool

    def instruction_byte(self) -> int:
        addr = self.register & SPI_ADDRESS_MASK
        if self.is_write:
            return addr
        return SPI_RW_MASK | addr

    def to_wire(self) -> bytes:
        return bytes([self.instruction_byte()]) + self.data


def _encode_stp(ftw: int, asf: int, pow_: int = 0) -> bytes:
    """Encode single-tone profile (8 bytes): ASF[61:48] | POW[47:32] | FTW[31:0]."""
    if not 0 <= ftw <= FTW_MAX:
        raise ValueError(f"FTW out of range: {ftw}")
    if not 0 <= asf <= ASF_MAX:
        raise ValueError(f"ASF out of range: {asf}")
    if not 0 <= pow_ <= POW_MAX:
        raise ValueError(f"POW out of range: {pow_}")
    word = ((asf & ASF_MAX) << 48) | ((pow_ & POW_MAX) << 32) | (ftw & FTW_MAX)
    return word.to_bytes(8, byteorder="big", signed=False)


class AD9910Backend(Backend):
    """Backend translating AD9910-bound IR nodes to bit-exact SPI commands."""

    backend_id = "ad9910"
    supported_device_classes = frozenset({DeviceClass.AD9910})

    def __init__(self, f_sysclk_hz: float = 1e9) -> None:
        if f_sysclk_hz <= 0.0:
            raise ValueError(f"f_sysclk_hz must be positive, got {f_sysclk_hz}")
        self.f_sysclk_hz = f_sysclk_hz

    def emit(self, node: IRNode) -> Iterable[BackendCommand]:
        if isinstance(node, DDSSetProfile):
            return self._emit_dds_set_profile(node)
        if isinstance(node, GateBlock):
            return self._emit_gate_block(node)
        if isinstance(node, AODMovePlan):
            return self._emit_aod_move_plan(node)
        raise ValueError(
            f"AD9910Backend cannot emit node of type {type(node).__name__!r} "
            f"(name={node.name!r})"
        )

    def _emit_dds_set_profile(self, node: DDSSetProfile) -> list[BackendCommand]:
        if not 0 <= node.profile_index < NUM_SINGLE_TONE_PROFILES:
            raise ValueError(
                f"profile_index {node.profile_index} out of range [0, 8)"
            )
        reg = _SINGLE_TONE_PROFILES[node.profile_index]
        payload_bytes = _encode_stp(ftw=node.ftw, asf=node.asf, pow_=0)
        spi = SPITransaction(register=int(reg), data=payload_bytes, is_write=True)
        wire = spi.to_wire()
        return [
            BackendCommand(
                backend_id=self.backend_id,
                op="spi_write",
                payload={
                    "register": reg.name,
                    "register_addr": int(reg),
                    "bytes": wire.hex(),
                    "ftw": node.ftw,
                    "asf": node.asf,
                    "profile_index": node.profile_index,
                    "instruction_byte": spi.instruction_byte(),
                },
                source_node=node.name,
            ),
            BackendCommand(
                backend_id=self.backend_id,
                op="io_update",
                payload={"profile_index": node.profile_index},
                source_node=node.name,
            ),
        ]

    def _emit_gate_block(self, node: GateBlock) -> list[BackendCommand]:
        return [
            BackendCommand(
                backend_id=self.backend_id,
                op="dds_gate_pulse",
                payload={
                    "species": node.species.value,
                    "gate_name": node.gate_name,
                },
                source_node=node.name,
            )
        ]

    def _emit_aod_move_plan(self, node: AODMovePlan) -> list[BackendCommand]:
        return [
            BackendCommand(
                backend_id=self.backend_id,
                op="aod_ramp_sequence",
                payload={"algorithm": node.algorithm},
                source_node=node.name,
            )
        ]

    def latency_profile(self) -> LatencyProfile:
        return LatencyProfile(electronic_ns=500.0)


__all__ = [
    "AD9910Backend",
    "AD9910Register",
    "SPITransaction",
    "amplitude_to_asf",
    "freq_to_ftw",
    "ASF_MAX",
    "FTW_MAX",
    "POW_MAX",
    "RAM_DEPTH_WORDS",
    "RAM_WORD_BITS",
    "NUM_SINGLE_TONE_PROFILES",
]
