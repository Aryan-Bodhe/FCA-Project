"""Pydantic models for the trace contract (PLAN.md §3).

JSON uses camelCase (aliases); Python uses snake_case. Construct with either
name (`populate_by_name=True`); serialise with `by_alias=True`.
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

AlgorithmId = Literal["next_closure", "close_by_one", "in_close"]
Granularity = Literal["concept", "detailed"]
StepKind = Literal["init", "concept_found", "candidate", "reject", "done"]


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


# --------------------------------------------------------------------------- ops


class AddNode(CamelModel):
    """New concept. `extent`/`intent` are FULL index arrays, sorted ascending."""

    op: Literal["add_node"] = "add_node"
    id: int
    extent: list[int]
    intent: list[int]


class AddEdge(CamelModel):
    """Hasse edge; `source` is the PARENT (superconcept, larger extent)."""

    op: Literal["add_edge"] = "add_edge"
    source: int
    target: int


class RemoveEdge(CamelModel):
    op: Literal["remove_edge"] = "remove_edge"
    source: int
    target: int


GraphOp = Annotated[Union[AddNode, AddEdge, RemoveEdge], Field(discriminator="op")]


# ------------------------------------------------------------------------- steps


class Focus(CamelModel):
    """What the UI should highlight for this step."""

    nodes: list[int] = Field(default_factory=list)
    added_edges: list[tuple[int, int]] = Field(default_factory=list)
    removed_edges: list[tuple[int, int]] = Field(default_factory=list)


class AlgoInfo(CamelModel):
    """Algorithm-internal detail; only present in `detailed` granularity."""

    depth: int = 0
    attribute: Optional[int] = None
    candidate_intent: list[int] = Field(default_factory=list)
    candidate_extent: Optional[list[int]] = None
    closure: Optional[list[int]] = None
    accepted: bool
    reason: str = ""


class Step(CamelModel):
    index: int
    kind: StepKind
    message: str
    ops: list[GraphOp] = Field(default_factory=list)
    focus: Focus = Field(default_factory=Focus)
    algo: Optional[AlgoInfo] = None


# -------------------------------------------------------------------------- trace


class Meta(CamelModel):
    dataset: str
    algorithm: AlgorithmId
    granularity: Granularity
    objects: list[str]
    attributes: list[str]
    concept_count: int
    step_count: int
    truncated: bool = False
    max_concepts: int
    max_steps: int


class Trace(CamelModel):
    version: Literal[1] = 1
    meta: Meta
    steps: list[Step]

    @model_validator(mode="after")
    def _check_structure(self) -> "Trace":
        steps = self.steps
        if not steps:
            raise ValueError("a trace needs at least an 'init' and a 'done' step")
        for i, step in enumerate(steps):
            if step.index != i:
                raise ValueError(f"steps[{i}].index is {step.index}, expected {i}")
        if steps[0].kind != "init":
            raise ValueError("first step must have kind 'init'")
        if steps[-1].kind != "done":
            raise ValueError("last step must have kind 'done'")
        if self.meta.step_count != len(steps):
            raise ValueError(
                f"meta.stepCount is {self.meta.step_count} but there are {len(steps)} steps"
            )
        n_concepts = sum(1 for s in steps for op in s.ops if op.op == "add_node")
        if self.meta.concept_count != n_concepts:
            raise ValueError(
                f"meta.conceptCount is {self.meta.concept_count} but ops add {n_concepts} nodes"
            )
        return self
