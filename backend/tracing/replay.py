"""Replay trace ops into a graph state, with strict validation.

This mirrors what the frontend's `stateAt(trace, k)` will do (PLAN.md D3) and
is used by tests to check that a trace is internally consistent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from tracing.schema import AddEdge, AddNode, GraphOp, RemoveEdge, Step, Trace


@dataclass
class GraphState:
    """Graph after applying some prefix of a trace."""

    nodes: dict[int, tuple[frozenset[int], frozenset[int]]] = field(default_factory=dict)
    edges: set[tuple[int, int]] = field(default_factory=set)  # (parent, child)

    def copy(self) -> "GraphState":
        return GraphState(dict(self.nodes), set(self.edges))


class ReplayError(ValueError):
    """An op was invalid for the state it was applied to."""


def apply_op(state: GraphState, op: GraphOp) -> None:
    if isinstance(op, AddNode):
        if op.id in state.nodes:
            raise ReplayError(f"add_node: id {op.id} already exists")
        if op.extent != sorted(set(op.extent)) or op.intent != sorted(set(op.intent)):
            raise ReplayError(f"add_node {op.id}: extent/intent must be sorted and unique")
        state.nodes[op.id] = (frozenset(op.extent), frozenset(op.intent))
    elif isinstance(op, AddEdge):
        edge = (op.source, op.target)
        if op.source not in state.nodes or op.target not in state.nodes:
            raise ReplayError(f"add_edge {edge}: unknown endpoint")
        if edge in state.edges:
            raise ReplayError(f"add_edge {edge}: already present")
        state.edges.add(edge)
    elif isinstance(op, RemoveEdge):
        edge = (op.source, op.target)
        if edge not in state.edges:
            raise ReplayError(f"remove_edge {edge}: not present")
        state.edges.remove(edge)
    else:  # pragma: no cover - the discriminated union makes this unreachable
        raise ReplayError(f"unknown op {op!r}")


def apply_step(state: GraphState, step: Step) -> None:
    for op in step.ops:
        apply_op(state, op)


def replay_steps(steps: Iterable[Step], upto: Optional[int] = None) -> GraphState:
    """State after applying steps[0..upto] (inclusive); all steps if `upto` is None."""
    state = GraphState()
    for step in steps:
        if upto is not None and step.index > upto:
            break
        apply_step(state, step)
    return state


def replay(trace: Trace, upto: Optional[int] = None) -> GraphState:
    return replay_steps(trace.steps, upto)
