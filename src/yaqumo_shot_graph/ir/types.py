"""Core enums and type registries for the shot-graph IR.

first-class) and §6 item 4 (heterogeneous backend registry).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TimingDomain(str, Enum):
    """Three timing domains — non-collapsible."""

    ELECTRONIC = "electronic"  # NI-DAQ, AD9910, TTL — ns-µs
    OPTICAL = "optical"        # CPA pulses, delay lines, mechanical stages
    FEEDBACK = "feedback"      # camera → classify → branch — ms, classical


class AtomSpecies(str, Enum):
    """Yb isotopes used in the Kyoto + IMS Okazaki ecosystem."""

    YB171 = "Yb171"  # I=1/2 qubit
    YB174 = "Yb174"  # I=0 bosonic ancilla
    YB173 = "Yb173"  # I=5/2 fermionic (arXiv:2602.22883)


class DeviceClass(str, Enum):
    """Backend device categories."""

    NI_DAQ = "ni_daq"
    AD9910 = "ad9910"
    CAMERA = "camera"
    SLM = "slm"
    OPTICAL_DELAY = "optical_delay"
    ARDUINO_LOCK = "arduino_lock"
    FPGA_CTRL = "fpga_ctrl"


@dataclass(frozen=True)
class LatencyProfile:
    """Per-domain latency contribution.

    Four separate buckets so the sim layer can attribute cost to the
    physically correct domain (board review 2026-04-20):

    - ``electronic_ns`` — ns-µs electronic precision (AD9910 SPI, TTL)
    - ``optical_ps``    — ps-fs CPA pulse precision
    - ``optical_ms``    — classical-mechanical optical cost (delay-stage motion)
    - ``feedback_ms``   — camera exposure / DMA / classification / planning
    """

    electronic_ns: float = 0.0
    optical_ps: float = 0.0
    optical_ms: float = 0.0
    feedback_ms: float = 0.0

    def total_ms(self) -> float:
        return (
            self.electronic_ns / 1e6
            + self.optical_ps / 1e9
            + self.optical_ms
            + self.feedback_ms
        )

    def dominant_domain(self) -> TimingDomain:
        optical_total_ms = self.optical_ps / 1e9 + self.optical_ms
        contributions = {
            TimingDomain.ELECTRONIC: self.electronic_ns / 1e6,
            TimingDomain.OPTICAL: optical_total_ms,
            TimingDomain.FEEDBACK: self.feedback_ms,
        }
        return max(contributions, key=lambda k: contributions[k])
