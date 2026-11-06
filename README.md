# FCA-Project

Formal Concept Analysis (FCA): enumerate formal concepts with several algorithms
(NextClosure, Close-by-One, In-Close) and build the concept lattice. A
step-by-step web visualiser is being built — see [`PLAN.md`](./PLAN.md) for the
roadmap and [`AGENTS.md`](./AGENTS.md) for the repository map and invariants.

## Dev setup

Python 3.10+ is required (developed on 3.13). The code is **not** an installable
package: `backend/` is put on the import path via `PYTHONPATH` (or pytest's
`pythonpath` setting).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pandas networkx pytest          # enough for the algorithms + tests
# needed from the API chunk (C1) onwards:
pip install fastapi "uvicorn[standard]" pydantic httpx
```

> `pyproject.toml` only declares dependencies and tool config (it is not a
> package definition, so `pip install .` is not supported). Install the
> libraries it lists with pip directly, as above.

### Run the tests

From the repository root:

```bash
python3 -m pytest
```

Tests live in `backend/tests/` (not `backend/testing/`, which is gitignored and
holds stale research scripts).

### Quick algorithm check (no GUI)

```bash
PYTHONPATH=backend python3 - <<'PY'
import pandas as pd
from algorithms import NextClosure, CloseByOne, InClose
from models import FormalContext

context = FormalContext.from_pandas(pd.read_csv("data/fca_airlines.csv", index_col=0))
for algorithm_type in (NextClosure, CloseByOne, InClose):
    print(algorithm_type.__name__, len(list(algorithm_type(context).run())))
PY
```

### Demo (requires a display)

```bash
PYTHONPATH=backend python3 -m backend.main
```

`backend/main.py` selects the TkAgg matplotlib backend and has path assumptions
that currently differ between "run from root" and "run from backend"; it is a
research demo, not the web app.
