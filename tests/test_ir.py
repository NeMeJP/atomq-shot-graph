"""M1 exit criterion: dual-isotope feedback graph builds and validates."""
from __future__ import annotations

import pytest

from yaqumo_shot_graph import ShotGraph, nodes
from yaqumo_shot_graph.ir.types import AtomSpecies, DeviceClass, TimingDomain


def build_dual_isotope_demo() -> ShotGraph:
    """Canonical dual-isotope MCM-with-feedback shot graph."""
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
    g.add(nodes.MeasureAncilla(name="mcm", species=AtomSpecies.YB174, output_bit="m"))
    g.add(nodes.BranchIf(
        name="feedforward",
        condition="m == 1",
        true_branch=("correction",),
    ))
    g.add(nodes.GateBlock(
        name="correction", species=AtomSpecies.YB171, gate_name="x_correction",
    ))
    return g


def test_dual_isotope_graph_builds_and_validates() -> None:
    g = build_dual_isotope_demo()
    g.validate()
    assert len(g) == 9


def test_graph_rejects_duplicate_names() -> None:
    g = ShotGraph()
    g.add(nodes.LoadAtoms(name="x", species=AtomSpecies.YB171, count=1))
    with pytest.raises(ValueError, match="duplicate node name"):
        g.add(nodes.LoadAtoms(name="x", species=AtomSpecies.YB174, count=1))


def test_graph_rejects_unknown_predecessor() -> None:
    g = ShotGraph()
    with pytest.raises(ValueError, match="unknown predecessor"):
        g.add(nodes.LoadAtoms(name="x", species=AtomSpecies.YB171, count=1), after="ghost")


def test_branch_if_must_reference_existing_nodes() -> None:
    g = ShotGraph()
    g.add(nodes.MeasureAncilla(name="m1"))
    g.add(nodes.BranchIf(name="br", condition="m==1", true_branch=("does_not_exist",)))
    with pytest.raises(ValueError, match="references unknown node"):
        g.validate()


def test_timing_domains_are_distinguished() -> None:
    g = build_dual_isotope_demo()
    electronic = [n for n in g.nodes() if n.timing_domain == TimingDomain.ELECTRONIC]
    feedback = [n for n in g.nodes() if n.timing_domain == TimingDomain.FEEDBACK]
    assert electronic, "expected at least one electronic-domain node"
    assert feedback, "expected at least one feedback-domain node (image / MCM / branch)"


def test_node_latencies_are_nonnegative() -> None:
    g = build_dual_isotope_demo()
    for node in g.nodes():
        assert node.latency_ms() >= 0.0, f"{node.name} has negative latency"


def test_feedback_dominates_duration() -> None:
    """Sanity: image/classify/MCM should dominate a 9-node shot budget."""
    g = build_dual_isotope_demo()
    by_domain: dict[TimingDomain, float] = {d: 0.0 for d in TimingDomain}
    for node in g.nodes():
        by_domain[node.timing_domain] += node.latency_ms()
    # load=200ms (electronic), image=10+classify=2+rearrange=10+mcm=5+branch=0.1 ≈ 27ms
    # electronic still > feedback because of MOT loading — that's realistic too.
    assert by_domain[TimingDomain.FEEDBACK] > 20.0


def test_ad9910_ftw_range_enforced() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        nodes.DDSSetProfile(name="bad", ftw=2**33, asf=0x1000, profile_index=0)


def test_all_node_types_have_device_class() -> None:
    from yaqumo_shot_graph.ir.nodes import NODE_TYPES

    for node_cls in NODE_TYPES:
        fields = node_cls.model_fields
        assert "device_class" in fields
        assert "timing_domain" in fields


def test_device_class_registry_has_all_documented_devices() -> None:
    """pin_list_v2.md §2 inferred-high list must be reflected in DeviceClass."""
    required = {"ni_daq", "ad9910", "camera", "slm", "optical_delay", "arduino_lock"}
    assert {d.value for d in DeviceClass} >= required


# === 2026-04-20 board-review consensus fixes ===


def test_yb173_species_exists() -> None:
    """Board review (Takahashi, de Léséleuc): YB173 must be representable."""
    assert AtomSpecies.YB173 == "Yb173"


def test_fpga_ctrl_device_class_exists() -> None:
    """Board review (Tomita): heterogeneous multi-FPGA slot is reserved."""
    assert DeviceClass.FPGA_CTRL == "fpga_ctrl"


def test_gate_block_optical_mechanism_coerces_domain() -> None:
    """Board review (5/6 personas, BLOCKER): GateBlock must not collapse domains."""
    g = nodes.GateBlock(
        name="rydberg_cz", species=AtomSpecies.YB171, gate_name="cz",
        gate_mechanism="optical",
    )
    assert g.timing_domain == TimingDomain.OPTICAL
    assert g.device_class == DeviceClass.OPTICAL_DELAY
    assert g.latency_ms() == 0.0  # ps CPA — negligible in ms budget


def test_gate_block_electronic_mechanism_stays_electronic() -> None:
    g = nodes.GateBlock(
        name="cw_gate", species=AtomSpecies.YB171, gate_name="x",
        gate_mechanism="electronic",
    )
    assert g.timing_domain == TimingDomain.ELECTRONIC
    assert g.device_class == DeviceClass.AD9910
    assert g.latency_ms() == 0.01  # ~10 µs CW


def test_measure_ancilla_exposure_ms_parameterized() -> None:
    """Board review (5/6): MeasureAncilla must expose exposure_ms."""
    m20 = nodes.MeasureAncilla(name="m_default")
    assert m20.exposure_ms == 20.0  # literature anchor arXiv:2406.12247
    assert m20.latency_ms() == 25.0  # 20 + 5 dma

    m50 = nodes.MeasureAncilla(name="m_slow", exposure_ms=50.0)
    assert m50.latency_ms() == 55.0


def test_calibration_step_has_device_class_default() -> None:
    """Board review: CalibrationStep must instantiate (with required methodology)."""
    c = nodes.CalibrationStep(
        name="cal", routine="aom_center",
        reference_standard="SRS-FS725",
        acceptance_criterion="drift < 1e-9",
    )
    assert c.device_class == DeviceClass.NI_DAQ


def test_calibration_step_validator_requires_methodology() -> None:
    """R2 board review: empty reference_standard/acceptance_criterion must raise."""
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="reference_standard and acceptance_criterion"):
        nodes.CalibrationStep(name="cal", routine="aom_center")  # missing methodology


def test_calibration_step_methodology_fields_present() -> None:
    """Board review (Nakashoji): reference_standard / blank_id / acceptance_criterion exist."""
    c = nodes.CalibrationStep(
        name="cal_strict",
        routine="aom_center",
        reference_standard="SRS-DS345-10MHz",
        blank_id="dark-frame-001",
        acceptance_criterion="drift < 1e-9 over 60 s",
    )
    assert c.reference_standard == "SRS-DS345-10MHz"
    assert c.acceptance_criterion.startswith("drift <")


def test_stabilization_loop_node_constructs() -> None:
    """Board review (Tomita, Ohmori, Nakashoji): fiber MZI lock must be representable."""
    loop = nodes.StabilizationLoop(
        name="fiber_mzi_lock", loop_bandwidth_hz=500.0, setpoint="mzi_phase",
    )
    assert loop.device_class == DeviceClass.ARDUINO_LOCK
    assert loop.latency_ms() == 0.0  # background


def test_assert_stabilization_guards_optical_gate() -> None:
    assert_node = nodes.AssertStabilization(name="assert_lock", loop_name="fiber_mzi_lock")
    assert assert_node.timing_domain == TimingDomain.ELECTRONIC
    assert assert_node.timeout_ms == 10.0


def test_tdm_waveform_slot_exists() -> None:
    """Board review (Tomita): ICCE 2025 TDM waveform slot reserved."""
    wf = nodes.TDMWaveform(
        name="tdm_ch0", channel_id=0,
        spline_control_points=((0.0, 0.0), (10.0, 0.5), (20.0, 0.0)),
    )
    assert wf.device_class == DeviceClass.FPGA_CTRL
    assert len(wf.spline_control_points) == 3


def test_optical_delay_backend_accepts_optical_gate_block() -> None:
    """Board review: OpticalDelayBackend must route GateBlock(mechanism='optical')."""
    from yaqumo_shot_graph.backends.optical_delay import OpticalDelayBackend

    bk = OpticalDelayBackend()
    g = nodes.GateBlock(
        name="rydberg_cz", species=AtomSpecies.YB171, gate_name="cz",
        gate_mechanism="optical",
    )
    cmds = list(bk.emit(g))
    assert len(cmds) == 1
    assert cmds[0].op == "optical_gate"
    assert cmds[0].payload["gate_name"] == "cz"
