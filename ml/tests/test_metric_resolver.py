"""Unit tests for ml/graph/metric_resolver.py's alias lookup."""

from ml.graph.metric_resolver import resolve_metric


def test_resolve_metric_maps_known_aliases_to_canonical_name():
    assert resolve_metric("LDL") == "LDL Cholesterol"
    assert resolve_metric("ldl-c") == "LDL Cholesterol"
    assert resolve_metric("Low Density Lipoprotein") == "LDL Cholesterol"


def test_resolve_metric_is_case_and_whitespace_insensitive():
    assert resolve_metric("  LDL cholesterol  ") == "LDL Cholesterol"
    assert resolve_metric("ldl CHOLESTEROL") == "LDL Cholesterol"


def test_resolve_metric_passes_canonical_name_through_unchanged():
    assert resolve_metric("Sodium") == "Sodium"


def test_resolve_metric_passes_unrecognized_name_through_unchanged():
    assert resolve_metric("Some Rare Test Nobody Has Aliased") == "Some Rare Test Nobody Has Aliased"
