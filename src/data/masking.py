"""Rules-based, one-way masking of personal details in note text (D-088). No LLM.

Works the same at a client: point `contacts` at the CRM contact list and add patterns
in config/masking.yaml. Known business keys are protected first so they are never altered.
"""
import hashlib
import os
import re
import unicodedata
import warnings
import pandas as pd
import yaml


def load_rules(path="config/masking.yaml", demo=True):
    cfg = yaml.safe_load(open(path))
    cfg["_compiled"] = [(p["name"], re.compile(p["regex"]), p["replace"]) for p in cfg["patterns"]]
    salt = os.environ.get(cfg["names"]["salt_env"])
    if not salt:
        if not demo:
            raise RuntimeError(f"Set {cfg['names']['salt_env']} before masking real data")
        warnings.warn("Using the public demo salt for masking stand-ins")
        salt = cfg["names"]["default_salt"]
    cfg["_salt"] = salt
    return cfg


def _fold(s):
    """Lower case, strip accents, collapse whitespace."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def stand_in(name, cfg):
    h = hashlib.sha256((cfg["_salt"] + "|" + _fold(name)).encode()).hexdigest()
    return cfg["names"]["label"].format(int(h[:8], 16) % 1000)


def _name_patterns(full, cfg):
    """Regexes for one contact: full name, 'Last, First', and each part alone (whole words, any spacing)."""
    parts = _fold(full).split(" ")
    sep = r"[\s,]+"
    pats = [sep.join(map(re.escape, parts)), sep.join(map(re.escape, reversed(parts)))]
    pats += [re.escape(p) for p in parts if len(p) >= cfg["names"].get("min_part_length", 3)]
    return [re.compile(r"(?<![A-Za-z])" + p + r"(?![A-Za-z])", re.IGNORECASE) for p in pats]


def _known_value_patterns(phones=(), emails=()):
    """Exact known contact values in any spacing or separators (from the contact list)."""
    pats = []
    for ph in phones:
        d = re.sub(r"\D", "", str(ph))
        if len(d) >= 7:
            pats.append((re.compile(r"[\s().-]?".join(d)), "[PHONE]"))
    for em in emails:
        pats.append((re.compile(r"\s*".join(map(re.escape, str(em))), re.IGNORECASE), "[EMAIL]"))
    return pats


def mask_text(text, names, cfg, keys=(), phones=(), emails=()):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    protected = {}
    for i, k in enumerate(sorted({str(k) for k in keys if k}, key=len, reverse=True)):
        tok = f"\x00K{i}\x00"
        if k in text:
            text = text.replace(k, tok); protected[tok] = k
    for rx, rep in _known_value_patterns(phones, emails):
        text = rx.sub(rep, text)
    for _, rx, rep in cfg["_compiled"]:
        text = rx.sub(rep, text)
    for n in sorted(names, key=len, reverse=True):
        label = stand_in(n, cfg)
        for rx in _name_patterns(n, cfg):
            text = rx.sub(label, text)
    for tok, k in protected.items():
        text = text.replace(tok, k)
    return text


def mask_notes(notes, contacts, cfg):
    """Return a masked copy. customerID, invoiceNumber and note_id are join keys and stay as they are."""
    g = contacts.groupby("customer_id")
    names, phones, emails = (g[c].apply(list).to_dict() for c in ["contact_name", "phone", "email"])
    out = notes.copy()
    keys_cols = [c for c in ["invoiceNumber", "customerID"] if c in out.columns]
    out["note_text"] = [mask_text(r["note_text"], names.get(r["customerID"], []), cfg,
                                  keys=[r[c] for c in keys_cols if pd.notna(r[c])],
                                  phones=phones.get(r["customerID"], []), emails=emails.get(r["customerID"], []))
                        for _, r in out.iterrows()]
    return out


def leftover_pii(masked, contacts, cfg):
    """Rule N6, independent of the masking patterns: exact known emails and phones (digits only),
    and any contact first name, last name or full name as a whole word."""
    names = contacts.groupby("customer_id")["contact_name"].apply(list).to_dict()
    emails = [e.lower() for e in contacts["email"].dropna()]
    phones = [re.sub(r"\D", "", p) for p in contacts["phone"].dropna()]
    bad = []
    for i, (t, c) in enumerate(zip(masked["note_text"], masked["customerID"])):
        low, digits = _fold(t), re.sub(r"\D", "", t)
        hit = any(e in low.replace(" ", "") for e in emails) or any(p and p in digits for p in phones)
        for n in names.get(c, []):
            parts = [p for p in _fold(n).split(" ") if len(p) >= cfg["names"].get("min_part_length", 3)]
            hit = hit or any(re.search(r"(?<![a-z])" + re.escape(p) + r"(?![a-z])", low) for p in parts)
        if hit:
            bad.append(i)
    return masked.iloc[bad]
