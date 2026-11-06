"""LatticeBuilder: order-independent Hasse diagram + diff ops (plan chunk B2)."""

from __future__ import annotations

import random

import networkx as nx
import pytest

from algorithms import CloseByOne, InClose, NextClosure
from tracing.lattice_builder import LatticeBuilder
from tracing.replay import GraphState, apply_op

from helpers import index_concepts, load_context
from reference import hasse_reference

ALGORITHMS = [NextClosure, CloseByOne, InClose]
ALGORITHM_IDS = [a.__name__ for a in ALGORITHMS]
DATASETS = ["fca_airlines", "fca_benchmark_20x12", "fca_benchmark_40x20"]


def _build(concepts):
    """Insert concepts in order, replaying emitted ops alongside the builder.
    Returns (builder, replayed_state)."""
    builder = LatticeBuilder()
    state = GraphState()
    for extent, intent in concepts:
        delta = builder.add(extent, intent)
        for op in delta.ops():
            apply_op(state, op)
        # the replayed graph must track the builder after EVERY step
        assert state.edges == builder.edges
        assert len(state.nodes) == len(builder)
    return builder, state


def _as_extent_edges(builder: LatticeBuilder) -> set[tuple[frozenset, frozenset]]:
    return {(builder.extent(p), builder.extent(c)) for p, c in builder.edges}


def _assert_matches_reference(concepts, builder):
    extents = [e for e, _ in concepts]
    assert len(builder) == len(concepts)
    assert _as_extent_edges(builder) == hasse_reference(extents)
    graph = nx.DiGraph(sorted(builder.edges))
    assert nx.is_directed_acyclic_graph(graph)


@pytest.fixture(scope="module")
def algorithm_orders():
    """{dataset: {algorithm: [(extent, intent), ...] in discovery order}}"""
    out = {}
    for name in DATASETS:
        context = load_context(name)
        out[name] = {
            a.__name__: index_concepts(context, a(context).run()) for a in ALGORITHMS
        }
    return out


@pytest.mark.parametrize("dataset", DATASETS)
@pytest.mark.parametrize("algorithm", ALGORITHM_IDS)
def test_algorithm_discovery_order(algorithm_orders, dataset, algorithm):
    concepts = algorithm_orders[dataset][algorithm]
    builder, state = _build(concepts)
    _assert_matches_reference(concepts, builder)
    # ids are discovery order and replayed nodes carry the exact extents/intents
    for node_id, (extent, intent) in enumerate(concepts):
        assert state.nodes[node_id] == (extent, intent)
    assert state.edges == builder.edges


@pytest.mark.parametrize("dataset", ["fca_airlines", "fca_benchmark_20x12"])
def test_random_permutations(algorithm_orders, dataset):
    """Order independence, including permutations where the top concept is NOT first."""
    base = algorithm_orders[dataset]["NextClosure"]
    rng = random.Random(42)
    for i in range(20):
        shuffled = list(base)
        rng.shuffle(shuffled)
        if i == 0:  # make sure the "top not first" case is exercised deterministically
            top = max(range(len(base)), key=lambda k: len(base[k][0]))
            shuffled.sort(key=lambda c: c == base[top])  # top last
        builder, _ = _build(shuffled)
        _assert_matches_reference(shuffled, builder)


def test_random_permutations_40x20(algorithm_orders):
    base = algorithm_orders["fca_benchmark_40x20"]["CloseByOne"]
    rng = random.Random(7)
    for _ in range(3):
        shuffled = list(base)
        rng.shuffle(shuffled)
        builder, _ = _build(shuffled)
        _assert_matches_reference(shuffled, builder)


def test_duplicate_is_noop_without_new_id():
    builder = LatticeBuilder()
    first = builder.add({0, 1}, set())
    again = builder.add([1, 0], [])
    assert first.is_new and not again.is_new
    assert again.node_id == first.node_id
    assert again.ops() == []
    assert len(builder) == 1 and builder.edges == set()


def test_same_extent_different_intent_is_rejected():
    builder = LatticeBuilder()
    builder.add({0}, {1})
    with pytest.raises(ValueError):
        builder.add({0}, {2})


def test_insert_between_replaces_edge():
    """Chain top > bottom, then insert a middle concept: remove_edge + two add_edges."""
    builder = LatticeBuilder()
    top = builder.add({0, 1, 2}, set())
    bottom = builder.add(set(), {0, 1})
    assert builder.edges == {(top.node_id, bottom.node_id)}

    middle = builder.add({1}, {0})
    assert middle.parents == (top.node_id,)
    assert middle.children == (bottom.node_id,)
    assert middle.removed_edges == ((top.node_id, bottom.node_id),)
    assert set(middle.added_edges) == {(top.node_id, 2), (2, bottom.node_id)}
    assert builder.edges == {(0, 2), (2, 1)}

    kinds = [op.op for op in middle.ops()]
    assert kinds == ["add_node", "remove_edge", "add_edge", "add_edge"]


def test_multiple_parents_and_children():
    #        top
    #       /   \
    #      A     B        new concept N = A∩B extent-wise sits below both
    #       \   /
    #         N
    #         |
    #       bottom
    builder = LatticeBuilder()
    top = builder.add({0, 1, 2, 3}, set()).node_id
    a = builder.add({0, 1, 2}, {0}).node_id
    b = builder.add({1, 2, 3}, {1}).node_id
    bottom = builder.add(set(), {0, 1, 2}).node_id
    n = builder.add({1, 2}, {0, 1})

    assert set(n.parents) == {a, b}
    assert n.children == (bottom,)
    # bottom was attached directly below A and B before N existed
    assert set(n.removed_edges) == {(a, bottom), (b, bottom)}
    assert builder.edges == {(top, a), (top, b), (a, n.node_id), (b, n.node_id), (n.node_id, bottom)}


def test_non_child_descendant_gets_linked():
    """Regression for ConceptLattice.add_concept's flaw: a new concept inserted above a
    node that is NOT a direct child of its parents must still become that node's parent."""
    builder = LatticeBuilder()
    top = builder.add({0, 1, 2, 3}, set()).node_id
    q = builder.add({0, 1}, {0}).node_id        # top -> q
    c = builder.add({0}, {0, 1}).node_id         # q -> c
    x = builder.add({0, 2}, {2})                 # incomparable with q; above c; below top
    assert x.parents == (top,)
    assert x.children == (c,)
    assert builder.edges == {(top, q), (q, c), (top, x.node_id), (x.node_id, c)}


def test_ops_are_sorted_and_deterministic():
    concepts = [
        (frozenset({0, 1, 2}), frozenset()),
        (frozenset({2}), frozenset({1})),
        (frozenset({0, 2}), frozenset({0})),
    ]
    runs = []
    for _ in range(2):
        builder = LatticeBuilder()
        runs.append([[o.model_dump() for o in builder.add(e, i).ops()] for e, i in concepts])
    assert runs[0] == runs[1]
