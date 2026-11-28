"""F5, F6, T4, T5 and N-rule tests. F6 and the N-rule test need the raw data and are skipped without it."""
import os
import numpy as np
import pandas as pd
import pytest
from src.model import train as T

RAW_A, RAW_B = "data/raw/customer_invoices.csv", "data/raw/ibm_ar.csv"
OUTCOMES = {"clear_date", "days_late", "late", "set"}


def test_f5_no_outcome_inputs():
    for num, cat in [(T.NUMERIC_STAGE1, T.CATEGORICAL_STAGE1), *T.ibm_inputs().values()]:
        assert not OUTCOMES & set(num + cat)
    a_num, a_cat = T.ibm_inputs()["model_a"]; b_num, b_cat = T.ibm_inputs()["model_b"]
    assert "disputed" not in a_num + a_cat + b_num + b_cat          # only the ceiling may use it
    assert "disputed" in T.ibm_inputs()["ceiling"][0]
    for banned in ["customer_id", "customer_label", "invoice_id"]:
        assert banned not in T.NUMERIC_STAGE1 + T.CATEGORICAL_STAGE1


@pytest.mark.skipif(not os.path.exists(RAW_A), reason="raw data not present")
def test_f6_row_counts_match_contract():
    from src.data.load import load_a, load_b
    a = load_a(RAW_A); b = load_b(RAW_B)
    assert len(a) == 48702
    assert a["set"].value_counts().to_dict() == {"train": 26522, "test": 12526, "replay": 9654}
    assert b["set"].value_counts().to_dict() == {"train": 1930, "test": 536}


def test_t4_reader_sees_only_masked_text_date_role():
    import inspect
    from src.features import notes
    src = inspect.getsource(notes.extract)
    assert '["note_id", "note_text", "note_date", "author_role"]' in src
    for banned in ["topic", "disputed", "late", "clear_date"]:
        assert f'"{banned}"' not in src


@pytest.mark.skipif(not os.path.exists(RAW_B), reason="raw data not present")
def test_t5_and_n_rules_on_generated_notes():
    from src.data.load import load_b
    from src.data.notes_generate import generate_notes
    from src.data.masking import load_rules, mask_notes
    from src.data.notes_checks import run_checks
    from src.features.notes import extract
    b = load_b(RAW_B)
    raw1, c1 = generate_notes(b, seed=42); raw2, _ = generate_notes(b, seed=42)
    pd.testing.assert_frame_equal(raw1, raw2)                          # generation repeatable
    cfg = load_rules(); m = mask_notes(raw1, c1, cfg)
    pd.testing.assert_frame_equal(extract(m), extract(m))              # T5 reader repeatable
    assert all(v == 0 for v in run_checks(m, b, c1, cfg).values())
