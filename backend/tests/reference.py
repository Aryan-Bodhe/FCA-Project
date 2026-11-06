"""Brute-force reference FCA enumerator used to validate the real algorithms.

Deliberately naive and independent of `algorithms.base`: enumerate every subset
of attributes, keep the closed ones.
"""

from __future__ import annotations

from itertools import combinations


def bruteforce_concepts(
    objects: list, attributes: list, matrix: list[list[int]]
) -> set[tuple[frozenset, frozenset]]:
    """All formal concepts as {(frozenset(extent), frozenset(intent))} using labels.

    `matrix[g][m]` truthy <=> object g has attribute m; `objects`/`attributes`
    give the labels in row/column order.
    """
    n, m = len(objects), len(attributes)
    concepts: set[tuple[frozenset, frozenset]] = set()
    for size in range(m + 1):
        for subset in combinations(range(m), size):
            extent = [g for g in range(n) if all(matrix[g][j] for j in subset)]
            intent = [j for j in range(m) if all(matrix[g][j] for g in extent)]
            if set(intent) == set(subset):  # closed attribute set
                concepts.add(
                    (
                        frozenset(objects[g] for g in extent),
                        frozenset(attributes[j] for j in intent),
                    )
                )
    return concepts


def hasse_reference(extents: list[frozenset]) -> set[tuple[frozenset, frozenset]]:
    """Independent reference for the covering relation, keyed by extent.

    Builds the strict-order DAG (parent extent ⊃ child extent) over all concepts
    and takes its transitive reduction with networkx. Returns {(parent_extent,
    child_extent)}.
    """
    import networkx as nx

    graph = nx.DiGraph()
    graph.add_nodes_from(range(len(extents)))
    for i, a in enumerate(extents):
        for j, b in enumerate(extents):
            if a > b:
                graph.add_edge(i, j)
    reduced = nx.transitive_reduction(graph)
    return {(extents[i], extents[j]) for i, j in reduced.edges}
