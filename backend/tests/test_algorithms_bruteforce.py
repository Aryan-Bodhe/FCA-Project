"""Validate every algorithm against an independent brute-force enumerator."""

from __future__ import annotations

import random

import pandas as pd
import pytest

from algorithms import CloseByOne, InClose, NextClosure
from models import FormalContext

from helpers import DATA_DIR, canonical, context_from_matrix
from reference import bruteforce_concepts

ALGORITHMS = [NextClosure, CloseByOne, InClose]
ALGORITHM_IDS = [a.__name__ for a in ALGORITHMS]

# Edge-case contexts (rows = objects, columns = attributes).
EDGE_CASES = {
    "1x1_one": [[1]],
    "1x1_zero": [[0]],
    "all_zero_3x3": [[0] * 3 for _ in range(3)],
    "all_one_3x3": [[1] * 3 for _ in range(3)],
    "identity_4x4": [[int(i == j) for j in range(4)] for i in range(4)],
    "anti_identity_4x4": [[int(i != j) for j in range(4)] for i in range(4)],
    "one_zero_row": [[1, 1, 0], [0, 0, 0], [1, 0, 1]],
    "one_full_row": [[1, 1, 1], [1, 0, 0], [0, 1, 0]],
    "all_one_column": [[1, 0, 1], [1, 1, 0], [1, 0, 0]],
    "all_zero_column": [[0, 1, 1], [0, 1, 0], [0, 0, 1]],
    "duplicate_rows": [[1, 0, 1], [1, 0, 1], [0, 1, 1]],
    "duplicate_columns": [[1, 1, 0], [0, 0, 1], [1, 1, 1]],
    "wide_1x6": [[1, 0, 1, 1, 0, 1]],
    "tall_6x1": [[1], [0], [1], [1], [0], [1]],
}


def _random_matrix(rng: random.Random) -> list[list[int]]:
    n = rng.randint(1, 6)
    m = rng.randint(1, 6)
    density = rng.choice([0.1, 0.3, 0.5, 0.7, 0.9])
    return [[int(rng.random() < density) for _ in range(m)] for _ in range(n)]


RANDOM_CASES = {}
_rng = random.Random(20260106)
for _i in range(50):
    RANDOM_CASES[f"random_{_i:02d}"] = _random_matrix(_rng)

ALL_CASES = {**EDGE_CASES, **RANDOM_CASES}


def _expected(context: FormalContext, matrix: list[list[int]]):
    objects = [context.object_map[i] for i in context.objects]
    attributes = [context.attribute_map[i] for i in context.attributes]
    return bruteforce_concepts(objects, attributes, matrix)


@pytest.mark.parametrize("algorithm", ALGORITHMS, ids=ALGORITHM_IDS)
@pytest.mark.parametrize("name", list(ALL_CASES))
def test_matches_bruteforce(algorithm, name):
    matrix = ALL_CASES[name]
    context = context_from_matrix(matrix)
    produced = list(algorithm(context).run())

    expected = _expected(context, matrix)
    got = canonical(produced)

    assert got == expected, f"{algorithm.__name__} on {name}: set mismatch"
    assert len(produced) == len(got), f"{algorithm.__name__} on {name}: duplicate concepts"


@pytest.mark.parametrize("algorithm", ALGORITHMS, ids=ALGORITHM_IDS)
@pytest.mark.parametrize("name", ["fca_airlines", "fca_benchmark_20x12"])
def test_matches_bruteforce_on_datasets(algorithm, name):
    df = pd.read_csv(DATA_DIR / f"{name}.csv", index_col=0)
    context = FormalContext.from_pandas(df)
    matrix = df.to_numpy().tolist()

    produced = list(algorithm(context).run())
    got = canonical(produced)

    assert got == _expected(context, matrix)
    assert len(produced) == len(got), "duplicate concepts"
