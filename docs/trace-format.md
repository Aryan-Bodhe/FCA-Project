# Trace format

The trace is the JSON document the backend produces and the frontend plays back
step by step. The authoritative specification is **PLAN.md §3 "Trace contract"**
(kept in one place on purpose). The executable definition is
[`backend/tracing/schema.py`](../backend/tracing/schema.py) (Pydantic models,
camelCase aliases), which also enforces structural rules: `steps[i].index == i`,
first step `init`, last step `done`, `meta.stepCount == len(steps)`,
`meta.conceptCount == number of add_node ops`.

## Quick reference

- `Trace { version: 1, meta, steps[] }`
- `Step { index, kind, message, ops[], focus, algo? }` where `kind` is
  `init | concept_found | candidate | reject | done`
- `GraphOp` is one of `add_node {id, extent[], intent[]}`,
  `add_edge {source, target}`, `remove_edge {source, target}`; `source` is the
  parent (larger extent). Indices refer to `meta.objects` / `meta.attributes`.
- Within a step, ops are ordered `add_node`, `remove_edge`*, `add_edge`*.

## Helpers and fixtures

- [`backend/tracing/replay.py`](../backend/tracing/replay.py) — applies ops to a
  graph state with strict validation (mirrors the frontend's `stateAt`).
- [`docs/examples/tiny_trace.json`](./examples/tiny_trace.json) — 3 objects × 3
  attributes, 6 concepts, produced with Close-by-One's discovery order. Step 4
  inserts concept #3 between #0 and #1, so it contains a `remove_edge` op. Use it
  as the frontend fixture until real traces are available.

## Behavioural note worth knowing for the UI

NextClosure enumerates closed sets in lectic order, which always visits a
concept after all of its superconcepts. Its traces therefore **never contain
`remove_edge`** (verified on random contexts). Close-by-One and In-Close discover
concepts in an order where a new concept can land *between* existing ones, so
their traces do contain `remove_edge`. The removed-edge "ghost" in the UI will
only ever show for those two algorithms.
