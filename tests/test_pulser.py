"""M5b tests -- Pulser export smoke + ImportError path."""
from __future__ import annotations

import sys

import pytest

from yaqumo_shot_graph import ShotGraph, nodes
from yaqumo_shot_graph.export.pulser import to_pulser_sequence
from yaqumo_shot_graph.ir.types import AtomSpecies


def _minimal_graph(count: int = 4) -> ShotGraph:
    g = ShotGraph()
    g.add(nodes.LoadAtoms(name="load", species=AtomSpecies.YB171, count=count))
    g.add(nodes.GateBlock(name="rydberg_gate", species=AtomSpecies.YB171, gate_name="cz"))
    return g


def test_to_pulser_sequence_returns_sequence() -> None:
    pytest.importorskip("pulser")
    g = _minimal_graph()
    seq = to_pulser_sequence(g)
    assert type(seq).__name__ == "Sequence"


def test_register_atom_count_matches_load_atoms() -> None:
    pytest.importorskip("pulser")
    g = _minimal_graph(count=9)
    seq = to_pulser_sequence(g)
    assert len(seq.register.qubits) >= 9


def test_optical_delay_translates_to_pulser_delay() -> None:
    pytest.importorskip("pulser")
    g = ShotGraph()
    g.add(nodes.LoadAtoms(name="load", species=AtomSpecies.YB171, count=4))
    g.add(nodes.GateBlock(name="gate", species=AtomSpecies.YB171, gate_name="cz"))
    g.add(nodes.OpticalDelay(name="delay", delay_ps=1000.0, stage_settle_ms=0.001))
    seq = to_pulser_sequence(g)
    assert type(seq).__name__ == "Sequence"


def test_missing_load_atoms_raises_value_error() -> None:
    pytest.importorskip("pulser")
    g = ShotGraph()
    g.add(nodes.GateBlock(name="orphan_gate", species=AtomSpecies.YB171, gate_name="cz"))
    with pytest.raises(ValueError, match="LoadAtoms"):
        to_pulser_sequence(g)


def test_import_error_when_pulser_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate pulser being unavailable and verify a helpful ImportError."""
    for mod_name in list(sys.modules):
        if mod_name == "pulser" or mod_name.startswith("pulser."):
            monkeypatch.setitem(sys.modules, mod_name, None)
    monkeypatch.setitem(sys.modules, "pulser", None)

    g = _minimal_graph()
    with pytest.raises(ImportError, match="pip install pulser"):
        to_pulser_sequence(g)
