"""FormalConcept ordering semantics (see AGENTS.md, "Ordering and concept comparison").

c1 <= c2  <=>  c1.objects ⊆ c2.objects  AND  c1.attributes ⊇ c2.attributes
"""

from models import FormalConcept

# A tiny diamond: top > left, right > bottom
TOP = FormalConcept(["a", "b"], [])
LEFT = FormalConcept(["a"], ["x"])
RIGHT = FormalConcept(["b"], ["y"])
BOTTOM = FormalConcept([], ["x", "y"])


def test_le_follows_extent_subset_and_intent_superset():
    assert BOTTOM <= LEFT <= TOP
    assert BOTTOM <= RIGHT <= TOP
    assert BOTTOM <= TOP
    assert not TOP <= LEFT
    assert not LEFT <= BOTTOM


def test_le_is_reflexive():
    for c in (TOP, LEFT, RIGHT, BOTTOM):
        assert c <= c
        assert c >= c


def test_strict_comparisons():
    assert BOTTOM < TOP
    assert TOP > BOTTOM
    assert not TOP < TOP
    assert not TOP > TOP
    assert not LEFT < RIGHT
    assert not LEFT > RIGHT


def test_ge_gt_mirror_le_lt():
    assert TOP >= LEFT
    assert TOP > LEFT
    assert not LEFT >= TOP


def test_equality_uses_set_semantics_not_list_order():
    assert FormalConcept(["a", "b"], ["x", "y"]) == FormalConcept(["b", "a"], ["y", "x"])
    assert FormalConcept(["a"], ["x"]) != FormalConcept(["a"], ["y"])
    assert FormalConcept(["a"], ["x"]) != FormalConcept(["a", "b"], ["x"])


def test_extent_ordering_is_not_same_direction_as_intent():
    # Subset extent but *smaller* intent is not <= (guards against a naive
    # same-direction subset comparison).
    smaller_extent_smaller_intent = FormalConcept(["a"], ["x"])
    bigger_extent_bigger_intent = FormalConcept(["a", "b"], ["x", "y"])
    assert not smaller_extent_smaller_intent <= bigger_extent_bigger_intent
    assert not bigger_extent_bigger_intent <= smaller_extent_smaller_intent
    assert smaller_extent_smaller_intent.is_incomparable(bigger_extent_bigger_intent)


def test_incomparable():
    assert LEFT.is_incomparable(RIGHT)
    assert RIGHT.is_incomparable(LEFT)
    assert not TOP.is_incomparable(LEFT)
    assert not BOTTOM.is_incomparable(TOP)
    assert not LEFT.is_incomparable(LEFT)
