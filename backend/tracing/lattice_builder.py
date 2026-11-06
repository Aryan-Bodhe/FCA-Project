"""Incremental Hasse-diagram builder for concepts arriving in ANY order.

Why this exists instead of `graphing.concept_graph.ConceptLattice`:
`ConceptLattice.add_concept` only looks for new children among the children of
the new node's parents, and stores attribute *deltas* relative to the parents at
insertion time. That is correct when concepts arrive sorted by extent size (how
its constructor uses it) but gives a wrong Hasse diagram for Close-by-One /
In-Close discovery order and for arbitrary permutations (verified in B2). The
trace needs the algorithm's own discovery order, so we keep a separate,
order-independent builder. `ConceptLattice` is untouched and still serves the
matplotlib demo.

Conventions (PLAN.md §3): node ids are discovery order (0, 1, 2, ...); an edge
is (parent, child) where the parent is the superconcept (larger extent).
Concepts are ordered by extent inclusion alone (intent is determined by extent).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from tracing.schema import AddEdge, AddNode, GraphOp, RemoveEdge

Edge = tuple[int, int]


@dataclass(frozen=True)
class StepDelta:
    """Result of inserting one concept."""

    node_id: int
    is_new: bool  # False => duplicate; nothing changed
    extent: frozenset[int]
    intent: frozenset[int]
    parents: tuple[int, ...] = ()  # direct parents of the new node
    children: tuple[int, ...] = ()  # direct children of the new node
    added_edges: tuple[Edge, ...] = ()
    removed_edges: tuple[Edge, ...] = ()

    def ops(self) -> list[GraphOp]:
        """Graph ops for this insertion: add_node, remove_edges, add_edges (each sorted)."""
        if not self.is_new:
            return []
        out: list[GraphOp] = [
            AddNode(id=self.node_id, extent=sorted(self.extent), intent=sorted(self.intent))
        ]
        out += [RemoveEdge(source=s, target=t) for s, t in self.removed_edges]
        out += [AddEdge(source=s, target=t) for s, t in self.added_edges]
        return out


@dataclass
class LatticeBuilder:
    """Maintains the covering relation of the concepts inserted so far."""

    nodes: list[tuple[frozenset[int], frozenset[int]]] = field(default_factory=list)
    parents: dict[int, set[int]] = field(default_factory=dict)
    children: dict[int, set[int]] = field(default_factory=dict)
    _by_extent: dict[frozenset[int], int] = field(default_factory=dict)

    # ------------------------------------------------------------------ queries

    def __len__(self) -> int:
        return len(self.nodes)

    @property
    def edges(self) -> set[Edge]:
        return {(p, c) for p, cs in self.children.items() for c in cs}

    def extent(self, node: int) -> frozenset[int]:
        return self.nodes[node][0]

    def intent(self, node: int) -> frozenset[int]:
        return self.nodes[node][1]

    def node_id_of(self, extent: Iterable[int]) -> Optional[int]:
        return self._by_extent.get(frozenset(extent))

    # ----------------------------------------------------------------- insertion

    def add(self, extent: Iterable[int], intent: Iterable[int]) -> StepDelta:
        """Insert a concept; idempotent for duplicates (returns `is_new=False`)."""
        ext, itt = frozenset(extent), frozenset(intent)

        existing = self._by_extent.get(ext)
        if existing is not None:
            if self.nodes[existing][1] != itt:
                raise ValueError(
                    f"extent {sorted(ext)} already inserted with a different intent: "
                    f"{sorted(self.nodes[existing][1])} vs {sorted(itt)}"
                )
            return StepDelta(existing, False, ext, itt)

        above = {n for n, (e, _) in enumerate(self.nodes) if ext < e}  # superconcepts
        below = {n for n, (e, _) in enumerate(self.nodes) if e < ext}  # subconcepts

        # A node in `above` is a *direct* parent iff none of its children is also in
        # `above` (a child in `above` would sit strictly between it and the new node).
        # Symmetrically for direct children among `below`.
        new_parents = sorted(u for u in above if not (self.children[u] & above))
        new_children = sorted(w for w in below if not (self.parents[w] & below))

        node_id = len(self.nodes)
        self.nodes.append((ext, itt))
        self._by_extent[ext] = node_id
        self.parents[node_id] = set()
        self.children[node_id] = set()

        # Edges p -> c that the new node now separates.
        removed = sorted(
            (p, c) for p in new_parents for c in new_children if c in self.children[p]
        )
        for p, c in removed:
            self.children[p].discard(c)
            self.parents[c].discard(p)

        added: list[Edge] = [(p, node_id) for p in new_parents]
        added += [(node_id, c) for c in new_children]
        for p, c in added:
            self.children[p].add(c)
            self.parents[c].add(p)

        return StepDelta(
            node_id=node_id,
            is_new=True,
            extent=ext,
            intent=itt,
            parents=tuple(new_parents),
            children=tuple(new_children),
            added_edges=tuple(added),
            removed_edges=tuple(removed),
        )
