import pandas as pd
from src.data.masking import load_rules, mask_text, mask_notes, leftover_pii, stand_in

CFG = load_rules()

def test_patterns_and_keys():
    t = "Invoice 6050714721: call Alex Sample on 555-0142 or (317) 555-0199, alex.sample@x.example.com, Ref CASE-12345."
    m = mask_text(t, ["Alex Sample"], CFG)
    assert "6050714721" in m                      # join key untouched
    for leak in ["555-0142", "555-0199", "alex.sample", "CASE-12345", "Alex Sample"]:
        assert leak not in m
    assert m.count("[PHONE]") == 2 and "[EMAIL]" in m and "[REF]" in m

def test_one_way_and_consistent():
    a, b = stand_in("Alex Sample", CFG), stand_in("alex sample", CFG)
    assert a == b and a.startswith("Contact ")

def test_n6_catches_known_values():
    contacts = pd.DataFrame({"customer_id": ["c1"], "contact_name": ["Alex Sample"],
                             "email": ["a@x.example.com"], "phone": ["555-0142"]})
    notes = pd.DataFrame({"customerID": ["c1"], "note_text": ["reach a@x.example.com"]})
    assert len(leftover_pii(notes, contacts, CFG)) == 1
    assert len(leftover_pii(mask_notes(notes, contacts, CFG), contacts, CFG)) == 0
