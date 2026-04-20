"""Typed IR nodes — pydantic v2 BaseModel. See PLAN.md for milestone map."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from yaqumo_shot_graph.ir.types import AtomSpecies, DeviceClass, TimingDomain


class IRNode(BaseModel):
    """Abstract base for all shot-graph nodes."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    device_class: DeviceClass
    timing_domain: TimingDomain

    def latency_ms(self) -> float:
        return 0.0


class LoadAtoms(IRNode):
    """Single MOT cycle; may co-load a second species in the same window.

    dual-isotope co-loading in PRX 2024
    happens in ONE MOT cycle (~200 ms), not two sequential loads. Use
    ``ancilla_species`` to mark the co-loaded isotope without doubling the
    latency contribution.
    """

    node_type: Literal["load_atoms"] = "load_atoms"
    species: AtomSpecies
    ancilla_species: AtomSpecies | None = None
    count: int = Field(gt=0)
    device_class: DeviceClass = DeviceClass.NI_DAQ
    timing_domain: TimingDomain = TimingDomain.ELECTRONIC

    def latency_ms(self) -> float:
        return 200.0


class AcquireEMCCD(IRNode):
    """Andor iXon-897-class capture. Default 20 ms anchors arXiv:2406.12247 abstract."""

    node_type: Literal["acquire_emccd"] = "acquire_emccd"
    exposure_ms: float = Field(default=20.0, gt=0)
    dma_overhead_ms: float = Field(default=5.0, ge=0)
    device_class: DeviceClass = DeviceClass.CAMERA
    timing_domain: TimingDomain = TimingDomain.FEEDBACK

    def latency_ms(self) -> float:
        return self.exposure_ms + self.dma_overhead_ms


class ClassifyOccupancy(IRNode):
    node_type: Literal["classify_occupancy"] = "classify_occupancy"
    threshold: float = 0.5
    device_class: DeviceClass = DeviceClass.CAMERA
    timing_domain: TimingDomain = TimingDomain.FEEDBACK

    def latency_ms(self) -> float:
        return 2.0


class AODMovePlan(IRNode):
    node_type: Literal["aod_move_plan"] = "aod_move_plan"
    algorithm: Literal["hungarian", "sqrt_t"] = "sqrt_t"
    device_class: DeviceClass = DeviceClass.AD9910
    timing_domain: TimingDomain = TimingDomain.FEEDBACK

    def latency_ms(self) -> float:
        return 10.0


class DDSSetProfile(IRNode):
    node_type: Literal["dds_set_profile"] = "dds_set_profile"
    ftw: int = Field(ge=0, lt=2**32)
    asf: int = Field(ge=0, lt=2**14)
    profile_index: int = Field(ge=0, lt=8)
    device_class: DeviceClass = DeviceClass.AD9910
    timing_domain: TimingDomain = TimingDomain.ELECTRONIC

    def latency_ms(self) -> float:
        return 0.001


class AnalogRamp(IRNode):
    node_type: Literal["analog_ramp"] = "analog_ramp"
    channel: str
    start_v: float
    end_v: float
    ramp_ms: float = Field(gt=0)
    device_class: DeviceClass = DeviceClass.NI_DAQ
    timing_domain: TimingDomain = TimingDomain.ELECTRONIC

    def latency_ms(self) -> float:
        return self.ramp_ms


class TTLWindow(IRNode):
    node_type: Literal["ttl_window"] = "ttl_window"
    channel: str
    on: bool
    duration_us: float = Field(gt=0)
    device_class: DeviceClass = DeviceClass.NI_DAQ
    timing_domain: TimingDomain = TimingDomain.ELECTRONIC

    def latency_ms(self) -> float:
        return self.duration_us / 1000.0


class OpticalDelay(IRNode):
    """Mechanical delay line coordination — non-electronic timing domain.

    ``delay_ps`` is capped at 100 ns (100_000 ps) to reflect the physical
    coordination window documented in arXiv:1910.05292 Supplemental p. 10
    (τ ≈ 60 ns).
    """

    node_type: Literal["optical_delay"] = "optical_delay"
    delay_ps: float = Field(ge=0.0, le=100_000.0)
    stage_settle_ms: float = Field(default=50.0, ge=0)
    device_class: DeviceClass = DeviceClass.OPTICAL_DELAY
    timing_domain: TimingDomain = TimingDomain.OPTICAL

    def latency_ms(self) -> float:
        return self.stage_settle_ms


class GateBlock(IRNode):
    """Species-tagged quantum gate.

    ``gate_mechanism`` discriminates the Kyoto CW regime (electronic, ~µs)
    from the IMS Okazaki ultrafast regime (optical, ps CPA pulses).
    Coercion to the correct domain happens in a ``mode='before'`` validator
    so the frozen contract is never violated (board review, Takahashi).
    """

    node_type: Literal["gate_block"] = "gate_block"
    species: AtomSpecies
    gate_name: str
    gate_mechanism: Literal["electronic", "optical"] = "electronic"
    device_class: DeviceClass = DeviceClass.AD9910
    timing_domain: TimingDomain = TimingDomain.ELECTRONIC

    @model_validator(mode="before")
    @classmethod
    def _coerce_optical_domain(cls, data: object) -> object:
        if isinstance(data, dict) and data.get("gate_mechanism") == "optical":
            data.setdefault("device_class", DeviceClass.OPTICAL_DELAY)
            data.setdefault("timing_domain", TimingDomain.OPTICAL)
            # Even if user passed defaults explicitly, force coherence here:
            data["device_class"] = DeviceClass.OPTICAL_DELAY
            data["timing_domain"] = TimingDomain.OPTICAL
        return data

    def latency_ms(self) -> float:
        if self.gate_mechanism == "optical":
            return 0.0  # ps CPA — negligible in ms budget
        return 0.01


class MeasureAncilla(IRNode):
    """MCM readout on ancilla species. Default 20 ms anchors arXiv:2406.12247."""

    node_type: Literal["measure_ancilla"] = "measure_ancilla"
    species: AtomSpecies = AtomSpecies.YB174
    output_bit: str = "m"
    exposure_ms: float = Field(default=20.0, gt=0)
    dma_overhead_ms: float = Field(default=5.0, ge=0)
    device_class: DeviceClass = DeviceClass.CAMERA
    timing_domain: TimingDomain = TimingDomain.FEEDBACK

    def latency_ms(self) -> float:
        return self.exposure_ms + self.dma_overhead_ms


class BranchIf(IRNode):
    node_type: Literal["branch_if"] = "branch_if"
    condition: str
    true_branch: tuple[str, ...] = ()
    false_branch: tuple[str, ...] = ()
    device_class: DeviceClass = DeviceClass.NI_DAQ
    timing_domain: TimingDomain = TimingDomain.FEEDBACK

    def latency_ms(self) -> float:
        return 0.1


class Reset(IRNode):
    node_type: Literal["reset"] = "reset"
    species: AtomSpecies | None = None
    device_class: DeviceClass = DeviceClass.NI_DAQ
    timing_domain: TimingDomain = TimingDomain.ELECTRONIC

    def latency_ms(self) -> float:
        return 1.0


class CalibrationStep(IRNode):
    """Calibration routine with pass/fail methodology.

    a routine without a
    reference standard and an acceptance criterion is not a calibration.
    When ``routine`` is set, both ``reference_standard`` and
    ``acceptance_criterion`` MUST be non-empty.
    """

    node_type: Literal["calibration_step"] = "calibration_step"
    routine: str
    reference_standard: str = ""
    blank_id: str | None = None
    acceptance_criterion: str = ""
    duration_ms: float = Field(default=100.0, gt=0)
    device_class: DeviceClass = DeviceClass.NI_DAQ
    timing_domain: TimingDomain = TimingDomain.ELECTRONIC

    @model_validator(mode="after")
    def _require_methodology(self) -> CalibrationStep:
        if self.routine and not (self.reference_standard and self.acceptance_criterion):
            raise ValueError(
                "CalibrationStep with a routine requires non-empty "
                "reference_standard and acceptance_criterion "
                "(board review: calibration without pass/fail is a stub)."
            )
        return self

    def latency_ms(self) -> float:
        return self.duration_ms


class StabilizationLoop(IRNode):
    """Persistent background servo (e.g. Arduino DUE fiber MZI phase lock).

    although the controller is electronic
    (Arduino DUE), the loop protects the optical CPA path — classified
    OPTICAL per internal design notes §1.1 so ``dominant_domain()`` attributes the
    cross-lab servo to the correct side.

    """

    node_type: Literal["stabilization_loop"] = "stabilization_loop"
    loop_bandwidth_hz: float = Field(gt=0)
    setpoint: str
    device_class: DeviceClass = DeviceClass.ARDUINO_LOCK
    timing_domain: TimingDomain = TimingDomain.OPTICAL


class AssertStabilization(IRNode):
    """Block until the named StabilizationLoop reports locked.

    Required predecessor of every ``GateBlock(gate_mechanism='optical')`` —
    enforced in ``ShotGraph.validate()`` per R2 de Léséleuc/Ohmori findings.
    """

    node_type: Literal["assert_stabilization"] = "assert_stabilization"
    loop_name: str
    timeout_ms: float = Field(default=10.0, gt=0)
    device_class: DeviceClass = DeviceClass.ARDUINO_LOCK
    timing_domain: TimingDomain = TimingDomain.ELECTRONIC

    def latency_ms(self) -> float:
        return 0.1  # already-locked fast path

    def worst_case_latency_ms(self) -> float:
        """Lock-acquisition worst case — bounded by ``timeout_ms``."""
        return self.timeout_ms


class TDMWaveform(IRNode):
    """Time-division-multiplexed waveform on a QuEL-style multi-FPGA controller."""

    node_type: Literal["tdm_waveform"] = "tdm_waveform"
    channel_id: int = Field(ge=0)
    spline_control_points: tuple[tuple[float, float], ...] = ()
    device_class: DeviceClass = DeviceClass.FPGA_CTRL
    timing_domain: TimingDomain = TimingDomain.ELECTRONIC

    def latency_ms(self) -> float:
        return 0.001


NODE_TYPES: tuple[type[IRNode], ...] = (
    LoadAtoms, AcquireEMCCD, ClassifyOccupancy, AODMovePlan, DDSSetProfile,
    AnalogRamp, TTLWindow, OpticalDelay, GateBlock, MeasureAncilla,
    BranchIf, Reset, CalibrationStep, StabilizationLoop, AssertStabilization,
    TDMWaveform,
)

__all__ = [
    "IRNode", "LoadAtoms", "AcquireEMCCD", "ClassifyOccupancy", "AODMovePlan",
    "DDSSetProfile", "AnalogRamp", "TTLWindow", "OpticalDelay", "GateBlock",
    "MeasureAncilla", "BranchIf", "Reset", "CalibrationStep",
    "StabilizationLoop", "AssertStabilization", "TDMWaveform", "NODE_TYPES",
]
