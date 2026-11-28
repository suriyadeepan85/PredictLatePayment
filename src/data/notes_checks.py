"""Quality rules N1 to N6 for Dataset C (data contract section 8). Each returns a count of failures."""
import pandas as pd
from src.data.masking import leftover_pii


def run_checks(masked, invoices, contacts, cfg, generated_topics=True):
    m = masked.copy(); m["note_date"] = pd.to_datetime(m["note_date"])
    inv = invoices.set_index("invoice_id")
    linked = m[m["invoiceNumber"].notna()].join(inv[["customer_id", "invoice_date", "due_date"]], on="invoiceNumber")
    stage2 = linked["due_date"] - pd.Timedelta(days=10)
    out = {
        "N1 unknown customer": int((~m["customerID"].isin(invoices["customer_id"])).sum()),
        "N1 unknown invoice or wrong customer": int((linked["customer_id"] != linked["customerID"]).sum()),
        "N2 invoice note outside invoice date..Stage 2 date": int(((linked["note_date"] < linked["invoice_date"]) |
                                                                    (linked["note_date"] > stage2)).sum()),
        "N3 duplicate note_id or empty text": int(m["note_id"].duplicated().sum() + (m["note_text"].str.strip() == "").sum()),
        "N6 personal data left after masking": len(leftover_pii(masked, contacts, cfg)),
    }
    if generated_topics:
        disputed = set(invoices.loc[invoices["disputed"] == 1, "invoice_id"])
        threads = set(m.loc[m["topic"] == "invoice dispute", "invoiceNumber"])
        out["N5 disputed invoice without a dispute thread"] = len(disputed - threads)
    return out
