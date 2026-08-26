"""Unit tests for ml/rag/ingest/table_parsing.py's HTML table parser."""

from ml.rag.ingest.table_parsing import find_table_blocks, flatten_row, parse_table_rows

SAMPLE_TABLE = (
    "<table>\n"
    "<tr><th>Test</th><th>Result</th><th>Flag</th></tr>\n"
    "<tr><td>Sodium</td><td>138 mEq/L</td><td>Normal</td></tr>\n"
    "<tr><td>Potassium</td><td>5.4 mEq/L</td><td>High</td></tr>\n"
    "</table>"
)


def test_find_table_blocks_extracts_table_html():
    text = f"Some header text\n\n{SAMPLE_TABLE}\n\nSome footer text"
    blocks = find_table_blocks(text)
    assert len(blocks) == 1
    assert blocks[0] == SAMPLE_TABLE


def test_find_table_blocks_returns_empty_list_when_no_table():
    assert find_table_blocks("just plain text, no tables here") == []


def test_parse_table_rows_uses_first_row_as_headers():
    rows = parse_table_rows(SAMPLE_TABLE)
    assert rows == [
        {"Test": "Sodium", "Result": "138 mEq/L", "Flag": "Normal"},
        {"Test": "Potassium", "Result": "5.4 mEq/L", "Flag": "High"},
    ]


def test_parse_table_rows_handles_mismatched_cell_counts():
    ragged = "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td></tr></table>"
    assert parse_table_rows(ragged) == [{"A": "1"}]


def test_parse_table_rows_returns_empty_list_for_empty_table():
    assert parse_table_rows("<table></table>") == []


def test_flatten_row_renders_label_value_pairs():
    row = {"Test": "Potassium", "Result": "5.4 mEq/L", "Flag": "High"}
    assert flatten_row(row) == "Test: Potassium, Result: 5.4 mEq/L, Flag: High"


def test_flatten_row_skips_empty_values():
    row = {"Test": "Potassium", "Result": "", "Flag": "High"}
    assert flatten_row(row) == "Test: Potassium, Flag: High"
