"""Trace schema + the hand-checked fixture (plan chunk B1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tracing.replay import ReplayError, replay
from tracing.schema import AddEdge, AddNode, Focus, Meta, RemoveEdge, Step, Trace

from helpers import DATA_DIR
from reference import hasse_reference

TINY = DATA_DIR.parent / "docs" / "examples" / "tiny_trace.json"


@pytest.fixture(scope="module")
def tiny_raw() -> dict:
    return json.loads(TINY.read_text())


@pytest.fixture(scope="module")
def tiny(tiny_raw) -> Trace:
    return Trace.model_validate(tiny_raw)


# ------------------------------------------------------------------ schema shape


def test_aliases_are_camel_case_in_json(tiny):
    dumped = tiny.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert {"stepCount", "conceptCount", "maxConcepts", "maxSteps"} <= set(dumped["meta"])
    focus = dumped["steps"][4]["focus"]
    assert set(focus) == {"nodes", "addedEdges", "removedEdges"}
    assert "step_count" not in dumped["meta"]


def test_round_trip_is_lossless(tiny_raw, tiny):
    again = tiny.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert again == tiny_raw
    assert Trace.model_validate(again) == tiny


def test_populate_by_name_and_alias_both_work():
    assert Focus(added_edges=[(0, 1)]) == Focus.model_validate({"addedEdges": [[0, 1]]})


def test_op_discriminator_picks_the_right_model(tiny):
    ops = [op for s in tiny.steps for op in s.ops]
    assert {type(op) for op in ops} == {AddNode, AddEdge, RemoveEdge}


def test_bad_op_value_is_rejected(tiny_raw):
    bad = json.loads(json.dumps(tiny_raw))
    bad["steps"][2]["ops"][0]["op"] = "teleport_node"
    with pytest.raises(ValidationError):
        Trace.model_validate(bad)


def test_unknown_fields_are_rejected(tiny_raw):
    bad = json.loads(json.dumps(tiny_raw))
    bad["steps"][1]["surprise"] = 1
    with pytest.raises(ValidationError):
        Trace.model_validate(bad)


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (lambda d: d["steps"][3].__setitem__("index", 99), "index"),
        (lambda d: d["steps"][0].__setitem__("kind", "done"), "init"),
        (lambda d: d["steps"][-1].__setitem__("kind", "init"), "done"),
        (lambda d: d["meta"].__setitem__("stepCount", 1), "stepCount"),
        (lambda d: d["meta"].__setitem__("conceptCount", 1), "conceptCount"),
        (lambda d: d["meta"].__setitem__("algorithm", "magic"), "algorithm"),
        (lambda d: d["meta"].__setitem__("granularity", "fine"), "granularity"),
        (lambda d: d.__setitem__("version", 2), "version"),
    ],
)
def test_structural_validation(tiny_raw, mutate, fragment):
    bad = json.loads(json.dumps(tiny_raw))
    mutate(bad)
    with pytest.raises(ValidationError) as exc:
        Trace.model_validate(bad)
    assert fragment in str(exc.value)


def test_trace_needs_steps():
    meta = Meta(
        dataset="d", algorithm="next_closure", granularity="concept", objects=[], attributes=[],
        concept_count=0, step_count=0, max_concepts=1, max_steps=1,
    )
    with pytest.raises(ValidationError):
        Trace(meta=meta, steps=[])


def test_algo_info_only_when_present(tiny):
    assert all(s.algo is None for s in tiny.steps)
    step = Step.model_validate(
        {"index": 1, "kind": "reject", "message": "x",
         "algo": {"accepted": False, "reason": "closure adds a smaller attribute"}}
    )
    assert step.algo.depth == 0 and step.algo.attribute is None and step.algo.closure is None


# -------------------------------------------------------------- fixture content


def test_fixture_metadata(tiny):
    assert tiny.meta.dataset == "tiny"
    assert tiny.meta.objects == ["g1", "g2", "g3"]
    assert tiny.meta.attributes == ["a", "b", "c"]
    assert tiny.meta.concept_count == 6
    assert tiny.steps[0].kind == "init" and tiny.steps[-1].kind == "done"
    assert [s.kind for s in tiny.steps[1:-1]] == ["concept_found"] * 6


def test_fixture_exercises_remove_edge_in_one_step(tiny):
    removing = [s for s in tiny.steps if any(op.op == "remove_edge" for op in s.ops)]
    assert len(removing) == 1
    step = removing[0]
    assert step.focus.removed_edges == [(0, 1)]
    ops = [op.op for op in step.ops]
    assert ops == ["add_node", "remove_edge", "add_edge", "add_edge"]


def test_fixture_focus_matches_ops(tiny):
    for step in tiny.steps:
        added = [(o.source, o.target) for o in step.ops if isinstance(o, AddEdge)]
        removed = [(o.source, o.target) for o in step.ops if isinstance(o, RemoveEdge)]
        nodes = [o.id for o in step.ops if isinstance(o, AddNode)]
        assert step.focus.added_edges == added
        assert step.focus.removed_edges == removed
        assert step.focus.nodes == nodes


def test_fixture_replays_to_a_valid_hasse_diagram(tiny):
    """Replaying the ops is valid at every step and ends at the true Hasse diagram
    (checked against an independent transitive-reduction reference)."""
    final = replay(tiny)  # raises ReplayError on any invalid op
    assert sorted(final.nodes) == list(range(6))
    extents = [final.nodes[i][0] for i in range(6)]
    got = {(final.nodes[p][0], final.nodes[c][0]) for p, c in final.edges}
    assert got == hasse_reference(extents)
    assert len(final.edges) == 7


def test_fixture_matches_the_context(tiny):
    """Concepts in the fixture are exactly the concepts of the 3x3 context
    g1:{c}  g2:{b,c}  g3:{a,b}."""
    rows = {0: {2}, 1: {1, 2}, 2: {0, 1}}  # object index -> attribute indices
    final = replay(tiny)
    for extent, intent in final.nodes.values():
        derived_intent = set(range(3)) if not extent else set.intersection(*(rows[g] for g in extent))
        derived_extent = {g for g, attrs in rows.items() if intent <= attrs}
        assert set(intent) == derived_intent
        assert set(extent) == derived_extent


def test_every_prefix_of_the_fixture_is_a_hasse_diagram_of_its_nodes(tiny):
    for k in range(len(tiny.steps)):
        state = replay(tiny, upto=k)
        extents = [state.nodes[i][0] for i in sorted(state.nodes)]
        ids = sorted(state.nodes)
        got = {(state.nodes[p][0], state.nodes[c][0]) for p, c in state.edges}
        assert got == hasse_reference(extents), f"prefix up to step {k}"
        assert ids == list(range(len(ids)))


def test_replay_rejects_invalid_ops():
    step = Step.model_validate(
        {"index": 1, "kind": "concept_found", "message": "x",
         "ops": [{"op": "add_edge", "source": 0, "target": 1}]}
    )
    meta = Meta(
        dataset="d", algorithm="next_closure", granularity="concept", objects=[], attributes=[],
        concept_count=0, step_count=3, max_concepts=1, max_steps=1,
    )
    init = Step(index=0, kind="init", message="i")
    done = Step(index=2, kind="done", message="d")
    trace = Trace(meta=meta, steps=[init, step, done])
    with pytest.raises(ReplayError):
        replay(trace)
