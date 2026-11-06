# FCA Lattice Visualiser — Project Plan

Status: planning complete, implementation not started.
Companion docs: `AGENTS.md` (repo map & invariants — read it first), `backend/README.md` (original architecture sketch).

---

## 0. How to use this plan (read this first, every time)

This plan is split into **chunks** (A1, A2, B1 … E2). Each chunk is sized for one agent session and is
written so it can be done **without any knowledge of earlier conversations**.

**Resume protocol for any agent:**

1. Read `AGENTS.md`, then **§1–§6 of this file** (goals, decisions, contracts, layout, conventions).
2. Read **only the chunk you were told to resume** (plus the chunks listed under its `Depends on`, skimming their "Done when").
3. Check the **Progress Log (§9)** for notes left by previous agents (deviations, gotchas).
4. Run `git status`. **Preserve existing uncommitted work** (esp. `backend/graphing/concept_graph.py`, `backend/main.py`, `backend/resch.ipynb`, `hasse_diagram.png`). Never `git stash`, `git checkout .`, or run `cleanup.py` without being asked.
5. Do the chunk. Meet every "Done when" item. Do not start the next chunk.
6. Before stopping (even if hitting a limit mid-chunk): update the **Progress Log (§9)** — status, what was done, what is left, any deviations from this plan.

**Copy-paste resume prompt for the user:**

> Continue the FCA visualiser project. Follow the resume protocol in `PLAN.md` §0. Resume from chunk **<ID>**. If the Progress Log says it is partially done, finish it; otherwise start it fresh.

---

## 1. Goals

**G1.** Interactive web app showing the **step-by-step construction** of a concept lattice. The user clicks **Next / Back** to move one step at a time.

**G2.** UI contains:
- a **dataset selector**,
- an **algorithm selector** (NextClosure, Close-by-One, In-Close),
- a **controls bar** for stepping (first / back / next / last / slider, plus play as a cheap extra),
- a **node-data display selector**: by default nodes are small and clean; **hovering a node shows its data** (extent + intent). Modes: `Hover` (default), `Labels` (always show reduced labels), `Off`.
  *(Interpretation note: if a plain on/off toggle was intended, drop `Labels` in D6.)*

**Non-goals (for now):** auth, DB, multi-user, deployment infra, editing datasets in-browser, replacing the research notebooks.

**MVP milestone** = A1–A2, B1–B5, C1, D1–D6 complete. D7/E1/E2 are hardening and extras.

---

## 2. Key decisions

| # | Decision | Choice | Why / alternatives |
|---|----------|--------|--------------------|
| 1 | Where does the step sequence come from? | **Backend precomputes the entire trace** (list of steps) and returns it as JSON in one request. | Next/Back becomes pure client-side navigation; no server session state, easy to test, easy to cache. Streaming is a stretch item for huge lattices. |
| 2 | Backend | **Python + FastAPI + Uvicorn + Pydantic v2** | Reuses existing algorithms directly; already named in `backend/README.md`. |
| 3 | Frontend | **React + TypeScript + Vite** | Matches README sketch; fast dev loop. |
| 4 | Graph rendering | **React Flow (`@xyflow/react`)** with custom node/edge components | Pan/zoom, hover events, custom nodes built in. |
| 5 | Layout | **ELK.js (`elkjs`, layered algorithm) in a Web Worker**, computed **once on the final lattice**; earlier steps only show/hide nodes at those fixed positions. | Re-laying out each step makes nodes jump and destroys the "watch it grow" feel. Per-step relayout is a stretch option. |
| 6 | Client state | **Zustand** | Small, simple: current trace, step index, display mode, pinned node. |
| 7 | Server data fetching | **TanStack Query** | Caching, loading/error states for datasets/algorithms/trace. |
| 8 | Styling | **Tailwind CSS** (no heavy component library) | Fast to build a clean, minimal UI. |
| 9 | API ↔ TS types | **OpenAPI → `openapi-typescript`** generated types | Single source of truth; avoids drift. |
| 10 | Tests | **pytest** (+ `httpx` TestClient) backend; **Vitest + React Testing Library** frontend; Playwright smoke test optional (E2). | |
| 11 | Package manager (frontend) | **npm** | Fewest moving parts. Pin versions in `package.json` at scaffold time (check latest stable then). |
| 12 | Backend packaging | **Do NOT convert to an installable package.** Keep `backend/` on `sys.path` (`pythonpath = ["backend"]` in pytest, `--app-dir backend` for uvicorn). Add a root `pyproject.toml` only for deps/tool config. | Matches `AGENTS.md` ("not installed as a package"); avoids a risky restructure. |
| 13 | Lattice incremental building | Trace builder diffs the lattice's edge set before/after each insertion to derive `add_edge` / `remove_edge` ops (see B2). | Works regardless of how `ConceptLattice` is implemented internally. |
| 14 | Step granularity | Two levels: **`concept`** (default; 1 step per discovered concept) and **`detailed`** (also steps for each candidate tested/rejected). Schema supports both from day one; UI for detailed is D7. | Delivers MVP fast without painting ourselves into a corner. |
| 15 | New test location | `backend/tests/` (NOT `backend/testing/` — that folder is gitignored). | |

---

## 3. Trace contract (the heart of the project)

JSON uses **camelCase** (Pydantic `alias_generator=to_camel`, `populate_by_name=True`; FastAPI serialises by alias). Python uses snake_case.

```jsonc
// Trace
{
  "version": 1,
  "meta": {
    "dataset": "fca_airlines",
    "algorithm": "next_closure",        // next_closure | close_by_one | in_close
    "granularity": "concept",           // concept | detailed
    "objects":    ["Air_Canada", "..."],// ORIGINAL labels as strings; index = integer id used everywhere below
    "attributes": ["Europe", "..."],
    "conceptCount": 19,                 // concepts actually included
    "stepCount": 21,
    "truncated": false,                 // true if maxConcepts/maxSteps cap hit -> lattice is partial
    "maxConcepts": 2000,
    "maxSteps": 5000
  },
  "steps": [ /* Step[] */ ]
}

// Step — steps[i].index === i
{
  "index": 3,
  "kind": "init" | "concept_found" | "candidate" | "reject" | "done",
  "message": "Concept #2 found: ...",   // human-readable explanation shown in the UI
  "ops": [ /* GraphOp[] — may be empty */ ],
  "focus": {                            // what the UI should highlight for THIS step
    "nodes": [2],
    "addedEdges":   [[0, 2]],
    "removedEdges": [[0, 1]]
  },
  "algo": {                             // only present when granularity = "detailed" and kind is candidate/reject/concept_found
    "depth": 1,                         // recursion depth (CbO/In-Close) or 0
    "attribute": 4,                     // attribute index being tried, or null
    "candidateIntent": [1, 4],          // attribute indices
    "candidateExtent": [0, 2],          // object indices, if the algorithm computes it (else null)
    "closure": [1, 4, 7],               // closed intent, if computed (else null)
    "accepted": false,
    "reason": "Closure adds attribute 0 which is lexically before 4"
  }
}

// GraphOp (discriminated on "op")
{ "op": "add_node",    "id": 2, "extent": [0, 2], "intent": [1, 4, 7] }   // FULL extent/intent as index arrays, sorted ascending
{ "op": "add_edge",    "source": 0, "target": 2 }                          // source = PARENT (superconcept, larger extent), target = CHILD
{ "op": "remove_edge", "source": 0, "target": 1 }
```

**Rules**
- Node `id` = discovery order (0,1,2…), unique and stable within a trace.
- Edges are the **Hasse (covering) relation** of the concepts found *so far*. Inserting a concept between `p` and `c` yields `remove_edge(p,c)` + `add_edge(p,n)` + `add_edge(n,c)` in the same step.
- Step 0 is always `init` (empty graph, explains context + algorithm). The last step is always `done` (summary: concept count, edge count; mention truncation if any). In `concept` granularity the steps in between are exactly one `concept_found` per concept.
- Applying `ops` of steps `0..k` in order must reproduce the graph shown at step `k`. Ops must be **invertible**-friendly (add↔remove) so the client can step backward by replay or by inverse.
- Final graph after all steps must equal the Hasse diagram of the full concept lattice (verified in B5 tests).
- Labels are converted with `str(...)` (CSV labels may be numeric).
- **Reduced labeling** (object shown at its object-concept, attribute shown at its attribute-concept) is **computed on the frontend from the final graph** (D6), not shipped in the trace.

---

## 4. API contract (all under `/api`)

| Method & path | Response |
|---|---|
| `GET /api/health` | `{ "status": "ok" }` |
| `GET /api/datasets` | `[{ id, name, fileName, objectCount, attributeCount }]` — scanned from `data/*.csv`; `id` = file stem |
| `GET /api/datasets/{id}` | `{ id, name, objects: string[], attributes: string[], matrix: (0\|1)[][] }` |
| `GET /api/algorithms` | `[{ id, name, description, supportsDetailed }]` |
| `POST /api/trace` | body `{ dataset, algorithm, granularity = "concept", maxConcepts = 2000, maxSteps = 5000 }` → `Trace` |

Errors: `404` unknown dataset/algorithm; `422` invalid request or invalid CSV (non-Boolean cell, ragged rows); hitting a cap is **not** an error — return the partial trace with `truncated: true`.
Dev: Vite dev server proxies `/api` → `http://localhost:8000` (no CORS needed). Prod: FastAPI also serves the built frontend (E2).

---

## 5. Target repository layout

New things marked `NEW`. Do not move or rename existing files.

```text
FCA-Project/
  PLAN.md                         NEW  this file
  AGENTS.md                       existing — keep in sync (see each chunk's Done-when)
  pyproject.toml                  NEW  deps + pytest/ruff config (NOT a package definition)
  data/                           existing CSVs (unchanged)
  backend/
    algorithms/                   existing (+ event streams in B3/B4)
    models/                       existing
    graphing/                     existing (ConceptLattice stays for the matplotlib demo)
    tracing/                      NEW
      schema.py                   Pydantic models: Trace, Step, GraphOp, Meta, AlgoInfo
      events.py                   internal AlgoEvent dataclasses emitted by algorithms
      lattice_builder.py          incremental lattice + diff -> GraphOps
      messages.py                 human-readable step messages
      generator.py                generate_trace(...)
      registry.py                 algorithm id -> class, display names/descriptions
    api/                          NEW
      main.py                     FastAPI app (`api.main:app`)
      routes/{datasets,algorithms,trace}.py
      services/datasets.py        data-dir resolution, CSV loading + validation
    scripts/export_openapi.py     NEW
    tests/                        NEW  (pytest; NOT backend/testing/)
  frontend/                       NEW  Vite + React + TS app
    src/
      api/                        generated types + fetch client + query hooks
      store/                      zustand store (trace, step, modes)
      stepping/                   pure fns: stateAt(trace, k), checkpoints
      layout/                     ELK wrapper + worker
      components/                 Header, Selectors, ControlsBar, GraphCanvas, nodes/edges, SidePanel, Tooltip
      lib/ , types/
    tests/ or src/**/*.test.ts(x)
  docs/
    examples/                     NEW  sample traces (airlines) used as frontend fixtures
```

Data dir resolution (fixes the cwd problem in `backend/main.py` without touching it): `DATA_DIR = Path(os.environ.get("FCA_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))` (adjust `parents[n]` to the file's depth).

---

## 6. Conventions & guardrails

- Follow every invariant in `AGENTS.md` ("Coding rules and invariants"). Especially: integer-index normalisation stays in `FormalContext`; algorithm `run()` stays a lazy generator yielding `FormalConcept`; set semantics for concepts; stable attribute order.
- **Never change algorithm behaviour** while adding events. A2's tests are the safety net; they must stay green after B3/B4.
- Compare concept collections as `{(frozenset(objects), frozenset(attributes))}`, never by list order.
- Python: type hints everywhere in new code; explicit imports (no `import *`); Pydantic v2; target the Python version installed locally (≥3.10 assumed — verify).
- Do not edit `ConceptLattice` unless a chunk says so; if a bug is found, record it in the Progress Log and make the smallest fix with a test.
- TypeScript: `strict` mode; no `any` in new code; ESLint + Prettier clean.
- Dependencies: Python deps declared in `pyproject.toml` (`[project] dependencies` = fastapi, uvicorn[standard], pydantic, pandas, networkx; extras `dev` = pytest, httpx, ruff; extra `demo` = matplotlib). Frontend deps in `frontend/package.json`. If network installs fail, say so in the Progress Log and continue with what's possible.
- Headless-safe: nothing in tests may open a GUI window or call `draw()`.
- Each chunk ends with: tests for the chunk pass, `python3 -m compileall backend` passes, `AGENTS.md` updated if file roles/commands/APIs changed, Progress Log updated.

---

## 7. Dependency graph & parallelism

```text
A1 → A2 → B3 → B4 ─┐
A1 → B1 → B2 ──────┴→ B5 → C1 ──────────────┐
                 B1 (fixture) → D1 → D2 → D3 → D4 → D5 → D6 → D7 → E1 → E2
                                 (D3–D5 use the B1 hand-made fixture until B5/C1 exist;
                                  D2 needs C1 for real data, or mock it with MSW/fixtures)
```

- **Backend track:** A1, A2, B1–B5, C1.
- **Frontend track:** D1–D7 can start right after **B1** (it provides a hand-written trace fixture + schema), so two agents can work in parallel.
- D7 needs B3/B4/B5 `detailed` mode. E1/E2 need everything.

---

## 8. Chunks

Size legend: S ≈ ≤1h, M ≈ 1–3h, L ≈ 3h+. (Rough.)

---

### Phase A — Foundation

#### A1 · Baseline & tooling (S)
**Depends on:** nothing.
**Goal:** reproducible dev setup without touching research code.
**Tasks**
1. `git status`; note local changes (do not discard).
2. Create root `pyproject.toml` per §6 (deps, `[tool.pytest.ini_options]` with `testpaths = ["backend/tests"]`, `pythonpath = ["backend"]`; ruff config optional). Do **not** add a `[build-system]`/package definition.
3. Extend `.gitignore`: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `node_modules/`, `frontend/dist/`, `.venv/`, `.ipynb_checkpoints/`, `*.log`. Keep existing `temp/` and `testing/` entries. (Do not ignore `backend/resch.ipynb` or `hasse_diagram.png` on the user's behalf — leave them untracked.)
4. Create `backend/tests/__init__.py`-less folder with a trivial `test_smoke.py` that imports `models`, `algorithms` and runs NextClosure on `data/fca_airlines.csv`, asserting it yields > 0 concepts. Use a path helper (see §5) rather than a cwd-relative path.
5. Add a short "Dev setup" section to the root README (create `README.md` if missing) with exact commands.
**Done when:** `python3 -m pytest` passes from the repo root after installing the dependencies listed in `pyproject.toml` with pip (the file is not a package definition, so `pip install .` is not supported); `compileall` passes; AGENTS.md "Running and validating" updated with the pytest command.

#### A2 · Algorithm safety-net tests (M)
**Depends on:** A1.
**Goal:** lock current behaviour so later refactors (B3/B4) cannot silently break algorithms.
**Tasks** (in `backend/tests/`)
1. `test_concept_order.py`: `FormalConcept` `<=`, `<`, equality (set semantics), incomparability — per `AGENTS.md` ordering rules.
2. `test_algorithms_agree.py`: for `fca_airlines`, `fca_benchmark_20x12`, `fca_benchmark_40x20` — materialise all three algorithms, assert canonical-set equality, and no duplicate concepts within any single algorithm's output. **Do not** run 100x50.
3. `test_algorithms_bruteforce.py`: tiny reference implementation (enumerate all attribute subsets, keep closed ones) and compare on ~50 seeded random small contexts (e.g. up to 6 objects × 6 attributes, varied density, including all-zero and all-one rows/columns, 1×1, empty-intent-closure ≠ ∅ cases). Parametrise over the three algorithms.
4. Assert that the first yielded concept of each algorithm is the **top concept** (extent = all objects). The trace builder in B2/B5 relies on this — if false for any algorithm, record in Progress Log.
5. Pin the airlines concept count as a constant after verifying it with the brute-force reference.
**Done when:** all tests pass (or any discovered algorithm bug is documented in the Progress Log with a minimal failing test marked `xfail` and a note to the user). No algorithm code changed unless a real bug is found.

---

### Phase B — Trace engine (backend)

#### B1 · Trace schema + hand-written fixture (S)
**Depends on:** A1.
**Tasks**
1. `backend/tracing/schema.py`: Pydantic v2 models implementing §3 exactly (discriminated union for `GraphOp`; `AlgoInfo`; `Focus`; enums as `Literal`s). camelCase aliases.
2. `backend/tests/test_schema.py`: round-trip a sample, check aliases (`stepCount`, `addedEdges`, …), reject bad `op` values.
3. Hand-write `docs/examples/tiny_trace.json`: a 3×3 context with ~5 concepts, concept granularity, including **one step that inserts a node between two existing nodes** (so `remove_edge` is exercised) and a final `done` step. Validate it against the schema in a test. The frontend uses this fixture until real traces exist.
4. Short `docs/trace-format.md` pointing at §3 of this file (avoid duplicating the full spec — keep one source of truth, or move the spec there and link from PLAN.md).
**Done when:** schema tests pass; fixture validates; fixture is internally consistent (replaying ops yields a valid Hasse diagram).

#### B2 · Incremental lattice builder with diff ops (M)
**Depends on:** B1 (A2 recommended).
**Goal:** given concepts arriving in **arbitrary order** (algorithm discovery order), maintain the Hasse diagram and emit the ops for each insertion.
**Tasks**
1. `backend/tracing/lattice_builder.py`: class `LatticeBuilder` with `add(extent: frozenset[int], intent: frozenset[int]) -> StepDelta` returning `{node_id, new_node: GraphOp, added_edges, removed_edges}`; idempotent for duplicates (returns no-op delta and no new id).
2. **Decide reuse vs. own implementation:** first read the current `ConceptLattice` (including uncommitted changes). If `add_concept` correctly handles arbitrary order (parent finding + child-edge redirection) and the constructor can be seeded with one concept, wrap it and diff edge sets before/after. Otherwise implement a small standalone builder (order test: `c1 <= c2 ⇔ extent1 ⊆ extent2`; parents = maximal elements among existing nodes strictly above the new one; children = minimal strictly below; drop edges `p→c` for every `p ∈ parents, c ∈ children` that were direct). Record the decision in the Progress Log. Either way, **do not modify `ConceptLattice`** in this chunk.
3. Convention: edge `source` = parent (larger extent). If `ConceptLattice` uses the opposite direction, translate in the builder.
4. Tests (`backend/tests/test_lattice_builder.py`):
   - For each small dataset: feed all concepts in (a) algorithm order for all 3 algorithms and (b) 20 random permutations (top concept first, as the real algorithms do; also one permutation with top *not* first if the implementation supports it). Final edge set must equal an **independent reference**: networkx `transitive_reduction` of the strict-order DAG over all concepts.
   - Replaying emitted ops step by step reproduces the builder's graph.
   - Multi-parent insertion and "insert in between" cases (use B1 fixture shape).
**Done when:** tests pass for airlines, 20x12 and 40x20; acyclicity asserted.

#### B3 · Algorithm event streams — base + NextClosure (M)
**Depends on:** A2.
**Goal:** expose the algorithms' internal decisions as events without changing behaviour.
**Tasks**
1. `backend/tracing/events.py`: dataclasses (internal, not Pydantic) e.g. `CandidateEvent(depth, attribute, candidate_intent, candidate_extent|None, closure|None, accepted, reason)`, `ConceptEvent(extent: tuple[int,...], intent: tuple[int,...], depth)`. All sets as **integer indices** (before label remapping).
2. In `BaseAlgorithm`: add `events(self, detail: bool = False) -> Iterator[AlgoEvent]` contract (not abstract-breaking: default can raise `NotImplementedError`). Keep existing `run()` signature and laziness; implement `run()` for NextClosure **on top of** `events(detail=False)` (map `ConceptEvent` → `remap_concept`), or keep `run()` untouched and share the core via a private generator — pick the lower-risk option and note it.
3. `NextClosure.events(detail)`: `ConceptEvent` for each closed intent (first = closure of ∅). When `detail=True`, also emit a `CandidateEvent` for each attribute tried in `_step` (accepted or rejected, with the reason such as "closure adds smaller attribute(s) …"). With `detail=False`, **no per-candidate objects are created** (keeps benchmarks fast).
4. Tests: `events(False)` concept stream equals `run()` (same order, same concepts); `events(True)` contains exactly one accepted `CandidateEvent` immediately before each non-first `ConceptEvent`; A2 tests still green.
**Done when:** all of the above pass; `AGENTS.md` algorithm section mentions `events()`.

#### B4 · Event streams — Close-by-One & In-Close (M)
**Depends on:** B3.
**Tasks**
1. Implement `events(detail)` for `CloseByOne` (candidate = `A ∪ {i}`, closure `C`, canonicity test `A[:i] == C[:i]`; depth = recursion depth) and `InClose` (candidate attribute `j`, new extent, outcomes: "attribute already in closure", "rejected: earlier attribute contains new extent", "accepted → recurse"; fill `candidateExtent`). Read the code first — map each decision point to an event; **do not restructure the algorithm**. Beware `InClose`'s shared mutable `attributes` list: copy when emitting events.
2. Same test pattern as B3 for both algorithms.
3. A2 tests stay green (cross-algorithm agreement, brute-force).
**Done when:** all three algorithms have working `events()`; concept streams equal `run()`.

#### B5 · Trace generator (M)
**Depends on:** B2, B4 (B3 minimum if B4 is delayed — then only `next_closure` is enabled).
**Tasks**
1. `backend/tracing/registry.py`: `ALGORITHMS = {"next_closure": ..., "close_by_one": ..., "in_close": ...}` with display name, description (2–3 sentences each, accurate), `supports_detailed`.
2. `backend/tracing/messages.py`: message builders using **original labels** (objects/attributes), e.g.
   - init: "Context: 5 objects × 9 attributes. Algorithm: NextClosure. The lattice starts empty."
   - concept_found: "Concept #4 found — extent {A, B}, intent {x, y}. Inserted below #1 and #2; edge #1→#3 replaced because #4 lies between."
   - candidate/reject: algorithm-specific explanation from `AlgoInfo.reason`.
   - done: "Done: 19 concepts, 31 edges." (+ truncation warning)
   Truncate very long label lists in messages (e.g. ≤ 8 items + "…").
3. `backend/tracing/generator.py`: `generate_trace(context: FormalContext, dataset_id, algorithm_id, granularity, max_concepts, max_steps) -> Trace`. Pipeline: `algo.events(detail=granularity=="detailed")` → for each `ConceptEvent` call `LatticeBuilder.add` → build `Step` (ops + focus + message); for candidate events build ops-less steps (detailed only). Stop at caps → set `truncated`, still append `done` step.
4. Tests (`backend/tests/test_generator.py`): for airlines × 3 algorithms × both granularities — schema-valid; `steps[i].index == i`; first=`init`, last=`done`; `concept` mode has exactly `conceptCount` `concept_found` steps; replaying ops gives final graph equal to the reference Hasse diagram; label arrays match the CSV; truncation test with `max_concepts=3` on 20x12; **golden file**: commit `docs/examples/airlines_next_closure_concept.json` produced by the generator and test that regeneration matches it (deterministic output!).
5. Script `backend/scripts/make_example_traces.py` to regenerate golden/example files.
**Done when:** tests pass; example traces committed; generation for 40x20 completes in a few seconds at most (note timing in Progress Log).

---

### Phase C — API

#### C1 · FastAPI service (M)
**Depends on:** B5.
**Tasks**
1. `backend/api/services/datasets.py`: data-dir resolution (§5), list CSVs, load via `pandas.read_csv(path, index_col=0)` + `FormalContext.from_pandas`, **validate** (non-empty, all cells 0/1/bool, unique labels) → raise a domain error mapped to `422`. Do not change `from_csv` semantics.
2. Routes per §4 in `backend/api/routes/*.py`; app in `backend/api/main.py` with `/api` prefix, `response_model` set, request model `TraceRequest` with bounds (`maxConcepts` ≤ 20000, `maxSteps` ≤ 50000).
3. In-process LRU cache for `generate_trace` keyed by `(dataset, algorithm, granularity, maxConcepts, maxSteps)`.
4. Tests with `fastapi.testclient.TestClient`: each route happy path, 404/422 paths, truncated response, cache hit returns equal body.
5. Run docs in README: `uvicorn api.main:app --app-dir backend --reload --port 8000` (verify it works from repo root).
6. `backend/scripts/export_openapi.py` → writes `docs/openapi.json` (committed). Test or CI step checks it is up to date.
**Done when:** tests pass; manual `curl` of `/api/datasets` and a trace works; `AGENTS.md` updated (new dirs, commands).

---

### Phase D — Frontend

#### D1 · Scaffold, tooling, typed API client (M)
**Depends on:** B1 (for fixture/types), ideally C1 (`docs/openapi.json`).
**Tasks**
1. `npm create vite@latest frontend -- --template react-ts` into `frontend/` (remove the empty `frontend/main.py` placeholder; keep `frontend/README.md`, expand it). Pin versions.
2. Install: `@xyflow/react`, `elkjs`, `zustand`, `@tanstack/react-query`, `tailwindcss` (+ its Vite plugin/PostCSS per current docs), dev: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`, `openapi-typescript`, `eslint`, `prettier`, `msw` (optional).
3. Vite config: `/api` proxy → `http://localhost:8000`; Vitest config (jsdom).
4. `npm run gen:types` → `openapi-typescript ../docs/openapi.json -o src/api/schema.d.ts` (commit generated file). Re-export convenient aliases in `src/api/types.ts` (`Trace`, `Step`, `GraphOp`, …).
5. `src/api/client.ts` + hooks: `useDatasets()`, `useAlgorithms()`, `useTrace(params)` (TanStack Query; `staleTime: Infinity`).
6. App shell with Tailwind: header (placeholders for selectors), main canvas area, bottom controls bar area, right side panel. `QueryClientProvider` set up. One smoke test renders `<App/>`.
7. Scripts: `dev`, `build`, `lint`, `test`, `typecheck`, `gen:types`.
**Done when:** `npm run dev` shows the shell; `lint`, `typecheck`, `test`, `build` all pass; frontend README lists commands.

#### D2 · Selectors + trace loading (S)
**Depends on:** D1, C1 (or MSW mocks).
**Tasks**
1. Zustand store (`src/store/useAppStore.ts`): `datasetId`, `algorithmId`, `granularity` (`concept`), selectors/actions. Defaults: first dataset (`fca_airlines` if present) + `next_closure`.
2. `DatasetSelector` and `AlgorithmSelector` components (native `<select>` or accessible listbox) fed from the API hooks; show object×attribute counts next to dataset names; show algorithm description as a hint/tooltip.
3. When selection changes: fetch trace via `useTrace`; reset `stepIndex` to 0; show loading skeleton and error banner (with retry). Show a **truncation warning banner** when `meta.truncated`.
4. Tests: selectors render options from mocked API; changing selection triggers a new trace request and resets step.
**Done when:** with the backend running, picking dataset/algorithm loads a trace (visible as a debug line "N steps loaded" for now).

#### D3 · Stepping engine + controls bar (M)
**Depends on:** D2 (can develop against the `tiny_trace.json` fixture).
**Tasks**
1. `src/stepping/stateAt.ts` — **pure** function `stateAt(trace, k) → { nodes: Map<id, Node>, edges: Set<"s->t"> , lastStep }` replaying ops `0..k`; with a **checkpoint cache** (snapshot every ~25 steps, computed lazily) so Back/Next/slider jumps stay O(checkpoint interval). Also `finalState(trace)`.
2. Store: `stepIndex`, `next()`, `back()`, `first()`, `last()`, `goTo(i)`, clamped; `isPlaying`, `speedMs`.
3. `ControlsBar`: First, Back, Next, Last buttons; range slider; "Step k / N"; Play/Pause + speed (auto-advance, stops at the end). Disabled states at the boundaries.
4. Keyboard: `←`/`→` step, `Home`/`End`, `Space` play/pause (ignore when focus is in an input/select).
5. Show current `step.message` in a `StepExplanation` panel (side panel or under the controls).
6. Vitest: `stateAt` on the tiny fixture and on `docs/examples/airlines_next_closure_concept.json` — for every k, state equals independent incremental replay; backward == forward; store clamps; keyboard handler test.
**Done when:** controls navigate steps; explanation text updates; counts of visible nodes/edges shown as a temporary debug readout.

#### D4 · Layout engine (ELK in a Web Worker) (M)
**Depends on:** D3 (`finalState`).
**Tasks**
1. `src/layout/elkLayout.ts`: `computeLayout(finalNodes, finalEdges) → Promise<Map<id,{x,y}>>`. Use `elkjs` in a **Web Worker** (`elkjs/lib/elk-worker` pattern or Vite `?worker`). Options: `elk.algorithm=layered`, `elk.direction=DOWN`, fixed node size (~28×28), spacing tuned for readability, crossing-minimisation layer sweep. Constrain the **top concept to the first layer and the bottom concept (extent = ∅ or no children) to the last layer** if feasible (`layerConstraint FIRST/LAST`). Ignore ELK edge routing — straight edges from node positions.
2. Layout is keyed by trace identity (`dataset+algorithm+granularity`) and cached; recompute only when the final graph changes.
3. Hook `useLayout(trace)` returning `{ positions, status }`.
4. Unit tests (jsdom can't run workers — structure code so the pure part (building the ELK graph JSON) is testable and the worker call is mockable): ELK input has all nodes/edges; positions mapping; top node has the minimum y.
5. For lattices > ~800 nodes: still compute, but expose `status: "slow"` so the UI can warn (E1).
**Done when:** for airlines and 40x20 final graphs a position map is produced; top node is visually above all others; no jank during computation (worker).

#### D5 · Graph canvas: step-wise rendering (L)
**Depends on:** D3, D4.
**Tasks**
1. `GraphCanvas` with React Flow: read-only (no node drag/connect/delete; keep pan & zoom), `fitView` **only** on trace load (not per step), no minimap by default.
2. Render only nodes/edges visible at `stepIndex` using `stateAt` + fixed positions from `useLayout`.
3. Custom node `ConceptNode`: small circle (~14–18 px) with a tiny id/index label optional via setting; visual states: *default*, *new in this step* (accent colour + brief pulse), *top/bottom* subtle marker, *pinned/selected* (D6).
4. Custom edge: straight line; edges **added this step** highlighted; edges **removed this step** shown as a faded dashed red ghost for that step only (derive from `step.focus.removedEdges`); transitions via CSS (respect `prefers-reduced-motion`).
5. Smooth appearance (opacity/scale transition) but **no position animation**.
6. Tests: component test with the tiny fixture — number of rendered nodes/edges per step; removed-edge ghost appears only on the step where it is removed; Back restores previous rendering.
**Done when:** Next/Back visibly grows/shrinks the lattice on airlines for all three algorithms; layout never jumps.

#### D6 · Node data display modes + details (M)
**Depends on:** D5.
**Tasks**
1. Store: `nodeDisplayMode: "hover" | "labels" | "off"` (default `hover`), `pinnedNodeId | null`.
2. `NodeDisplaySelector` (segmented control in the header or above the canvas): **Hover / Labels / Off**.
3. **Hover mode:** hovering a node shows a tooltip (floating, not clipped by canvas; use `@floating-ui/react` or a positioned div) with: concept id, **extent** (object labels), **intent** (attribute labels), sizes, parents/children count. Long lists scroll/truncate with "+N more". Tooltip must not flicker when moving between nodes.
4. **Labels mode:** show **reduced labels** next to nodes — attributes above, objects below. Compute reduced labeling on the frontend from the **final** graph: attribute `m` is labelled at the node where it first appears (in intent of node but in no parent's intent); object `g` at the node where it is in the extent but in no child's extent. Pure function `reducedLabels(finalGraph)` with unit tests (verify on airlines against a hand-checked subset).
5. **Off mode:** completely clean nodes.
6. **Click** pins a node → full details in `SidePanel` ("Concept details": full extent & intent with labels, parents, children, step in which it was discovered) regardless of display mode; click background or `Esc` unpins.
7. Highlight parents/children of the hovered node (subtle) — optional, cheap.
**Done when:** switching modes works live while stepping; default view is clean; tooltip shows correct data (spot-check vs backend trace); reduced-labeling tests pass.

#### D7 · Detailed granularity UI (M)
**Depends on:** D6, B4/B5 (`detailed` traces), C1.
**Tasks**
1. `GranularityToggle` ("Concepts" / "Detailed") — disabled for algorithms with `supportsDetailed=false`. Changing it refetches the trace and resets the step.
2. `AlgoInfoPanel`: for steps with `algo` data show — current depth, attribute being tried, candidate intent, closure, accepted/rejected + reason; colour-coded accept (green) / reject (red).
3. In-canvas feedback for candidate steps: if the candidate closure matches an existing node, flash it; otherwise no graph change (steps have empty `ops`).
4. Slider shows tick marks (or colour bands) for `concept_found` steps vs candidate steps; add buttons **"Next concept"** / **"Previous concept"** that skip candidate steps.
5. Warn if the detailed trace was truncated by `maxSteps`.
6. Tests: skipping logic (next/prev concept) on a detailed fixture (commit `docs/examples/airlines_next_closure_detailed.json`); panel renders accepted/rejected states.
**Done when:** detailed mode works for all three algorithms; Next/Back work in both granularities; "Next concept" jumps correctly.

---

### Phase E — Hardening & delivery

#### E1 · Robustness, UX polish, context table (M)
**Depends on:** D6 (D7 preferred).
**Tasks**
1. States: loading skeletons, API-down error with retry, empty/invalid dataset error, truncation banner with explanation ("lattice shown is partial; raise limit or choose smaller dataset"), slow-layout notice for large lattices (>800 nodes).
2. **URL state**: sync `dataset`, `algorithm`, `granularity`, `step`, `mode` to the query string (shareable links; browser back button does not step).
3. Accessibility: aria-labels on controls, visible focus rings, tooltip content also reachable via keyboard focus on nodes (nodes focusable; Enter pins), colour-blind-safe accent choices, reduced-motion support.
4. **Context viewer**: collapsible panel with the object×attribute incidence table from `GET /api/datasets/{id}` (sticky headers, scroll); when a node is hovered/pinned, highlight its extent rows/intent columns.
5. Responsive layout (side panel collapses below ~900 px).
6. Dark/light follows system.
**Done when:** manual QA checklist in the Progress Log passes on airlines, 20x12, 40x20 and the 100x50 (expects truncation); tests for URL-state parsing/serialising pass.

#### E2 · Packaging, CI, docs (M)
**Depends on:** E1.
**Tasks**
1. Production serving: `npm run build` → FastAPI mounts `frontend/dist` as static files at `/` (with SPA fallback) when the directory exists; env `FCA_FRONTEND_DIST` override. Single command to run everything: document `uvicorn api.main:app --app-dir backend --port 8000`.
2. Root `Makefile` or `scripts/dev.sh` (optional): `make dev` runs backend + frontend; `make test`; `make check`.
3. GitHub Actions workflow: Python (install deps, `ruff`, `pytest`, openapi-export freshness check) and Node (`npm ci`, lint, typecheck, test, build). Cache deps.
4. Optional: Playwright smoke test — open app, pick dataset/algorithm, click Next 3×, assert node count increases; hover shows tooltip.
5. Rewrite root `README.md` (what it is, screenshot/GIF, setup, run, architecture diagram matching **reality**), update `backend/README.md` to state what is now implemented vs planned, update `AGENTS.md` fully (new directories, commands, invariants, known gaps), mark stale notebooks/tests as legacy.
6. Optionally migrate/fix or clearly deprecate the stale scripts in `backend/testing/` (ignored folder — only mention in AGENTS.md; don't spend time).
**Done when:** a fresh clone can follow README to run the full app; CI green; AGENTS.md matches the code.

---

### Stretch backlog (not scheduled — only do when asked)

- Upload a custom CSV (needs strict validation, size limits, temp storage, security review).
- Side-by-side algorithm comparison (two canvases, synchronised step counter, compare discovery order).
- Re-layout-per-step mode (optional toggle) and animated transitions between layouts.
- Export current view as PNG/SVG; export trace JSON.
- Streaming traces (SSE/WebSocket) for very large lattices; server-side pagination of steps.
- Search/highlight: click an attribute or object to highlight all concepts that contain it (uses full intents/extents).
- Compute and show implications / stem base.
- Replace stale `backend/testing/` scripts with proper benchmark tests.
- Show tree view of CbO/In-Close recursion alongside the lattice.

---

## 9. Progress Log (agents: update this!)

Status values: `todo` · `in-progress` · `done` · `blocked`.

| Chunk | Status | Last agent/date | Notes (decisions, deviations, what's left) |
|-------|--------|-----------------|---------------------------------------------|
| A1 | done | Claude, 2026-11-06 | Added root `pyproject.toml` (deps + pytest `testpaths`/`pythonpath` + ruff config, no build-system), extended `.gitignore`, `README.md` with dev setup, `backend/tests/{helpers,test_smoke}.py`. `helpers.py` provides `DATA_DIR` (env `FCA_DATA_DIR` override), `load_context`, `context_from_matrix`, `canonical`. Python 3.13 used. `fastapi` and `httpx` were NOT installable/installed in the dev sandbox (no network) — C1 must install them first. AGENTS.md updated. |
| A2 | done | Claude, 2026-11-06 | 238 tests pass (~3 s). No algorithm bugs found: NextClosure, CloseByOne and InClose match an independent brute-force reference on 14 edge-case + 50 seeded random contexts and on airlines/20x12; no duplicates; first yielded concept is the top concept for all three on all three datasets (B2/B5 may rely on this). Pinned counts: airlines = **6** concepts, 20x12 = **88**. (40x20 is only cross-checked between algorithms, not brute-forced.) No algorithm code was changed. |
| B1 | done | Claude, 2026-11-06 | `backend/tracing/{__init__,schema,replay}.py`, `backend/tests/test_schema.py` (23 tests), `docs/examples/tiny_trace.json`, `docs/trace-format.md`. Schema adds `extra="forbid"` and a model validator (step indices, init/done bookends, `stepCount`, `conceptCount`). **Deviation:** the fixture was *generated* once (script was not committed) from Close-by-One's real discovery order on the 3×3 context `g1:{c} g2:{b,c} g3:{a,b}`, then verified independently in tests (ops replay validly at every step, every prefix and the final graph equal a networkx transitive-reduction reference). It has 6 concepts / 7 edges and step 4 contains a `remove_edge`. Added `tracing/replay.py` (strict op replay) which B5 tests should reuse. |
| B2 | done | Claude, 2026-11-06 | **Decision: own standalone builder** (`backend/tracing/lattice_builder.py`), `ConceptLattice` untouched. Verified experimentally that `ConceptLattice.add_concept` is only correct for NextClosure order / extent-size-sorted input; it gives wrong edges for Close-by-One and In-Close order and for ~50–100% of random permutations. Builder finds direct parents/children via the existing graph (a node above the new concept is a parent iff none of its children is also above it; symmetric for children), so it is order-independent and cheap. `backend/tests/test_lattice_builder.py` (18 tests): all 3 algorithm orders × airlines/20x12/40x20, 20 random permutations (incl. top not first), duplicate no-op, in-between, multi-parent, non-child-descendant regression, determinism; ops replayed alongside the builder after every step. Edge direction `(parent, child)` and ids = discovery order as in §3. |
| B3 | todo | | |
| B4 | todo | | |
| B5 | todo | | |
| C1 | todo | | |
| D1 | todo | | |
| D2 | todo | | |
| D3 | todo | | |
| D4 | todo | | |
| D5 | todo | | |
| D6 | todo | | |
| D7 | todo | | |
| E1 | todo | | |
| E2 | todo | | |

**Open questions / decisions made along the way** (append, newest last):

- 2026-11-06 (A1/A2): Work was done in a fresh clone of `Aryan-Bodhe/FCA-Project` (`main` @ `fc9688e`), which does **not** contain the author's uncommitted local changes (`backend/graphing/concept_graph.py`, `backend/main.py`, `backend/resch.ipynb`, `hasse_diagram.png`). All A1/A2 changes are new files (plus `.gitignore`, `AGENTS.md`, `PLAN.md`), so they merge cleanly onto a local checkout. `AGENTS.md` and `PLAN.md` were not in the clone; copies were added at the repo root.
- 2026-11-06 (B2): **NextClosure traces never contain `remove_edge`** (lectic order visits every concept after all its superconcepts; 0 removals on all 512 3×3 contexts and 300 random 5×5). Close-by-One and In-Close do. The UI's removed-edge ghost (D5) only shows for those two; test D5 with `tiny_trace.json` or a CbO/In-Close trace, not NextClosure.
- 2026-11-06 (B2): The author's real local `concept_graph.py` and `main.py` (newer than the committed ones) were supplied and synced verbatim into the working tree (separate commit). They are unmodified. `ConceptLattice.add_top` / `add_concept` / `get_full_objects` etc. are as described in AGENTS.md.
- 2026-11-06 (A1/A2): Observed in code while reading: `FormalContext.objects`/`attributes` are pandas `Index` objects until `_preprocess()` replaces them with integer lists; `object_map`/`attribute_map` map index → original label (may be numpy scalars — convert with `str()` in the trace). `InClose` yields attribute lists that may be unsorted (set semantics hold) — sort before emitting trace ops.

---

## 10. Risks & things the first agents must verify

1. **This plan was written from `AGENTS.md`, not from reading the source.** Chunks A2/B2/B3/B4 start by reading the real code; if reality differs (e.g. edge direction in `ConceptLattice`, whether the first yielded concept is the top concept, what `object_map`/`attribute_map` look like), follow reality for internals but **keep the §3/§4 contracts unchanged** and log the difference.
2. **Uncommitted local changes** exist in `backend/graphing/concept_graph.py` and `backend/main.py`. Build new functionality in new files (`backend/tracing/`, `backend/api/`) so those changes are never overwritten.
3. **`ConceptLattice.add_concept` on arbitrary order** is unverified → B2 includes an independent transitive-reduction check.
4. **Trace size/time** for big contexts (100x50 can explode combinatorially) → caps + `truncated` flag + UI warning; naive O(n²) parent search is fine at ≤ a few thousand concepts.
5. **Layout stability vs. growth** → single final layout, visibility toggling (Decision 5).
6. **Frontend/Backend drift** → generated TS types from `docs/openapi.json`; CI freshness check (E2).
7. **Algorithm refactors** (events) can subtly change behaviour → A2 tests are mandatory before B3 and must stay green.
