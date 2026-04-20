"""IR -> OpenQASM 3 text (read-only export, M5a).

This is a read-only export layer, not a Yaqumo runtime.

Motivation: prove that the shot-graph IR can be translated to a
public, standards-based frontend (OpenQASM 3) without claiming that
OpenQASM 3 is the Yaqumo control stack. Pulse-level, optical-domain,
and feedback-domain nodes that have no native QASM 3 equivalent are
emitted as pragma-style comments.

The output is a single str; this module performs no file I/O.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from yaqumo_shot_graph.ir.nodes import (
    AcquireEMCCD,
    AnalogRamp,
    AODMovePlan,
    BranchIf,
    CalibrationStep,
    ClassifyOccupancy,
    DDSSetProfile,
    GateBlock,
    IRNode,
    LoadAtoms,
    MeasureAncilla,
    OpticalDelay,
    Reset,
    TTLWindow,
)

if TYPE_CHECKING:
    from yaqumo_shot_graph.ir.graph import ShotGraph



_HEADER_LINE1 = "OPENQASM 3.0;"
_HEADER_LINE2 = 'include "stdgates.inc";'


def _species_tag(species: object) -> str:
    raw = getattr(species, "value", species)
    return str(raw).lower()


def _render_load_atoms(node: LoadAtoms) -> list[str]:
    tag = _species_tag(node.species)
    return [
        f"// {node.name}: load {node.count} atoms of {node.species.value}",
        f"qubit[{node.count}] q_{tag};",
        f"bit[{node.count}] c_{tag};",
    ]


def _render_reset(node: Reset) -> list[str]:
    if node.species is None:
        return [
            f"// {node.name}: reset all registers",
            "reset q_yb171;",
            "reset q_yb174;",
        ]
    tag = _species_tag(node.species)
    return [f"reset q_{tag};"]


def _render_gate_block(node: GateBlock) -> list[str]:
    tag = _species_tag(node.species)
    return [f"{node.gate_name}_{tag} q_{tag}[0];"]


def _render_measure(node: MeasureAncilla) -> list[str]:
    tag = _species_tag(node.species)
    return [f"{node.output_bit} = measure q_{tag}[0];"]



def _render_branch_if(node: BranchIf) -> list[str]:
    if node.true_branch:
        targets = ", ".join(node.true_branch)
        comment = f"// true_branch -> {targets}"
    else:
        comment = "// true_branch (empty)"
    lines = [f"if ({node.condition}) {{ {comment} }}"]
    false_targets = ", ".join(node.false_branch)
    if false_targets:
        lines.append(f"// else_branch -> {false_targets}")
    return lines


def _render_optical(node: OpticalDelay) -> list[str]:
    return [
        f"// OPTICAL_DOMAIN: {node.name} "
        f"delay_ps={node.delay_ps}, stage_settle_ms={node.stage_settle_ms}"
    ]


def _render_calibration(node: CalibrationStep) -> list[str]:
    return [f"// CAL: routine={node.routine} duration_ms={node.duration_ms}"]



_KIND_MAP: dict[str, str] = {}
_KIND_MAP["acquire_emccd"] = "AcquireEMCCD"
_KIND_MAP["analog_ramp"] = "AnalogRamp"
_KIND_MAP["aod_move_plan"] = "AODMovePlan"
_KIND_MAP["branch_if"] = "BranchIf"
_KIND_MAP["calibration_step"] = "CalibrationStep"
_KIND_MAP["classify_occupancy"] = "ClassifyOccupancy"
_KIND_MAP["dds_set_profile"] = "DDSSetProfile"
_KIND_MAP["gate_block"] = "GateBlock"
_KIND_MAP["load_atoms"] = "LoadAtoms"
_KIND_MAP["measure_ancilla"] = "MeasureAncilla"
_KIND_MAP["optical_delay"] = "OpticalDelay"
_KIND_MAP["reset"] = "Reset"
_KIND_MAP["ttl_window"] = "TTLWindow"



def _kind_label(node: IRNode) -> str:
    kind = getattr(node, "node_type", "")
    return _KIND_MAP.get(kind, kind or "IRNode")



_FIELDS_BY_KIND: dict[str, tuple[str, ...]] = {}
_FIELDS_BY_KIND["acquire_emccd"] = ("exposure_ms", "dma_overhead_ms")
_FIELDS_BY_KIND["analog_ramp"] = ("channel", "start_v", "end_v", "ramp_ms")
_FIELDS_BY_KIND["aod_move_plan"] = ("algorithm",)
_FIELDS_BY_KIND["branch_if"] = ("condition", "true_branch", "false_branch")
_FIELDS_BY_KIND["calibration_step"] = ("routine", "duration_ms")
_FIELDS_BY_KIND["classify_occupancy"] = ("threshold",)
_FIELDS_BY_KIND["dds_set_profile"] = ("ftw", "asf", "profile_index")
_FIELDS_BY_KIND["gate_block"] = ("species", "gate_name")
_FIELDS_BY_KIND["load_atoms"] = ("species", "count")
_FIELDS_BY_KIND["measure_ancilla"] = ("species", "output_bit")
_FIELDS_BY_KIND["optical_delay"] = ("delay_ps", "stage_settle_ms")
_FIELDS_BY_KIND["reset"] = ("species",)
_FIELDS_BY_KIND["ttl_window"] = ("channel", "on", "duration_us")



def _payload_fields(node: IRNode) -> str:
    pairs: list[str] = []
    for field_name in _FIELDS_BY_KIND.get(getattr(node, "node_type", ""), ()):
        value = getattr(node, field_name, None)
        if value is None:
            continue
        value_repr = getattr(value, "value", value)
        pairs.append(f"{field_name}={value_repr}")
    return ", ".join(pairs)



def _render_pulse_level(node: IRNode) -> list[str]:
    return [f"// PULSE_LEVEL: {_kind_label(node)} {node.name} {_payload_fields(node)}"]


def _render_feedback(node: IRNode) -> list[str]:
    return [f"// FEEDBACK_DOMAIN: {_kind_label(node)} {node.name} {_payload_fields(node)}"]



def _render_node(node: IRNode) -> list[str]:
    if isinstance(node, LoadAtoms):
        return _render_load_atoms(node)
    if isinstance(node, Reset):
        return _render_reset(node)
    if isinstance(node, GateBlock):
        return _render_gate_block(node)
    if isinstance(node, MeasureAncilla):
        return _render_measure(node)
    if isinstance(node, BranchIf):
        return _render_branch_if(node)
    if isinstance(node, OpticalDelay):
        return _render_optical(node)
    if isinstance(node, (DDSSetProfile, AnalogRamp, TTLWindow)):
        return _render_pulse_level(node)
    if isinstance(node, (AODMovePlan, ClassifyOccupancy, AcquireEMCCD)):
        return _render_feedback(node)
    if isinstance(node, CalibrationStep):
        return _render_calibration(node)
    return [f"// UNMAPPED: {_kind_label(node)} {node.name}"]


def to_openqasm3(graph: "ShotGraph") -> str:
    lines: list[str] = [_HEADER_LINE1, _HEADER_LINE2]
    for node in graph.nodes():
        chunk = _render_node(node)
        if chunk:
            lines.extend(chunk)
    return "\n".join(lines) + "\n"


__all__ = ["to_openqasm3"]
