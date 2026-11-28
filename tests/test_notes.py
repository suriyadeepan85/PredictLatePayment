import json
import numpy as np
import pandas as pd
import pytest
from src.features.notes import extract_rules, validate, extract_llm, aggregate, FIELDS

def test_rules_reader_schema_and_values():
    o = validate(extract_rules("Customer disputes invoice 123 ($5.00): billed twice. Reason logged: duplicate charge."))
    assert o["dispute"] == "yes" and o["reason"] == "duplicate charge" and o["tone"] == "negative"
    o = extract_rules("Customer queried the amount on 123; explained the charges and the query is resolved.")
    assert o["dispute"] == "no"                       # dispute-like query is not a dispute
    o = extract_rules("Customer confirmed payment for 123 will be made on 2013-05-02.")
    assert o["promise_to_pay"] == "yes" and o["promised_date"] == "2013-05-02"

def test_validate_rejects_bad_output():
    bad = {k: "yes" for k in FIELDS}; bad["tone"] = "angry"
    with pytest.raises(ValueError):
        validate(bad)

def test_llm_reader_retries_then_gives_unknown():
    class Fake:
        calls = 0
        def converse(self, **kw):
            Fake.calls += 1
            return {"output": {"message": {"content": [{"text": "not json"}]}}}
    row = {"note_date": "2013-01-01", "author_role": "x", "note_text": "y"}
    assert extract_llm(row, Fake(), "m", prompt="{note_date}{author_role}{note_text}") is None and Fake.calls == 2

def test_cutoff_and_no_note():
    inv = pd.DataFrame({"invoice_id": ["i1", "i2"], "customer_id": ["c1", "c2"],
                        "invoice_date": pd.to_datetime(["2013-01-01"] * 2), "due_date": pd.to_datetime(["2013-01-31"] * 2)})
    notes = pd.DataFrame({"note_id": ["n1", "n2"], "customerID": ["c1", "c1"], "invoiceNumber": ["i1", "i1"],
                          "note_date": pd.to_datetime(["2013-01-05", "2013-01-25"]),   # n2 is after the Stage 2 date (Jan 21)
                          "note_text": ["Customer disputes invoice i1. Reason logged: pricing.",
                                        "Dispute on i1 resolved; customer accepted."], "author_role": ["a", "a"]})
    sig = pd.DataFrame([{"note_id": i, **extract_rules(t)} for i, t in zip(notes.note_id, notes.note_text)])
    f = aggregate(notes, sig, inv).set_index("invoice_id")
    assert f.loc["i1", "s1_open_dispute"] == 1.0      # the later 'resolved' note is not visible yet
    assert np.isnan(f.loc["i2", "s1_open_dispute"]) and f.loc["i2", "s1_reason"] == "no_note"
