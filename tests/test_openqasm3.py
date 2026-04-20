"""M5a exit criterion: OpenQASM 3 export produces valid-looking text.

No openqasm3 reference parser is pinned as a test-time dep, so we assert
structural invariants of the output string (header, required declarations,
pragma comments for non-QASM-native domains).
"""
from __future__ import annotations

from yaqumo_shot_graph import ShotGraph, nodes
from yaqumo_shot_graph.export.openqasm3 import to_openqasm3
from yaqumo_shot_graph.ir.types import AtomSpecies, DeviceClass



def _build_dual_isotope_demo() -> ShotGraph:
    """Mirror of tests/test_ir.py::build_dual_isotope_demo."""
    g = ShotGraph()
    g.add(nodes.LoadAtoms(name="load", species=AtomSpecies.YB171, count=100))
    g.add(nodes.AcquireEMCCD(name="image_1", exposure_ms=5.0))
    g.add(nodes.ClassifyOccupancy(name="classify_1"))
    g.add(nodes.AODMovePlan(name="rearrange", algorithm="sqrt_t"))
    g.add(
        nodes.DDSSetProfile(
            name="aod_update", ftw=0x40000000, asf=0x2000, profile_index=0,
        )
    )
    g.add(
        nodes.GateBlock(
            name="rydberg_gate", species=AtomSpecies.YB171, gate_name="cz",
        )
    )
    g.add(nodes.LoadAtoms(name="load_174", species=AtomSpecies.YB174, count=1))
    g.add(
        nodes.MeasureAncilla(
            name="mcm", species=AtomSpecies.YB174, output_bit="m",
        )
    )
    g.add(
        nodes.BranchIf(
            name="feedforward",
            condition="m == 1",
            true_branch=("correction",),
        )
    )
    g.add(
        nodes.GateBlock(
            name="correction",
            species=AtomSpecies.YB171,
            gate_name="x_correction",
        )
    )
    return g



def test_header_is_emitted() -> None:
    g = ShotGraph()
    g.add(nodes.LoadAtoms(name="load", species=AtomSpecies.YB171, count=4))
    out = to_openqasm3(g)
    assert out.startswith("OPENQASM 3.0;")
    assert 'include "stdgates.inc";' in out


def test_minimal_graph_renders_header_and_qubit_decl() -> None:
    """At-least-one-LoadAtoms produces valid-looking header + register."""
    g = ShotGraph()
    g.add(nodes.LoadAtoms(name="load", species=AtomSpecies.YB171, count=8))
    out = to_openqasm3(g)
    lines = out.splitlines()
    assert lines[0] == "OPENQASM 3.0;"
    assert lines[1] == 'include "stdgates.inc";'
    assert "qubit[8] q_yb171;" in out
    assert "bit[8] c_yb171;" in out



def test_dual_isotope_demo_exports_expected_constructs() -> None:
    g = _build_dual_isotope_demo()
    out = to_openqasm3(g)

    assert out.startswith("OPENQASM 3.0;")
    assert 'include "stdgates.inc";' in out

    assert "qubit[100] q_yb171;" in out
    assert "q_yb174" in out

    assert "measure" in out
    assert "m = measure q_yb174[0];" in out

    assert "if (m == 1)" in out

    assert "cz_yb171 q_yb171[0];" in out
    assert "x_correction_yb171 q_yb171[0];" in out


def test_feedback_domain_nodes_become_pragma_comments() -> None:
    g = _build_dual_isotope_demo()
    out = to_openqasm3(g)
    assert "// FEEDBACK_DOMAIN" in out
    assert "AcquireEMCCD" in out
    assert "ClassifyOccupancy" in out
    assert "AODMovePlan" in out


def test_pulse_level_nodes_become_pragma_comments() -> None:
    g = _build_dual_isotope_demo()
    out = to_openqasm3(g)
    assert "// PULSE_LEVEL" in out
    assert "DDSSetProfile" in out



def test_optical_domain_node_becomes_pragma_comment() -> None:
    g = ShotGraph()
    g.add(nodes.LoadAtoms(name="load", species=AtomSpecies.YB171, count=2))
    g.add(nodes.OpticalDelay(name="cpa_delay", delay_ps=120.0, stage_settle_ms=25.0))
    out = to_openqasm3(g)
    assert "// OPTICAL_DOMAIN" in out
    assert "delay_ps=120.0" in out
    assert "stage_settle_ms=25.0" in out


def test_reset_without_species_resets_all_registers() -> None:
    g = ShotGraph()
    g.add(nodes.LoadAtoms(name="load", species=AtomSpecies.YB171, count=2))
    g.add(nodes.Reset(name="r"))
    out = to_openqasm3(g)
    assert "reset q_yb171;" in out
    assert "reset q_yb174;" in out


def test_calibration_step_emits_cal_comment() -> None:
    g = ShotGraph()
    g.add(nodes.CalibrationStep(name="cal", routine="rabi_freq", device_class=DeviceClass.NI_DAQ, reference_standard="ref", acceptance_criterion="ok"))
    out = to_openqasm3(g)
    assert "// CAL: routine=rabi_freq" in out


def test_output_is_pure_string_no_io() -> None:
    g = _build_dual_isotope_demo()
    out = to_openqasm3(g)
    assert isinstance(out, str)
    assert out.endswith("\n")


def test_module_docstring_declares_non_runtime() -> None:
    """pin_list_v2.md section 6 item 5: export is read-only, not a runtime."""
    from yaqumo_shot_graph.export import openqasm3 as mod

    assert mod.__doc__ is not None
    assert "read-only export layer, not a Yaqumo runtime." in mod.__doc__
