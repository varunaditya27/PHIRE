"""Tests for reference-corpus text rendering: USDA natural-language sentences and MedlinePlus spacing."""

from ml.rag.ingest import usda
from ml.rag.ingest.medlineplus import _strip_html
from ml.rag.ingest.reformat_corpus import reformat_text
from ml.rag.ingest.text_cleanup import fix_sentence_spacing

SALMON = {
    "fdc_id": 175167,
    "description": "Fish, salmon, Atlantic, wild, raw",
    "nutrients": {"Energy": "142 kcal", "Protein": "19.8 g", "Fat": "6.34 g", "Sodium": "44 mg", "Vitamin D": "10.9 ug"},
}


def test_food_text_states_qualitative_claims_in_sentences():
    text = usda.format_food_text(SALMON)

    assert "Fish, salmon, Atlantic, wild, raw is high in protein: it provides 19.8 grams per 100 grams, 40% of the daily value." in text
    assert "is high in vitamin D" in text            # 10.9 ug of 20 ug DV = 55%
    assert "is low in sodium" in text
    assert "Per 100 grams, Fish, salmon, Atlantic, wild, raw contains 142 calories of energy, 19.8 grams of protein" in text
    assert text.endswith("Source: USDA FoodData Central (fdcId 175167).")
    assert "per 100g:" not in text                   # the old key-value form is gone
    assert " g " not in text and " mg" not in text   # units are spelled out


def test_good_source_and_no_claim_tiers():
    egg = {"fdc_id": 1, "description": "Egg", "nutrients": {"Protein": "6 g", "Iron": "0.5 mg"}}  # 12% DV protein, 3% iron

    text = usda.format_food_text(egg)

    assert "Egg is a good source of protein" in text
    assert "iron:" not in text.split("Per 100 g")[0]  # 3% DV earns no qualitative claim


def test_old_format_round_trips_into_the_new_format():
    old = "Apples, raw, without skin — per 100g: Energy 48 kcal, Protein 0.27 g, Vitamin C 4 mg. Source: USDA FoodData Central (fdcId 171689)."

    food = usda.parse_old_food_text(old)

    assert food == {"fdc_id": "171689", "description": "Apples, raw, without skin",
                    "nutrients": {"Energy": "48 kcal", "Protein": "0.27 g", "Vitamin C": "4 mg"}}
    new = reformat_text("usda", old)
    assert new != old and "contains 48 calories of energy" in new
    assert reformat_text("usda", new) == new         # idempotent: already-new text is untouched


def test_non_usda_text_is_not_parsed_as_old_format():
    assert usda.parse_old_food_text("LDL is a type of cholesterol.") is None


def test_sentence_spacing_repair_only_touches_glued_sentences():
    assert fix_sentence_spacing("risk of disease.What are LDL?LDL and HDL") == "risk of disease. What are LDL? LDL and HDL"
    assert fix_sentence_spacing("HbA1c was 6.1% on 12.03.2026 and U.S.Army data") == "HbA1c was 6.1% on 12.03.2026 and U.S.Army data"


def test_medlineplus_strip_html_separates_blocks_but_not_inline_highlights():
    raw = '<p>Cholesterol is <span class="qt0">waxy</span> stuff.</p><p>What are LDL?</p>'

    assert _strip_html(raw) == "Cholesterol is waxy stuff. What are LDL?"
