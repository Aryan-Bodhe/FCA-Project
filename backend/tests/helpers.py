"""Shared helpers for backend tests.

`pytest` is configured (pyproject.toml) with `pythonpath = ["backend"]`, so
`from models import ...` / `from algorithms import ...` work in tests.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from models import FormalContext

# backend/tests/helpers.py -> parents[0]=tests, [1]=backend, [2]=repo root
DATA_DIR = Path(os.environ.get("FCA_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))


def load_context(name: str) -> FormalContext:
    """Load a dataset from the data directory by file stem, e.g. 'fca_airlines'."""
    df = pd.read_csv(DATA_DIR / f"{name}.csv", index_col=0)
    return FormalContext.from_pandas(df)


def context_from_matrix(matrix: list[list[int]]) -> FormalContext:
    """Build a FormalContext from a 0/1 matrix with labels g0.. / m0.. ."""
    n = len(matrix)
    m = len(matrix[0]) if n else 0
    df = pd.DataFrame(
        matrix,
        index=[f"g{i}" for i in range(n)],
        columns=[f"m{j}" for j in range(m)],
    )
    return FormalContext.from_pandas(df)


def canonical(concepts) -> set[tuple[frozenset, frozenset]]:
    """Canonical set form of a concept collection (order-independent)."""
    return {(frozenset(c.objects), frozenset(c.attributes)) for c in concepts}
