"""
Unit tests for ml/graph/document_dates.py's find_document_date -- split
out alongside that module (see its docstring) from test_observations.py.
"""

from datetime import date

from ml.graph.document_dates import find_document_date


def test_find_document_date_extracts_iso_date():
    text = "Riverside Medical Group\nDate of Service: 2026-03-01\n\nSodium: 138 mEq/L"
    assert find_document_date(text) == "2026-03-01"


def test_find_document_date_falls_back_to_today_when_absent():
    assert find_document_date("no date anywhere in this text") == date.today().isoformat()


def test_find_document_date_skips_a_date_of_birth_label():
    # Regression: the eval_data "demographics_vitals" document lists DOB
    # before Visit Date in document order -- a naive first-ISO-match
    # search silently dated the whole document's vitals to the patient's
    # birth year instead of the visit date.
    text = "Name: R. Thompson\nDOB: 1978-04-22        Sex: F\nVisit Date: 2026-03-01"
    assert find_document_date(text) == "2026-03-01"


def test_find_document_date_skips_date_of_birth_written_out():
    text = "Date of Birth: 1978-04-22\nDate of Service: 2026-03-01"
    assert find_document_date(text) == "2026-03-01"


def test_find_document_date_falls_back_to_today_when_only_a_dob_is_present():
    assert find_document_date("DOB: 1978-04-22") == date.today().isoformat()


def test_find_document_date_reads_ambiguous_slash_dates_day_first():
    # PHIRE's primary audience is Indian users/clinics: numeric dates are
    # conventionally day-first (DD/MM/YYYY), not the US MM/DD/YYYY
    # convention -- "03/01/2026" means 3 January, not March 1st.
    assert find_document_date("Date of Service: 03/01/2026") == "2026-01-03"


def test_find_document_date_reads_unambiguous_slash_date_regardless_of_order():
    assert find_document_date("Date of Service: 25/12/2026") == "2026-12-25"


def test_find_document_date_reads_dash_separated_numeric_date():
    assert find_document_date("Date of Service: 01-03-2026") == "2026-03-01"


def test_find_document_date_reads_month_name_dates():
    assert find_document_date("Report date: 1 March 2026") == "2026-03-01"
    assert find_document_date("Report date: March 1, 2026") == "2026-03-01"
    assert find_document_date("Report date: 1 Mar 2026") == "2026-03-01"
