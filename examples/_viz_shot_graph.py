"""Render the shot graph as a professional DAG via Graphviz.

Outputs docs/images/shot_graph.png with an industry-standard left-to-right
flow rendering (similar to Airflow / dbt / Prefect control-flow diagrams).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import importlib.util

spec = importlib.util.spec_from_file_location(
    "demo", Path(__file__).parent / "01_dual_isotope_feedback.py",
)
assert spec is not None and spec.loader is not None
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)

import graphviz  # noqa: E402

from yaqumo_shot_graph import ShotGraph  # noqa: E402
from yaqumo_shot_graph.ir.nodes import (  # noqa: E402
    AssertStabilization,
    BranchIf,
    GateBlock,
    StabilizationLoop,
)
from yaqumo_shot_graph.ir.types import TimingDomain  # noqa: E402

# Muted, desaturated palette — closer to academic figure style.
DOMAIN_STYLE = {
    TimingDomain.ELECTRONIC: {"fillcolor": "#e0e7ff", "color": "#4338ca", "fontcolor": "#1e1b4b"},
    TimingDomain.OPTICAL:    {"fillcolor": "#d1fae5", "color": "#047857", "fontcolor": "#064e3b"},
    TimingDomain.FEEDBACK:   {"fillcolor": "#fee2e2", "color": "#b91c1c", "fontcolor": "#7f1d1d"},
}

NODE_KIND_LABEL = {
    "load_atoms":          "LoadAtoms",
    "acquire_emccd":       "AcquireEMCCD",
    "classify_occupancy":  "ClassifyOccupancy",
    "aod_move_plan":       "AODMovePlan",
    "dds_set_profile":     "DDSSetProfile",
    "analog_ramp":         "AnalogRamp",
    "ttl_window":          "TTLWindow",
    "optical_delay":       "OpticalDelay",
    "gate_block":          "GateBlock",
    "measure_ancilla":     "MeasureAncilla",
    "branch_if":           "BranchIf",
    "reset":               "Reset",
    "calibration_step":    "CalibrationStep",
    "stabilization_loop":  "StabilizationLoop",
    "assert_stabilization": "AssertStabilization",
    "tdm_waveform":        "TDMWaveform",
}


def _node_label(node: object) -> str:
    """Two-line label: TypeName on top (bold), instance name + latency below."""
    type_label = NODE_KIND_LABEL.get(node.node_type, type(node).__name__)  # type: ignore[attr-defined]
    ms = node.latency_ms()  # type: ignore[attr-defined]
    name = node.name  # type: ignore[attr-defined]

    # Add extra hint for the interesting ones
    hint = ""
    if isinstance(node, GateBlock):
        hint = f"\\n{node.gate_mechanism} · {node.species.value} · {node.gate_name}"
    elif isinstance(node, (StabilizationLoop, AssertStabilization)):
        hint = f"\\n{getattr(node, 'setpoint', getattr(node, 'loop_name', ''))}"
    elif isinstance(node, BranchIf):
        hint = f"\\nif {node.condition}"

    ms_str = f"{ms:g} ms" if ms > 0 else "background"
    return f"<<B>{type_label}</B><BR/><FONT POINT-SIZE=\"9\">{name}{hint.replace(chr(92)+'n', '<BR/>')} · <I>{ms_str}</I></FONT>>"


def render(graph: ShotGraph, out_path: str) -> None:
    dot = graphviz.Digraph(
        "shot_graph",
        graph_attr={
            "rankdir": "LR",
            "splines": "spline",
            "bgcolor": "white",
            "fontname": "Helvetica",
            "labelloc": "t",
            "label": "<<B>yaqumo-shot-graph — dual-isotope MCM</B><BR/><FONT POINT-SIZE=\"10\">"
                     "color = timing domain · shape = node role</FONT>>",
            "pad": "0.5",
            "nodesep": "0.35",
            "ranksep": "0.55",
        },
        node_attr={
            "shape": "box",
            "style": "rounded,filled",
            "fontname": "Helvetica",
            "fontsize": "11",
            "penwidth": "1.5",
            "margin": "0.15,0.08",
        },
        edge_attr={
            "color": "#64748b",
            "penwidth": "1.2",
            "arrowsize": "0.75",
            "fontname": "Helvetica",
            "fontsize": "9",
        },
    )

    # Legend as a subgraph cluster
    with dot.subgraph(name="cluster_legend") as sub:
        sub.attr(label="Timing domain", style="dashed", color="#94a3b8",
                 fontcolor="#334155", fontsize="10", rankdir="TB")
        for d in TimingDomain:
            s = DOMAIN_STYLE[d]
            sub.node(
                f"_legend_{d.name}",
                label=f"  {d.name.lower()}  ",
                fillcolor=s["fillcolor"],
                color=s["color"],
                fontcolor=s["fontcolor"],
                fontsize="10",
            )

    for node in graph.nodes():
        style = DOMAIN_STYLE[node.timing_domain]
        # Special shape for branch/control flow
        shape = "box"
        if isinstance(node, BranchIf):
            shape = "diamond"
        elif isinstance(node, (StabilizationLoop, AssertStabilization)):
            shape = "note"
        dot.node(
            node.name,
            label=_node_label(node),
            fillcolor=style["fillcolor"],
            color=style["color"],
            fontcolor=style["fontcolor"],
            shape=shape,
        )

    for src, dst in graph.edges():
        dot.edge(src, dst)

    dot.render(out_path.replace(".png", ""), format="png", cleanup=True)
    print(f"saved: {out_path}")


if __name__ == "__main__":
    render(demo.build_dual_isotope_graph(), "docs/images/shot_graph.png")
