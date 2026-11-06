"""Cross-algorithm agreement on the committed benchmark datasets.

The 100x50 dataset is intentionally NOT used: enumeration can explode.
"""

from __future__ import annotations

import pytest

from algorithms import CloseByOne, InClose, NextClosure

from helpers import canonical, load_context

ALGORITHMS = [NextClosure, CloseByOne, InClose]
ALGORITHM_IDS = [a.__name__ for a in ALGORITHMS]
DATASETS = ["fca_airlines", "fca_benchmark_20x12", "fca_benchmark_40x20"]

# Verified against the independent brute-force reference (backend/tests/reference.py).
AIRLINES_CONCEPT_COUNT = 6
BENCHMARK_20X12_CONCEPT_COUNT = 88


@pytest.fixture(scope="module")
def results():
    """{dataset: {algorithm name: list[FormalConcept]}}, computed once."""
    out = {}
    for name in DATASETS:
        context = load_context(name)
        out[name] = {a.__name__: list(a(context).run()) for a in ALGORITHMS}
    return out


@pytest.mark.parametrize("dataset", DATASETS)
def test_all_algorithms_agree(results, dataset):
    sets = {alg: canonical(cs) for alg, cs in results[dataset].items()}
    reference = sets["NextClosure"]
    for alg, got in sets.items():
        assert got == reference, f"{alg} disagrees with NextClosure on {dataset}"


@pytest.mark.parametrize("dataset", DATASETS)
@pytest.mark.parametrize("algorithm", ALGORITHM_IDS)
def test_no_duplicates(results, dataset, algorithm):
    concepts = results[dataset][algorithm]
    assert len(concepts) == len(canonical(concepts))


def test_airlines_concept_count_is_pinned(results):
    for alg, concepts in results["fca_airlines"].items():
        assert len(concepts) == AIRLINES_CONCEPT_COUNT, alg


def test_20x12_concept_count_is_pinned(results):
    for alg, concepts in results["fca_benchmark_20x12"].items():
        assert len(concepts) == BENCHMARK_20X12_CONCEPT_COUNT, alg


@pytest.mark.parametrize("dataset", DATASETS)
@pytest.mark.parametrize("algorithm", ALGORITHM_IDS)
def test_first_concept_is_top_concept(results, dataset, algorithm):
    """The trace builder relies on the first yielded concept being the top
    concept (extent = all objects)."""
    context = load_context(dataset)
    all_objects = {context.object_map[i] for i in context.objects}
    first = results[dataset][algorithm][0]
    assert set(first.objects) == all_objects


@pytest.mark.parametrize("dataset", DATASETS)
@pytest.mark.parametrize("algorithm", ALGORITHM_IDS)
def test_concepts_are_closed_pairs(results, dataset, algorithm):
    """Each yielded (extent, intent) must be a genuine concept: the intent is
    exactly the set of attributes shared by all objects of the extent."""
    import pandas as pd

    from helpers import DATA_DIR

    df = pd.read_csv(DATA_DIR / f"{dataset}.csv", index_col=0).astype(bool)
    for c in results[dataset][algorithm]:
        objs, attrs = list(c.objects), list(c.attributes)
        sub = df.loc[objs] if objs else df.iloc[0:0]
        common = set(df.columns) if not objs else set(sub.columns[sub.all(axis=0)])
        assert set(attrs) == common
        having_all = set(df.index[df[attrs].all(axis=1)]) if attrs else set(df.index)
        assert set(objs) == having_all
