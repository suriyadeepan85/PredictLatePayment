"""Note reader and note signals S1 to S7 (specs/note_features.md).

Two readers with the same output: `extract_rules` (offline stand-in, used until Bedrock
access is approved: Q-001, Q-003) and `extract_llm` (Claude Haiku 4.5 on Bedrock).
Both read only the masked note text, date and author role.
"""
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd

FIELDS = ["dispute", "dispute_resolved", "reason", "missing_po_or_contact", "promise_to_pay",
          "promised_date", "escalation", "claim", "tone"]
REASONS = ["wrong amount", "duplicate charge", "pricing", "goods or service issue", "other", "none"]
YESNO = {"yes", "no"}
NEG = re.compile(r"frustrat|disput|still waiting|escalat|not confirmed|damaged|won't|on hold|pushed back|contest|challeng", re.I)
POS = re.compile(r"happy|accepted|confirmed payment|will pay as normal|resolved", re.I)


# General keyword lists, deliberately broader than any template, so some routine notes are misread
# (as a real reader would sometimes do). The Haiku reader replaces this when Bedrock is approved.
DISPUTE_RX = re.compile(r"disput|contest|challeng|pushed back|won't pay|on hold|won't accept|doesn't match|charged more|wrong", re.I)
REASON_RX = [("duplicate charge", r"twice|repeat|duplicate"), ("pricing", r"price|rate"),
             ("wrong amount", r"amount|total|charged more|doesn't match"),
             ("goods or service issue", r"damaged|never arrived|wasn't finished|not completed"),
             ("other", r"proof of delivery|line items|documents")]


def extract_rules(text):
    t = text.lower()
    dispute = bool(DISPUTE_RX.search(t)) and not re.search(r"query is resolved|explained the charges", t)
    reason = next((name for name, rx in REASON_RX if re.search(rx, t)), "none") if dispute else "none"
    p = re.search(r"will be made on (\d{4}-\d{2}-\d{2})", t)
    tone = "negative" if NEG.search(t) and not POS.search(t) else "positive" if POS.search(t) else "neutral"
    return {"dispute": "yes" if dispute else "no",
            "dispute_resolved": "yes" if dispute and "resolved" in t else "no",
            "reason": reason,
            "missing_po_or_contact": "yes" if re.search(r"po number|contact has changed", t) else "no",
            "promise_to_pay": "yes" if p else "no", "promised_date": p.group(1) if p else None,
            "escalation": "yes" if re.search(r"escalat|manager to review", t) else "no",
            "claim": "yes" if re.search(r"\bclaim\b", t) else "no", "tone": tone}


def validate(out):
    """Schema check for any reader's output (test T1). Raises on invalid output."""
    if set(out) != set(FIELDS):
        raise ValueError(f"fields {sorted(out)}")
    for k in FIELDS:
        v = out[k]
        if k == "reason":
            ok = v in REASONS
        elif k == "promised_date":
            ok = v is None or bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)))
        elif k == "tone":
            ok = v in {"positive", "neutral", "negative"}
        else:
            ok = v in YESNO
        if not ok:
            raise ValueError(f"{k}={v!r}")
    return out


def extract_llm(row, client, model_id, prompt=None):
    """Claude Haiku 4.5 on Bedrock, temperature 0. One retry on invalid output, then unknown."""
    prompt = prompt or Path(__file__).with_name("prompts").joinpath("note_reader.txt").read_text()
    msg = prompt.format(note_date=row["note_date"], author_role=row["author_role"], note_text=row["note_text"])
    for _ in range(2):
        r = client.converse(modelId=model_id, messages=[{"role": "user", "content": [{"text": msg}]}],
                            inferenceConfig={"temperature": 0, "maxTokens": 300})
        text = r["output"]["message"]["content"][0]["text"]
        try:
            return validate(json.loads(text[text.find("{"): text.rfind("}") + 1]))
        except (ValueError, json.JSONDecodeError):
            continue
    return None


def extract(notes, reader="rules", client=None, model_id=None):
    """One row of signals per note. Reads only note_text (masked), note_date and author_role."""
    rows = []
    for _, r in notes[["note_id", "note_text", "note_date", "author_role"]].iterrows():
        out = extract_rules(r["note_text"]) if reader == "rules" else extract_llm(r, client, model_id)
        rows.append({"note_id": r["note_id"], **(validate(out) if out else {k: None for k in FIELDS})})
    return pd.DataFrame(rows)


def aggregate(notes, signals, invoices):
    """Signals per invoice, using only the customer's notes dated on or before the invoice's
    Stage 2 date (due date minus 10 days). 'No note' stays missing (NaN), never 'no'."""
    n = notes.merge(signals, on="note_id")
    n["note_date"] = pd.to_datetime(n["note_date"])
    by_inv = {k: g.sort_values("note_date") for k, g in n[n["invoiceNumber"].notna()].groupby("invoiceNumber")}
    by_cust = {k: g.sort_values("note_date") for k, g in n.groupby("customerID")}
    yn = lambda b: 1.0 if b else 0.0
    out = []
    for r in invoices[["invoice_id", "customer_id", "invoice_date", "due_date"]].itertuples(index=False):
        cut = r.due_date - pd.Timedelta(days=10)
        f = {"invoice_id": r.invoice_id}
        iv = by_inv.get(r.invoice_id)
        iv = iv[iv["note_date"] <= cut] if iv is not None else None
        cu = by_cust.get(r.customer_id)
        cu = cu[cu["note_date"] <= cut] if cu is not None else None
        has_iv = iv is not None and len(iv) > 0
        has_cu = cu is not None and len(cu) > 0
        f["has_invoice_note"] = yn(has_iv)
        if has_iv:
            d = iv[iv["dispute"] == "yes"]
            f["s1_open_dispute"] = yn(len(d) > 0 and d.iloc[-1]["dispute_resolved"] == "no")
            f["dx_any_dispute_read"] = yn(len(d) > 0)          # diagnostic only, not a model input
            reasons = d[d["reason"] != "none"]["reason"]
            f["s1_reason"] = reasons.iloc[0] if len(reasons) else "none"
            pr = iv[iv["promise_to_pay"] == "yes"]
            f["s3_promise"] = yn(len(pr) > 0)
            f["s3_days_promise_vs_due"] = ((pd.to_datetime(pr.iloc[-1]["promised_date"]) - r.due_date).days
                                           if len(pr) else np.nan)
            f["s4_escalation"] = yn((iv["escalation"] == "yes").any())
        else:
            f.update({"s1_open_dispute": np.nan, "dx_any_dispute_read": np.nan, "s1_reason": "no_note", "s3_promise": np.nan,
                      "s3_days_promise_vs_due": np.nan, "s4_escalation": np.nan})
        window = cu[cu["note_date"] >= r.invoice_date] if has_cu else None
        po = (has_iv and (iv["missing_po_or_contact"] == "yes").any()) or \
             (window is not None and (window["missing_po_or_contact"] == "yes").any())
        f["s2_po_or_contact"] = yn(po) if (has_iv or (window is not None and len(window))) else np.nan
        f["s5_contacts_30d"] = float(((cu["note_date"] > cut - pd.Timedelta(days=30))).sum()) if has_cu else 0.0
        f["s6_tone"] = {"negative": -1.0, "neutral": 0.0, "positive": 1.0}.get(cu.iloc[-1]["tone"], np.nan) if has_cu else np.nan
        f["s7_open_claim"] = yn((cu[cu["note_date"] > cut - pd.Timedelta(days=90)]["claim"] == "yes").any()) if has_cu else np.nan
        out.append(f)
    return pd.DataFrame(out)


SIGNAL_NUMERIC = ["has_invoice_note", "s1_open_dispute", "s2_po_or_contact", "s3_promise", "s3_days_promise_vs_due",
                  "s4_escalation", "s5_contacts_30d", "s6_tone", "s7_open_claim"]
SIGNAL_CATEGORICAL = ["s1_reason"]
