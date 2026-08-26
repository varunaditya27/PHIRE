"""
Unit tests for ml/claims/extractor.py's response-parsing logic.

No Ollama/network dependency — tests _parse_claims directly against
canned model responses, since that's the part with actual parsing logic
to get wrong (the LLM call itself has nothing to unit test).
"""

from ml.claims.extractor import ClaimExtractor


def test_parse_claims_from_clean_json_array():
    response = '["LDL cholesterol is elevated.", "The patient takes atorvastatin."]'
    assert ClaimExtractor._parse_claims(response) == [
        "LDL cholesterol is elevated.", "The patient takes atorvastatin.",
    ]


def test_parse_claims_tolerates_surrounding_prose():
    response = 'Here are the claims:\n["LDL cholesterol is elevated."]\nLet me know if you need more.'
    assert ClaimExtractor._parse_claims(response) == ["LDL cholesterol is elevated."]


def test_parse_claims_returns_empty_list_for_empty_array():
    assert ClaimExtractor._parse_claims("[]") == []


def test_parse_claims_returns_empty_list_for_malformed_json():
    assert ClaimExtractor._parse_claims("not valid json at all") == []


def test_parse_claims_drops_non_string_and_blank_entries():
    response = '["A real claim.", "", "  ", 42, null]'
    assert ClaimExtractor._parse_claims(response) == ["A real claim."]


def test_parse_claims_ignores_trailing_text_containing_brackets():
    # A prior greedy regex (first "[" to the *last* "]" in the whole
    # response) swallowed trailing text like this into the match,
    # producing invalid JSON and silently dropping every claim.
    response = '["LDL cholesterol is elevated."]\n\nLet me know if you need [more] details.'
    assert ClaimExtractor._parse_claims(response) == ["LDL cholesterol is elevated."]


def test_parse_claims_returns_empty_list_when_response_has_no_array():
    assert ClaimExtractor._parse_claims('{"claims": "not a list"}') == []


def test_extract_returns_empty_list_for_blank_answer():
    extractor = ClaimExtractor.__new__(ClaimExtractor)  # skip __init__, no client needed
    assert extractor.extract("   ") == []
