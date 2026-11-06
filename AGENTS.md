# FCA-Project Agent Guide

This file is the repository's operational map for future coding agents. Read it
before changing code. The project is a small, research-oriented Python
implementation of Formal Concept Analysis (FCA): it reads a binary formal
context, enumerates formal concepts with several algorithms, and builds/draws a
concept lattice. There is no production web application in the current
checkout, despite the README diagrams referring to a future FastAPI/React
visualisation.

## Repository status and scope

- The repository is `Aryan-Bodhe/FCA-Project`.
- There is no `pyproject.toml`, `setup.py`, `requirements.txt`, lockfile,
  Makefile, CI configuration, or configured package runner.
- The code is not installed as a package. Imports assume `backend` is on
  `sys.path` (normally by running from `backend/` or setting
  `PYTHONPATH=backend`).
- The current worktree may contain local changes in
  `backend/graphing/concept_graph.py` and `backend/main.py`, an untracked
  `backend/resch.ipynb`, an untracked root `hasse_diagram.png`, and generated
  `__pycache__` directories. Do not discard those changes while working.
- `backend/temp/` and `backend/testing/` are ignored by `.gitignore`, but
  files currently exist there and are part of the local research workspace.
- The root `app.py` and `frontend/main.py` are empty placeholders.

## Architecture

The active implementation has three layers:

1. **Context/model layer** (`backend/models/`): converts a pandas DataFrame or
   CSV into a normalized integer-indexed formal context and represents a
   formal concept.
2. **Algorithm layer** (`backend/algorithms/`): enumerates closed attribute
   sets using NextClosure, Close-by-One, or In-Close. All active algorithms
   yield `FormalConcept` instances lazily.
3. **Graphing layer** (`backend/graphing/`): consumes the yielded concepts and
   incrementally constructs a NetworkX directed acyclic graph representing
   the concept order. `ConceptLattice.draw()` renders it with matplotlib.

The intended pipeline is:

```text
CSV/DataFrame
  -> FormalContext (labels mapped to integer indices)
  -> algorithm.run() generator
  -> FormalConcept objects with original labels restored
  -> ConceptLattice
  -> NetworkX graph / matplotlib drawing
```

`backend/README.md` describes a planned architecture in which algorithms emit
trace events to a FastAPI service and a React Flow/ELK.js frontend displays
them. That architecture is not implemented in this checkout. Do not invent
API routes or frontend behavior without first implementing them.

## Formal Concept Analysis model

The relation is a Boolean incidence matrix `I`:

- rows are objects `G`;
- columns are attributes `M`;
- `I[g][m]` is truthy when object `g` has attribute `m`.

The active code normalizes labels to integer indices:

- `FormalContext.objects` becomes `[0, 1, ..., n-1]`;
- `FormalContext.attributes` becomes `[0, 1, ..., m-1]`;
- `object_map` and `attribute_map` retain the original pandas index/column
  labels.

The derivation operators used by the algorithms are:

- `objects'` for an attribute set: the intersection of rows containing every
  selected attribute;
- `attributes'` for an object set: the intersection of attributes present on
  every selected object;
- attribute closure `A''`: derive objects from `A`, then derive attributes
  from those objects.

Empty intersections intentionally use the complete universe at the start:
`compute_extent([])` returns all objects and `compute_intent([])` returns all
attributes. Empty object/attribute sets therefore have normal FCA semantics.

### Ordering and concept comparison

`FormalConcept` compares concepts as lattice elements:

- `c1 <= c2` means `c1.objects ⊆ c2.objects` **and**
  `c1.attributes ⊇ c2.attributes`;
- strict comparisons use `<=` plus inequality;
- equality compares object and attribute sets, not list ordering;
- `is_incomparable()` is the negation of either direction.

This order is important: adding attributes moves downward in the concept
lattice and reduces the extent. Do not replace it with a conventional
same-direction subset comparison.

## File-by-file map

### Root files

- [`AGENTS.md`](./AGENTS.md): this guide. Keep it synchronized with the
  implementation when behavior, commands, or file roles change.
- [`.gitignore`](./.gitignore): ignores `temp/` and `testing/` by directory
  name. It does **not** currently ignore Python caches, notebook checkpoints,
  generated images, or other common build artifacts.
- [`app.py`](./app.py): empty root-level placeholder; no entry point.
- [`cleanup.py`](./cleanup.py): standalone cleanup utility. It recursively
  walks from the repository root, skips `.git`, virtual environments, and
  `node_modules`, removes directories named like `__pycache__`, `.pytest_cache`,
  `build`, `dist`, `logs`, etc., and removes `*.pyc`, `*.pyo`, `*.log`, and
  `.coverage`. It prints every removal and a final count. It is destructive
  within its explicit allowlist; do not broaden its patterns casually.
- [`hasse_diagram.png`](./hasse_diagram.png): local/generated PNG output,
  currently untracked. It is not source and should not be used as an API or
  test fixture unless deliberately promoted to a tracked asset.

### Models

- [`backend/models/__init__.py`](./backend/models/__init__.py): public model
  exports. Import `FormalContext` and `FormalConcept` from `models` when
  running with `backend` on the import path.
- [`backend/models/concept.py`](./backend/models/concept.py): `FormalConcept`
  stores `objects` and `attributes` lists without validation or copying.
  Equality and ordering treat them as sets. It has no `__repr__`, hashing, or
  serialization. Preserve the set semantics when adding behavior.
- [`backend/models/context.py`](./backend/models/context.py):
  `FormalContext(objects, attributes, relations)` stores the incidence matrix,
  computes `shape`, and immediately replaces the public object/attribute
  sequences with integer ranges while retaining maps to original labels.
  `from_csv(path)` calls `pandas.read_csv(..., index_col=0)`;
  `from_pandas(df)` uses the DataFrame index and columns and converts
  `to_numpy().tolist()`. `save()` is an unimplemented placeholder. Inputs are
  not shape-checked, coerced to bool, or copied defensively.

### Algorithms

- [`backend/algorithms/__init__.py`](./backend/algorithms/__init__.py):
  exports `NextClosure`, `CloseByOne`, and `InClose` through `__all__`.
- [`backend/algorithms/base.py`](./backend/algorithms/base.py):
  `BaseAlgorithm` owns a context and an unused `concepts` list. Its `_step()`
  and `run()` are placeholders. `derive_objects(m)` and
  `derive_attributes(g)` scan the normalized relation. `intersection()` is a
  list-preserving helper; `is_subset()` converts both operands to sets.
  `closure_of_attributes()` computes `A''`; `compute_extent()` and
  `compute_intent()` implement one derivation each; `remap_concept()` computes
  an extent from an integer intent and restores original labels. These methods
  currently use linear list intersections, so performance is deliberately
  simple rather than optimized.
- [`backend/algorithms/nextclosure.py`](./backend/algorithms/nextclosure.py):
  `NextClosure._step(found_concept)` scans attributes in reverse lectic order,
  creates a candidate prefix plus one attribute, closes it, and accepts it
  only when the closure does not alter the prefix before that attribute.
  `run()` yields the closure of the empty intent first, then repeatedly yields
  the next closed intent until it equals all attributes or no candidate exists.
  It is a generator; never call `len(algo.run())` without materializing it.
- [`backend/algorithms/closebyone.py`](./backend/algorithms/closebyone.py):
  `CloseByOne._step(A, y)` recursively tests attributes from `y`, closes
  `A + [i]`, and applies the canonical-prefix test
  `A[:i] == C[:i]` expressed through `intersection`. `run()` yields the empty
  closure and recursively discovered closures. It relies on attributes being
  normalized, ordered integers.
- [`backend/algorithms/inclose.py`](./backend/algorithms/inclose.py):
  `InClose._step(objects, attributes, index)` recursively intersects the
  current extent with each candidate attribute extent. Attributes that do not
  reduce the extent are appended directly; reducing candidates are accepted
  only if no earlier unselected attribute contains the new extent. An empty
  new extent yields the full attribute list; otherwise recursion continues and
  then yields the new attribute list. `run()` seeds recursion from the closure
  of the empty intent. Be careful with mutable `attributes.append(i)`: this is
  the algorithm's current state-sharing behavior.

All three active implementations return labeled `FormalConcept` objects, but
their output order is algorithm-specific. Compare concept collections using
canonical sets of `(frozenset(objects), frozenset(attributes))`, as shown in
the research scripts, rather than comparing lists.

### Graphing

- [`backend/graphing/concept_graph.py`](./backend/graphing/concept_graph.py):
  `ConceptLattice` wraps a `networkx.DiGraph`. Construction sorts concepts by
  descending extent size, inserts the first as the top node, incrementally
  inserts the rest, validates node/concept counts and acyclicity, and
  finalizes compact object storage.
  
  Each node initially has:
  - `objects`: the complete extent;
  - `attributes_delta`: attributes contributed at that node;
  - `level`: insertion-derived lattice level.

  `finalize_object_storage()` computes `objects_delta` by subtracting direct
  child extents, deletes complete `objects`, and sets `finalized=True`.
  After finalization, full object sets are reconstructed from descendants and
  full attribute sets from ancestors. Public helpers include
  `get_parents`, `get_children`, `get_siblings`, `get_node_attributes`,
  `get_node_objects`, `get_node_label`, `get_full_attributes`,
  `get_full_objects`, and `get_concept`.

  `add_concept()` refuses changes after finalization, suppresses duplicates,
  finds immediate parents using the concept order, redirects child edges, and
  stores only attribute deltas. `ConceptLattice([])` raises `ValueError`.
  `_validate()` assumes the input order after sorting corresponds to node
  insertion order. Any changes to sorting or edge insertion must preserve
  concept reconstruction and the DAG invariant.

  `draw()` uses `networkx.multipartite_layout` grouped by `level`, flips the
  vertical coordinate so the top is visually higher, labels nodes with stored
  object/attribute deltas, and renders using matplotlib. It does not save or
  return a figure explicitly.
- [`backend/graphing/hasse_diagram.py`](./backend/graphing/hasse_diagram.py):
  older skeletal alternative with `HasseNode` (concept plus parent/child
  lists) and `HasseDiagram`. `construct()` is unimplemented and
  `self.graph` starts as `None`. Do not assume it is wired to
  `ConceptLattice`.

### Entrypoints and experiments

- [`backend/main.py`](./backend/main.py): current demo entrypoint. It selects
  the TkAgg matplotlib backend, loads `data/fca_airlines.csv` with a
  repository-root-relative path, builds a `FormalContext`, enumerates
  `NextClosure` with a 1 ms display delay, builds a `ConceptLattice`, prints
  node/edge counts, and calls `draw()`. The commented benchmark line can
  switch to the 20x12 dataset. It imports with `from algorithms import *`,
  which is convenient but should be replaced with explicit imports if this
  becomes production code. Running it requires both correct `PYTHONPATH` and a
  display; its import path and data path currently make “run from root” and
  “run from backend” disagree, so resolve that deliberately rather than
  papering over one symptom.
- [`frontend/main.py`](./frontend/main.py): empty frontend placeholder.
- [`backend/README.md`](./backend/README.md): architecture sketch for a
  future FastAPI JSON backend plus React Flow/ELK.js UI. It is descriptive,
  not an implementation contract yet.
- [`frontend/README.md`](./frontend/README.md): one-line statement that the
  frontend is for FCA algorithm visualization; no setup instructions.

### Notebooks and legacy prototypes

These are exploratory artifacts, not reliable library tests. Preserve their
historical value, but do not use them as the source of truth for the active
`backend/models` and `backend/algorithms` APIs without updating them.

- [`backend/notebooks/analysis.ipynb`](./backend/notebooks/analysis.ipynb):
  early benchmark notebook. It imports third-party `fcapy` APIs as well as
  local `NextClosure`/`CloseByOne`, loads the three benchmark CSVs, preprocesses
  the first column as `object_id`, runs timing comparisons, and plots a
  logarithmic algorithm comparison. Several imports and call shapes target an
  older API.
- [`backend/notebooks/cbo.ipynb`](./backend/notebooks/cbo.ipynb): notebook
  version of the three-algorithm comparison on the 40x20 benchmark. It
  canonicalizes generated concepts into frozenset pairs and prints equality
  comparisons between NextClosure, CloseByOne, and InClose.
- [`backend/notebooks/courses.ipynb`](./backend/notebooks/courses.ipynb):
  synthetic 10-object/20-attribute context with a hard-coded NumPy matrix.
  It imports `NextClosure, Context` from the old `nextclosure.py` prototype,
  runs a few cells, and prints concepts. It does not use
  `models.FormalContext`.
- [`backend/notebooks/inclose.ipynb`](./backend/notebooks/inclose.ipynb):
  benchmark of the external `fca` package's `Context.get_concepts()` on the
  20x12 CSV. It is not a benchmark of the active local `InClose`.
- [`backend/notebooks/course.py`](./backend/notebooks/course.py): old script
  containing a 10x20 NumPy context and imports of the obsolete `Context`
  symbol from `algorithms.nextclosure`; it will not work against the current
  module without refactoring.
- [`backend/notebooks/nextclos.py`](./backend/notebooks/nextclos.py):
  self-contained predecessor implementation. It defines its own dataclass
  `Context`, `Concept`, and `NextClosure`, including preparation, derivation,
  closure, remapping, and a hard-coded five-airline example. Its `run()`
  prints concepts and returns nothing; it is separate from the active
  generator implementation.
- [`backend/resch.ipynb`](./backend/resch.ipynb): untracked research notebook
  based on the active `algorithms` and `models` packages. It loads the
  airline context, runs each local algorithm, canonicalizes outputs, and
  compares their concept sets; later cells build a lattice and inspect graph
  behavior. Treat it as local research unless explicitly added to version
  control.

### Testing and temporary experiments

- [`backend/testing/test_algo_correctness.py`](./backend/testing/test_algo_correctness.py):
  older benchmark/correctness script intended to compare algorithms. It calls
  obsolete APIs (`algo.prepare`, constructorless algorithms, and `len` on
  results) and is not currently aligned with the active generator design.
- [`backend/testing/test_library.py`](./backend/testing/test_library.py):
  older external-library benchmark using `fca.api_models.Context`; it is not
  a pytest test despite its name.
- [`backend/testing/test.py`](./backend/testing/test.py): empty/near-empty
  experimental test placeholder.
- [`backend/testing/see.py`](./backend/testing/see.py): currently empty.
- [`backend/temp/gviz.py`](./backend/temp/gviz.py): Graphviz experiment that
  creates a four-node illustrative graph and repeatedly renders
  `hasse_diagram.png` with `view=True`; it is not connected to
  `ConceptLattice` and may require the Graphviz executable and a GUI.

## Data files

All CSVs are comma-separated Boolean incidence tables with the first column
being the object identifier and the remaining columns attributes. The active
loader uses `index_col=0`, so keep that leading identifier column.

- [`data/fca_airlines.csv`](./data/fca_airlines.csv): 5 airlines × 9
  attributes, the default demo. Labels include `Air_Canada`, `Europe`, and
  the source spelling `Carribean`.
- [`data/fca_benchmark_20x12.csv`](./data/fca_benchmark_20x12.csv): 20
  objects × 12 generated attributes.
- [`data/fca_benchmark_40x20.csv`](./data/fca_benchmark_40x20.csv): 40
  objects × 20 generated attributes.
- [`data/fca_benchmark_100x50.csv`](./data/fca_benchmark_100x50.csv): 100
  objects × 50 generated attributes. Concept enumeration can grow
  exponentially; do not use it casually in an interactive run.

Do not silently rename labels, transpose matrices, or change the index-column
convention. If accepting a new input format, add explicit normalization and
tests rather than changing `from_csv` semantics invisibly.

## Running and validating changes

There is no declared environment, so first inspect the available Python and
install only dependencies required by the code being exercised. The core
runtime imports pandas, NetworkX, and (for drawing) matplotlib. NumPy,
Graphviz, `fcapy`, and `fca` are used only by experiments/prototypes.

From the repository root, the safest import setup is:

```bash
PYTHONPATH=backend python3 -m backend.main
```

However, `backend/main.py` currently reads `data/...` relative to the current
working directory and selects `TkAgg`, so a headless environment may fail at
the display step. For algorithm-only work, use a small script or an interactive
session with `PYTHONPATH=backend` and avoid `draw()`.

Useful focused checks:

```bash
python3 -m compileall backend cleanup.py
PYTHONPATH=backend python3 - <<'PY'
import pandas as pd
from algorithms import NextClosure, CloseByOne, InClose
from models import FormalContext

context = FormalContext.from_pandas(
    pd.read_csv("data/fca_airlines.csv", index_col=0)
)
for algorithm_type in (NextClosure, CloseByOne, InClose):
    concepts = list(algorithm_type(context).run())
    print(algorithm_type.__name__, len(concepts))
PY
```

When comparing algorithms, compare canonical concept sets, not generator
identity or enumeration order:

```python
{
    (frozenset(concept.objects), frozenset(concept.attributes))
    for concept in concepts
}
```

The existing files under `backend/testing/` are stale scripts rather than a
working test suite. If fixing them, first migrate them to the current
constructor and generator APIs, then use a real test runner and include
cross-algorithm canonical-set checks on the small datasets.

## Coding rules and invariants

1. Keep the integer-index normalization boundary in `FormalContext`. Algorithms
   should operate on integer indices and only expose original labels through
   `remap_concept()`.
2. Preserve generator laziness. Algorithm `run()` methods must yield concepts
   incrementally so callers can observe progress or stop early.
3. Do not mutate a caller's DataFrame, object labels, or relation matrix
   unexpectedly. Existing code does not fully enforce this, so make any
   strengthening explicit and test it.
4. Maintain set-based concept semantics even if storage remains lists.
5. Keep attribute order stable. NextClosure and Close-by-One canonical tests
   depend on integer attribute ordering.
6. If changing lattice insertion, validate node count, reconstructed extents
   and intents, and acyclicity. Test both duplicate concepts and concepts with
   multiple parents.
7. Prefer explicit imports in new code. Existing absolute imports such as
   `from models...` are a consequence of the current non-installed
   `backend`-on-`sys.path` layout.
8. Avoid adding dependencies without a manifest. If a dependency becomes
   required, add an appropriate dependency declaration and update this guide.
9. Keep experimental notebooks and old prototypes separate from the active
   implementation unless deliberately migrating them.
10. Do not claim FastAPI, React, ELK, Graphviz, or external FCA-library
    support is active merely because a README or notebook mentions it.

## Known gaps and likely maintenance work

The following are real implementation gaps, not instructions to fix them
unasked:

- `FormalContext.save()` is a placeholder.
- `BaseAlgorithm._step()` and `BaseAlgorithm.run()` are placeholders intended
  for an abstract base but are not abstract methods.
- `HasseDiagram.construct()` is a placeholder.
- Root and frontend entrypoints are empty.
- Input dimensions and Boolean values are not validated.
- There is no packaging, dependency pinning, CLI, web server, or automated CI.
- The active demo has inconsistent import/data path assumptions and requires a
  GUI backend for drawing.
- Existing benchmark scripts target obsolete APIs.

Address gaps surgically when requested; do not rewrite the research project
into a framework as an incidental cleanup.

## Change checklist

Before editing:

- Read the relevant model, algorithm, and graphing files together.
- Check `git status` and preserve unrelated worktree changes.
- Decide whether the change belongs to active code or an exploratory artifact.

After editing:

- Run `python3 -m compileall` or the narrowest applicable check.
- Materialize and compare algorithm outputs on `fca_airlines.csv` when
  touching closure logic.
- Validate lattice reconstruction and DAG invariants when touching graphing.
- Check paths from the intended working directory and avoid GUI-only
  validation in headless environments.
- Update this guide if file roles, commands, public APIs, or invariants change.
