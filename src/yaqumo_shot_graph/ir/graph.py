"""ShotGraph — typed DAG of IR nodes with validation.

Validation rules:
  - Must be acyclic
  - Every node has a valid TimingDomain and DeviceClass
  - BranchIf.true_branch / false_branch must reference existing nodes
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

import networkx as nx

if TYPE_CHECKING:
    from yaqumo_shot_graph.ir.nodes import IRNode


class ShotGraph:
    """Directed-acyclic shot-cycle specification."""

    def __init__(self) -> None:
        self._graph: nx.DiGraph[str] = nx.DiGraph()
        self._order: list[str] = []

    def add(self, node: IRNode, *, after: str | None = None) -> IRNode:
        """Add a node. Defaults to chaining after the last-added node.

        Use ``after=predecessor_name`` to branch off an earlier node,
        or pass the string literally to build feedback topologies.
        """
        if node.name in self._graph:
            raise ValueError(f"duplicate node name: {node.name!r}")
        self._graph.add_node(node.name, payload=node)
        if after is not None:
            if after not in self._graph:
                raise ValueError(f"unknown predecessor: {after!r}")
            self._graph.add_edge(after, node.name)
        elif self._order:
            self._graph.add_edge(self._order[-1], node.name)
        self._order.append(node.name)
        return node

    def add_edge(self, src: str, dst: str) -> None:
        """Add an explicit ordering edge (for branches / feedback topologies)."""
        if src not in self._graph:
            raise ValueError(f"unknown src node: {src!r}")
        if dst not in self._graph:
            raise ValueError(f"unknown dst node: {dst!r}")
        self._graph.add_edge(src, dst)

    def get(self, name: str) -> IRNode:
        if name not in self._graph:
            raise KeyError(name)
        return self._graph.nodes[name]["payload"]  # type: ignore[no-any-return]

    def nodes(self) -> Iterator[IRNode]:
        """Topologically ordered iteration."""
        for name in nx.topological_sort(self._graph):
            yield self._graph.nodes[name]["payload"]

    def edges(self) -> Iterator[tuple[str, str]]:
        yield from self._graph.edges()

    def validate(self) -> None:
        """Raise ValueError on any invariant violation."""
        if not nx.is_directed_acyclic_graph(self._graph):
            raise ValueError("shot graph contains a cycle")
        self._validate_branches()
        self._validate_optical_gates_have_stabilization_assert()

    def _validate_branches(self) -> None:
        from yaqumo_shot_graph.ir.nodes import BranchIf

        for name in self._graph.nodes:
            payload = self._graph.nodes[name]["payload"]
            if isinstance(payload, BranchIf):
                for target in (*payload.true_branch, *payload.false_branch):
                    if target not in self._graph:
                        raise ValueError(
                            f"BranchIf {name!r} references unknown node {target!r}"
                        )

    def _validate_optical_gates_have_stabilization_assert(self) -> None:
        """Every GateBlock(gate_mechanism='optical') must have an
        AssertStabilization in its topological ancestors that references
        a StabilizationLoop present in the graph (design requirement).
        """
        from yaqumo_shot_graph.ir.nodes import (
            AssertStabilization, GateBlock, StabilizationLoop,
        )

        loops_by_name = {
            name: payload
            for name in self._graph.nodes
            for payload in [self._graph.nodes[name]["payload"]]
            if isinstance(payload, StabilizationLoop)
        }

        for name in self._graph.nodes:
            node = self._graph.nodes[name]["payload"]
            if not (isinstance(node, GateBlock) and node.gate_mechanism == "optical"):
                continue
            ancestors = nx.ancestors(self._graph, name)
            assert_nodes = [
                self._graph.nodes[a]["payload"]
                for a in ancestors
                if isinstance(self._graph.nodes[a]["payload"], AssertStabilization)
            ]
            if not assert_nodes:
                raise ValueError(
                    f"optical GateBlock {name!r} has no AssertStabilization "
                    f"ancestor — required by internal design notes §1.1"
                )
            if not any(a.loop_name in loops_by_name for a in assert_nodes):
                raise ValueError(
                    f"optical GateBlock {name!r}: AssertStabilization "
                    f"ancestors reference unknown StabilizationLoop names"
                )

    def __len__(self) -> int:
        return len(self._graph)

    def __contains__(self, name: object) -> bool:
        return name in self._graph

    def __repr__(self) -> str:
        return (
            f"ShotGraph(nodes={len(self)}, "
            f"edges={self._graph.number_of_edges()})"
        )
