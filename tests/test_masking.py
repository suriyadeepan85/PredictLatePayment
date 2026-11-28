import pandas as pd
import pytest
from src.data.masking import load_rules, mask_text, mask_notes, leftover_pii, stand_in

CFG = load_rules()
NAMES = ["Alex Sample"]

@pytest.mark.parametrize("text,leak", [
    ("Spoke with Alex Sample.", "Sample"), ("Spoke with alex  sample.", "sample"),
    ("Sample, Alex called.", "Sample"), ("Alex called back.", "Alex"), ("Mr Sample called.", "Sample"),
    ("Spoke with Alex\nSample.", "Sample"), ("Call 555-0142.", "555-0142"), ("Call (317) 555-0199.", "555-0199"),
    ("Call 3175550199.", "3175550199"), ("Mail alex.sample@x.example.com", "alex.sample"),
    ("Mail alex @ x.example.com", "x.example"), ("ref case 12345", "12345"), ("Ticket #45678", "45678"),
])
def test_no_leaks(text, leak):
    assert leak not in mask_text(text, NAMES, CFG, keys=["6050714721"])

def test_keys_never_damaged():
    for t in ["Invoice 6050714721 due", "Invoice 6050714721-555-0142", "Ref 6050714721."]:
        assert "6050714721" in mask_text(t, NAMES, CFG, keys=["6050714721"])

def test_no_overmasking_inside_words():
    assert "Alexandria" in mask_text("Ship to Alexandria", NAMES, CFG)

def test_one_way_and_consistent():
    assert stand_in("Alex Sample", CFG) == stand_in("alex  SAMPLE", CFG)

def test_n6_independent_of_patterns():
    contacts = pd.DataFrame({"customer_id": ["c1"], "contact_name": ["Alex Sample"],
                             "email": ["a@x.example.com"], "phone": ["555-0142"]})
    notes = pd.DataFrame({"customerID": ["c1"] * 3, "invoiceNumber": [None] * 3,
                          "note_text": ["reach a@x.example.com", "call 5550142", "Sample said hi"]})
    assert len(leftover_pii(notes, contacts, CFG)) == 3
    assert len(leftover_pii(mask_notes(notes, contacts, CFG), contacts, CFG)) == 0

def test_real_data_requires_salt(monkeypatch):
    monkeypatch.delenv("LPP_MASK_SALT", raising=False)
    with pytest.raises(RuntimeError):
        load_rules(demo=False)
