"""Rules-based, one-way masking of personal details in note text (D-088). No LLM.

Works the same at a client: point `contacts` at the CRM contact list and add patterns
in config/masking.yaml.
"""
import hashlib
import os
import re
import pandas as pd
import yaml


def load_rules(path="config/masking.yaml"):
    cfg = yaml.safe_load(open(path))
    cfg["_compiled"] = [(p["name"], re.compile(p["regex"]), p["replace"]) for p in cfg["patterns"]]
    cfg["_salt"] = os.environ.get(cfg["names"]["salt_env"], cfg["names"]["default_salt"])
    return cfg


def stand_in(name, cfg):
    h = hashlib.sha256((cfg["_salt"] + "|" + name.lower()).encode()).hexdigest()
    return cfg["names"]["label"].format(int(h[:8], 16) % 1000)


def mask_text(text, names, cfg):
    for _, rx, rep in cfg["_compiled"]:
        text = rx.sub(rep, text)
    for n in sorted(names, key=len, reverse=True):          # longest first: full names before parts
        text = re.sub(re.escape(n), stand_in(n, cfg), text, flags=re.IGNORECASE)
    return text


def mask_notes(notes, contacts, cfg):
    """Return a masked copy. customerID, invoiceNumber and note_id are join keys and stay as they are."""
    names = contacts.groupby("customer_id")["contact_name"].apply(list).to_dict()
    out = notes.copy()
    out["note_text"] = [mask_text(t, names.get(c, []), cfg) for t, c in zip(out["note_text"], out["customerID"])]
    return out


def leftover_pii(masked, contacts, cfg):
    """Rule N6: rows where anything that looks like personal data survived masking."""
    names = contacts.groupby("customer_id")["contact_name"].apply(list).to_dict()
    known = [v.lower() for v in pd.concat([contacts["email"], contacts["phone"]]).dropna()]
    bad = []
    for i, (t, c) in enumerate(zip(masked["note_text"], masked["customerID"])):
        if any(k in t.lower() for k in known):          # independent of the patterns: exact known values
            bad.append(i); continue
        t_wo_tags = re.sub(r"\[(EMAIL|PHONE|REF)\]", "", t)
        hit = any(rx.search(t_wo_tags) for _, rx, _ in cfg["_compiled"])
        hit = hit or any(n.lower() in t.lower() for n in names.get(c, []))
        if hit:
            bad.append(i)
    return masked.iloc[bad]
