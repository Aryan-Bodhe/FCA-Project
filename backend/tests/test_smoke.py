from algorithms import NextClosure

from helpers import load_context


def test_next_closure_runs_on_airlines():
    context = load_context("fca_airlines")
    concepts = list(NextClosure(context).run())
    assert len(concepts) > 0
