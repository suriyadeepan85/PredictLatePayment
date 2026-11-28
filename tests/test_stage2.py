"""Stage 2 behaviour (review 2026-11-28, S2-09). Needs the raw IBM file."""
import os
import warnings
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

RAW_B = "data/raw/ibm_ar.csv"
pytestmark = [pytest.mark.skipif(not os.path.exists(RAW_B), reason="raw data not present"),
              pytest.mark.filterwarnings("ignore:Using the public demo salt")]


@pytest.fixture(scope="module")
def b():
    from src.data.load import load_b
    return load_b(RAW_B)


def _features(b, late_noted_share, seed=42):
    from src.data.notes_generate import generate_notes
    from src.data.masking import load_rules, mask_notes
    from src.features.notes import extract, aggregate
    raw, c = generate_notes(b, seed=seed, late_noted_share=late_noted_share)
    m = mask_notes(raw, c, load_rules())
    return raw, aggregate(m, extract(m), b)


def test_population_is_unpaid_on_stage2_date(b):
    from src.model.train import stage2_population
    p = stage2_population(b)
    assert (p["clear_date"] > p["due_date"] - pd.Timedelta(days=10)).all()
    assert len(p[p["set"] == "train"]) == 1345 and len(p[p["set"] == "test"]) == 320


def test_generator_is_blind_to_outcomes(b):
    from src.data.notes_generate import generate_notes
    shuffled = b.copy()
    rng = np.random.default_rng(0)
    for col in ["clear_date", "days_late", "late"]:
        shuffled[col] = rng.permutation(shuffled[col].values)
    pd.testing.assert_frame_equal(generate_notes(b)[0], generate_notes(shuffled)[0])


def test_late_noted_share_and_routine_notes_on_disputed(b):
    raw, _ = _features(b, 0.3)
    disp = raw[raw["topic"] == "invoice dispute"].merge(b[["invoice_id", "due_date"]], left_on="invoiceNumber", right_on="invoice_id")
    first = disp.groupby("invoiceNumber").agg(first=("note_date", "min"), due=("due_date", "first"))
    assert 0.25 <= (first["first"] > first["due"] - pd.Timedelta(days=10)).mean() <= 0.35
    disputed = set(b.loc[b["disputed"] == 1, "invoice_id"])
    routine = raw[(raw["topic"] != "invoice dispute") & raw["invoiceNumber"].isin(disputed)]
    assert len(routine) > 0                                   # D-109


def test_no_dispute_signal_when_nothing_is_noted_in_time(b):
    """At 0% noted (all disputes logged after the Stage 2 date), no INVOICE-level note signal may predict Disputed.
    Customer-level signals (s5 contacts, s6 tone, s7 claim, s2's contact-change part) may: they read the customer's notes
    about earlier invoices, which are known at scoring time (a customer who often disputes is real information)."""
    from src.model.train import stage2_population
    _, f = _features(b, 1.0)
    d = stage2_population(b).merge(f, on="invoice_id")
    for col in ["has_invoice_note", "s1_open_dispute", "s3_promise", "s4_escalation"]:
        x = d[col].fillna(-9)
        assert abs(roc_auc_score(d["disputed"], x) - 0.5) < 0.06, col
