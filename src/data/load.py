"""Load and clean Datasets A and B exactly as docs/data_contract.md v1.4 says."""
import hashlib
import numpy as np
import pandas as pd

GRACE_DAYS = 3                      # calendar days (D-012, D-056)
SHA_A = "3409441a8ecc48438a0fd42421ce3230d95305f7afcefb732bf232a948b6cf88"
SHA_B = "f5d488eaa4c1cc843b478b6f1068c553c5394aab4b64d587e4b9ad811d845c19"
CUT_A = pd.Timestamp("2019-10-01")  # D-063
CUT_B = pd.Timestamp("2013-07-01")  # D-068
MIN_CATEGORY_ROWS = 20              # Q12


def _check_sha(path, expected):
    got = hashlib.sha256(open(path, "rb").read()).hexdigest()
    if got != expected:
        raise ValueError(f"SHA-256 mismatch for {path}: {got}")


def _yyyymmdd(s):
    return pd.to_datetime(s.astype("Int64").astype(str), format="%Y%m%d", errors="coerce")


def _group_rare(s, fit_mask, min_rows=MIN_CATEGORY_ROWS):
    """Q12: codes with fewer than min_rows TRAINING rows become OTHER (counted on training rows only,
    so test and replay data never decide the grouping)."""
    counts = s[fit_mask].value_counts()
    keep = set(counts[counts >= min_rows].index)
    return s.where(s.isin(keep), "OTHER")


def load_a(path, grace_days=GRACE_DAYS, check_sha=True):
    """Dataset A (Customer Invoices). Returns one row per clean invoice, names masked.

    Common columns: invoice_id, customer_id, customer_label, invoice_date, due_date,
    clear_date, amount, terms_days, late, days_late, set (train/test/replay), plus
    business_code and payment_terms.
    """
    if check_sha:
        _check_sha(path, SHA_A)
    raw = pd.read_csv(path)
    log = {"raw": len(raw)}
    df = raw.drop_duplicates()                                   # Q1
    log["Q1 duplicates dropped"] = len(raw) - len(df)
    if df["doc_id"].duplicated().any():                         # Q2
        raise ValueError("Q2: same doc_id with different values")
    n = len(df); df = df[df["document type"] == "RV"]            # Q3
    log["Q3 non-RV dropped"] = n - len(df)
    out = pd.DataFrame({
        "invoice_id": df["doc_id"].astype("int64").astype(str),
        "customer_id": df["cust_number"].astype(str),
        "invoice_date": pd.to_datetime(df["posting_date"]),
        "due_date": _yyyymmdd(df["due_in_date"]),
        "baseline_date": _yyyymmdd(df["baseline_create_date"]),
        "clear_date": pd.to_datetime(df["clear_date"]),
        "amount": df["total_open_amount"],
        "payment_terms": df["cust_payment_terms"].astype(str),
        "business_code": df["business_code"].astype(str),
        "is_open": df["isOpen"].astype(int),
    })
    if out[["invoice_id", "customer_id", "amount"]].isna().any().any() or (out["customer_id"] == "nan").any():  # Q4
        raise ValueError("Q4: missing required value")
    if out[["invoice_date", "due_date", "baseline_date"]].isna().any().any():   # Q4, Q5
        raise ValueError("Q4/Q5: missing or unparseable required date")
    log["Q11 dropped columns"] = "area_business, posting_id, name_customer (masked), invoice_currency, document type, isOpen"
    n = len(out); out = out[~(out["due_date"] < out["invoice_date"])]           # Q6
    log["Q6 due before invoice dropped"] = n - len(out)
    if (out["clear_date"] < out["invoice_date"]).any():                        # Q7
        raise ValueError("Q7: clear date before invoice date")
    if ((out["is_open"] == 0) & out["clear_date"].isna()).any() or ((out["is_open"] == 1) & out["clear_date"].notna()).any():
        raise ValueError("Q8: paid/open status inconsistent with clear date")
    if (out["amount"] <= 0).any():                                             # Q9
        raise ValueError("Q9: amount at or below 0")
    out["terms_days"] = (out["due_date"] - out["baseline_date"]).dt.days
    if not out["terms_days"].between(0, 120).all():                            # Q10
        raise ValueError("Q10: payment terms outside 0 to 120 days")
    fit = (out["invoice_date"] < CUT_A) & (out["is_open"] == 0)               # training rows
    out["payment_terms"] = _group_rare(out["payment_terms"], fit)              # Q12
    out["business_code"] = _group_rare(out["business_code"], fit)
    codes = {c: f"Customer {i:04d}" for i, c in enumerate(sorted(out["customer_id"].unique()), 1)}
    out["customer_label"] = out["customer_id"].map(codes)                      # masking, section 11
    out["days_late"] = (out["clear_date"] - out["due_date"]).dt.days
    out["late"] = np.where(out["clear_date"].notna(), (out["days_late"] > grace_days).astype(float), np.nan)
    out["set"] = np.select([out["is_open"] == 1, out["invoice_date"] < CUT_A], ["replay", "train"], "test")
    log["clean"] = len(out)
    out.attrs["quality_log"] = log
    return out.reset_index(drop=True)


def load_b(path, grace_days=GRACE_DAYS, check_sha=True):
    """Dataset B (IBM). Same common columns as load_a, plus country_code, paperless, disputed.

    `disputed` is an event source (notes) and the ceiling model only; never a deployed-model input.
    """
    if check_sha:
        _check_sha(path, SHA_B)
    raw = pd.read_csv(path, dtype={"invoiceNumber": str, "customerID": str, "countryCode": str})
    if raw["invoiceNumber"].duplicated().any():
        raise ValueError("Q2: duplicate invoiceNumber")
    if raw.isna().any().any():
        raise ValueError("Q4: missing values")
    d = lambda c: pd.to_datetime(raw[c], format="%m/%d/%Y")
    out = pd.DataFrame({
        "invoice_id": raw["invoiceNumber"], "customer_id": raw["customerID"],
        "invoice_date": d("InvoiceDate"), "due_date": d("DueDate"), "clear_date": d("SettledDate"),
        "amount": raw["InvoiceAmount"], "country_code": raw["countryCode"],
        "paperless": (raw["PaperlessBill"] == "Electronic").astype(int),
        "disputed": (raw["Disputed"] == "Yes").astype(int),
    })
    if (out["clear_date"] < out["invoice_date"]).any() or (out["amount"] <= 0).any():
        raise ValueError("Q7/Q9 failed")
    out["terms_days"] = (out["due_date"] - out["invoice_date"]).dt.days
    out["stage2_date"] = out["due_date"] - pd.Timedelta(days=10)
    out["days_late"] = (out["clear_date"] - out["due_date"]).dt.days
    out["late"] = (out["days_late"] > grace_days).astype(float)
    out["set"] = np.where(out["invoice_date"] < CUT_B, "train", "test")
    out.attrs["quality_log"] = {"raw": len(raw), "clean": len(out)}
    return out
