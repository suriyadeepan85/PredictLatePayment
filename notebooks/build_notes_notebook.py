"""Builds notebooks/05_note_features.ipynb. Run: python notebooks/build_notes_notebook.py"""
import nbformat as nbf
from pathlib import Path
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
md("""# 05 · Notes: generate, mask, read, turn into signals (Stage 2)

1. **Generate** synthetic account notes for the IBM invoices, blind to outcomes (data contract section 6), with obviously fake personal details (D-088). Dispute notes use varied wording, 30% of disputes are first noted only after the Stage 2 date, and routine notes appear on any invoice (D-104, D-109).
2. **Mask** the personal details with plain rules, no LLM, into a second file; check nothing survives (rule N6).
3. **Read** each masked note into structured fields (`specs/note_features.md`).
4. **Aggregate** to the seven signals per invoice, using only notes dated on or before the Stage 2 date (due date minus 10 days).

**Reader used here:** the rules-based stand-in. The Claude Haiku reader (`extract_llm`) has the same output and switches in once Bedrock access is approved (Q-001, Q-003). Its keyword lists are broader than the templates, so it makes some realistic mistakes, but it was still written by the same hand as the templates. The real test of note reading comes with Haiku."""),
code("""import sys; sys.path.insert(0, "..")
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from src.data.load import load_b
from src.data.notes_generate import generate_notes, ALLOWED
from src.data.masking import load_rules, mask_notes, leftover_pii
from src.features.notes import extract, aggregate, SIGNAL_NUMERIC

os.makedirs("../data/generated", exist_ok=True)
b = load_b("../data/raw/ibm_ar.csv")"""),
md("## 1. Generate (seeded, blind to outcomes)"),
code("""print("Columns the generator may see:", ALLOWED)
assert not {"clear_date", "days_late", "late"} & set(ALLOWED)
raw, contacts = generate_notes(b, seed=42)
raw.to_csv("../data/generated/notes_raw.csv", index=False)          # restricted: contains fake personal details
print(f"{len(raw):,} notes for {raw['customerID'].nunique()} customers; {len(contacts)} fake contacts")
raw["topic"].value_counts()"""),
md("""## 2. Mask personal details (rules only) and check rule N6"""),
code("""cfg = load_rules("../config/masking.yaml")
masked = mask_notes(raw, contacts, cfg)
masked.to_csv("../data/generated/notes_masked.csv", index=False)
print("Raw notes containing a known email or phone:", len(leftover_pii(raw, contacts, cfg)))
n6 = leftover_pii(masked, contacts, cfg)
print("N6, masked notes still containing personal data:", len(n6), "(must be 0)")
assert len(n6) == 0
pd.DataFrame({"raw": raw["note_text"].head(4), "masked": masked["note_text"].head(4)})"""),
md("## 3. Quality rules N1 to N6 (shared code: `src/data/notes_checks.py`)"),
code("""from src.data.notes_checks import run_checks
checks = run_checks(masked, b, contacts, cfg)
print(checks)
assert all(v == 0 for v in checks.values())
m = masked.merge(b[["invoice_id", "due_date"]], left_on="invoiceNumber", right_on="invoice_id", how="left")
first_dispute = m[m["topic"] == "invoice dispute"].groupby("invoiceNumber").agg(first=("note_date", "min"), due=("due_date", "first"))
late_noted = (pd.to_datetime(first_dispute["first"]) > first_dispute["due"] - pd.Timedelta(days=10)).mean()
print(f"Disputed invoices whose dispute is first noted after the Stage 2 date: {late_noted:.2f} (target 0.30, D-104)")"""),
md("## 4. Read every masked note"),
code("""signals = extract(masked, reader="rules")
signals.to_csv("../data/generated/note_signals.csv", index=False)
t2 = masked[["note_id", "topic"]].merge(signals, on="note_id")
is_disp = t2["topic"] == "invoice dispute"
# Note level: follow-up notes in a dispute thread often don't use the word "dispute", so this reads lower than the invoice-level check in section 5.
print(f"T2 dispute notes read as dispute: {(t2.loc[is_disp, 'dispute'] == 'yes').mean():.3f}")
print(f"T2 non-dispute notes wrongly read as dispute: {(t2.loc[~is_disp, 'dispute'] == 'yes').mean():.3f}")
signals.drop(columns=["note_id", "promised_date"]).apply(lambda s: s.value_counts()).T.fillna(0).astype(int)"""),
md("## 5. Signals per invoice at the Stage 2 date"),
code("""feats = aggregate(masked, signals, b)
feats.to_csv("../data/generated/note_features.csv", index=False)
fb = b.merge(feats, on="invoice_id")
print("Invoices:", len(fb), "| with an invoice-linked note by the Stage 2 date:", int(fb["has_invoice_note"].sum()))
d = fb[fb["disputed"] == 1]
print(f"T2 (invoice level): disputed invoices with a dispute signal by the Stage 2 date: {(d['s1_reason'] != 'none').mean():.3f}; "
      f"still open: {(d['s1_open_dispute'] == 1).mean():.3f} (the rest were resolved in the notes)")
print(f"T2 (invoice level): undisputed invoices with an open-dispute signal: {(fb.loc[fb['disputed'] == 0, 's1_open_dispute'] == 1).mean():.3f}")
fb[SIGNAL_NUMERIC].describe().T[["count", "mean", "min", "max"]].round(2)"""),
md("""## 6. How the signals relate to lateness (training period only)"""),
code("""tr = fb[fb["set"] == "train"].copy()
def lab(s, yes="Yes", no="No"):
    return s.map({1.0: yes, 0.0: no}).fillna("No note")
panels = {
    "S1 Open dispute": lab(tr["s1_open_dispute"]),
    "S3 Promise to pay": lab(tr["s3_promise"]),
    "S4 Escalation": lab(tr["s4_escalation"]),
    "S6 Tone of latest note": tr["s6_tone"].map({-1.0: "Negative", 0.0: "Neutral", 1.0: "Positive"}).fillna("No note"),
    "S2 Missing PO / contact": lab(tr["s2_po_or_contact"]),
    "S7 Open claim": lab(tr["s7_open_claim"]),
}
sns.set_theme(style="white", font_scale=0.9)
fig, axes = plt.subplots(2, 3, figsize=(15, 7.5), dpi=150)
overall = tr["late"].mean() * 100
for ax, (title, s) in zip(axes.flat, panels.items()):
    g = tr.groupby(s)["late"].agg(["mean", "size"])
    order = [k for k in ["No note", "No", "Yes", "Negative", "Neutral", "Positive"] if k in g.index]
    g = g.loc[order]
    ax.bar(range(len(g)), g["mean"] * 100, color=["#9aa3ad" if k == "No note" else "#2a6fdb" for k in g.index])
    for i, (v, n) in enumerate(zip(g["mean"] * 100, g["size"])):
        ax.text(i, v + 1.5, f"{v:.0f}%\\nn={int(n):,}", ha="center", fontsize=8)
    ax.axhline(overall, ls="--", c="k", lw=1); ax.set_ylim(0, 100)
    ax.set_xticks(range(len(g))); ax.set_xticklabels(g.index)
    ax.set_title(title, loc="left", fontweight="bold"); ax.set_ylabel("Late rate, 3-day grace (%)")
fig.text(0.01, 0.005, f"IBM training invoices (n={len(tr):,}). Dashed line: overall late rate {overall:.1f}%. Notes are synthetic, anchored to real dispute flags.", fontsize=9)
sns.despine(fig); fig.tight_layout(rect=(0, 0.02, 1, 1))
fig.savefig("../docs/img/note_signals.png"); plt.show()"""),
]
nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3"}})
nbf.write(nb, Path(__file__).with_name("05_note_features.ipynb")); print("wrote")
