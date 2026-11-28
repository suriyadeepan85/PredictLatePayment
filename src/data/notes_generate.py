"""Blind, seeded generation of synthetic account notes for Dataset B (data contract section 6).

The generator receives only the columns allowed by rule 2. Outcome columns (clear date,
days late, late) are dropped in code before generation. Notes include obviously fake
personal details (D-088): names from a fixed fake list, @example.com emails, 555 phones.
"""
import numpy as np
import pandas as pd

ALLOWED = ["invoice_id", "customer_id", "invoice_date", "due_date", "amount", "paperless", "disputed"]
FIRST = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Avery", "Quinn", "Drew",
         "Robin", "Sam", "Parker", "Reese", "Skyler", "Dana", "Kendall", "Rowan", "Emerson", "Hayden"]
LAST = ["Sample", "Testwell", "Fakeham", "Mockford", "Placeholder", "Dummyson", "Notreal", "Synthton",
        "Exampleby", "Fictor"]
REASONS = {
    "wrong amount": ["the invoiced amount does not match the PO", "they say the total is higher than agreed"],
    "duplicate charge": ["they believe this was billed twice", "a duplicate of an earlier invoice, per the customer"],
    "pricing": ["the unit price is not the contracted rate", "they dispute the price increase"],
    "goods or service issue": ["part of the delivery was damaged", "the service was not completed as ordered"],
    "other": ["they raised a query on the line items", "they want supporting documents before paying"],
}
GENERIC_TOPICS = ["claim", "missing PO", "contact change", "payment promise", "general query"]


def make_contacts(customers, rng):
    rows = []
    used = set()
    for c in customers:
        for _ in range(rng.integers(1, 4)):
            while True:
                name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
                if (c, name) not in used:
                    used.add((c, name)); break
            first, last = name.split()
            rows.append({"customer_id": c, "contact_name": name,
                         "email": f"{first.lower()}.{last.lower()}@cust{c[-4:]}.example.com",
                         "phone": f"555-01{rng.integers(0, 100):02d}"})
    return pd.DataFrame(rows)


def _pii(contact, rng):
    """Optional personal details appended to a note."""
    bits = []
    if rng.random() < 0.7: bits.append(f"Spoke with {contact.contact_name}.")
    if rng.random() < 0.3: bits.append(f"Email: {contact.email}.")
    if rng.random() < 0.2: bits.append(f"Call back on {contact.phone}.")
    if rng.random() < 0.3: bits.append(f"Ref CASE-{rng.integers(10000, 99999)}.")
    return " ".join(bits)


def _date_between(start, end, rng):
    days = max((end - start).days, 0)
    return start + pd.Timedelta(days=int(rng.integers(0, days + 1)))


def generate_notes(invoices, seed=42, generic_share=0.33, dispute_like_share=0.2):
    """Return (notes_raw, contacts). One row per note."""
    inv = invoices[ALLOWED].copy()                      # rule 2: nothing else reaches the generator
    rng = np.random.default_rng(seed)
    contacts = make_contacts(sorted(inv["customer_id"].unique()), rng)
    by_cust = {c: g.reset_index(drop=True) for c, g in contacts.groupby("customer_id")}
    notes = []

    def add(r, when, topic, text, inv_link=True):
        ct = by_cust[r.customer_id].iloc[rng.integers(0, len(by_cust[r.customer_id]))]
        extra = _pii(ct, rng)
        notes.append({"customerID": r.customer_id, "invoiceNumber": r.invoice_id if inv_link else None,
                      "topic": topic, "note_date": when,
                      "author_role": rng.choice(["customer service", "receivables analyst"]),
                      "channel": rng.choice(["call", "email", "portal"]),
                      "note_text": (text + " " + extra).strip()})

    for r in inv.itertuples(index=False):
        start, cutoff = r.invoice_date, r.due_date - pd.Timedelta(days=10)
        if cutoff < start:
            cutoff = start
        amt = f"${r.amount:,.2f}"
        if r.disputed == 1:                              # every disputed invoice gets a dispute thread
            reason = rng.choice(list(REASONS)); detail = rng.choice(REASONS[reason])
            d0 = _date_between(start, cutoff, rng)
            add(r, d0, "invoice dispute", f"Customer disputes invoice {r.invoice_id} ({amt}): {detail}. Reason logged: {reason}.")
            d = d0
            for _ in range(rng.integers(0, 3)):
                d = _date_between(d, cutoff, rng)
                add(r, d, "invoice dispute", rng.choice([
                    f"Follow-up on the disputed invoice {r.invoice_id}; customer still waiting for our review.",
                    f"Sent supporting documents for {r.invoice_id}; customer has not confirmed yet.",
                    f"Customer frustrated about the delay resolving {r.invoice_id}."]))
            if rng.random() < 0.3:
                d = _date_between(d, cutoff, rng)
                add(r, d, "invoice dispute", f"Customer asked to escalate the dispute on {r.invoice_id} to a manager.")
            if rng.random() < 0.25:                      # realistic contradiction: resolved disputes
                d = _date_between(d, cutoff, rng)
                add(r, d, "invoice dispute", f"Dispute on {r.invoice_id} resolved; customer accepted the explanation and will pay as normal.")
        elif rng.random() < generic_share:
            d = _date_between(start, cutoff, rng)
            if rng.random() < dispute_like_share:        # dispute-like but not a flagged dispute
                add(r, d, "general query", f"Customer queried the amount on {r.invoice_id}; explained the charges and the query is resolved.")
                continue
            topic = rng.choice(GENERIC_TOPICS)
            if topic == "claim":
                add(r, d, "claim", rng.choice(["Customer opened a claim about a damaged shipment on another order.",
                                                "Claim for short delivery raised on the account; under review."]), inv_link=False)
            elif topic == "missing PO":
                add(r, d, "missing PO", f"Customer says invoice {r.invoice_id} needs a PO number before it can be approved.")
            elif topic == "contact change":
                add(r, d, "contact change", "Accounts payable contact has changed; invoices should go to the new contact.", inv_link=False)
            elif topic == "payment promise":
                promise = d + pd.Timedelta(days=int(rng.integers(3, 25)))
                add(r, d, "payment promise", f"Customer confirmed payment for {r.invoice_id} will be made on {promise:%Y-%m-%d}.")
            else:
                add(r, d, "general query", rng.choice(["Customer asked for a copy of the invoice. Sent.",
                                                       "Routine check-in; customer happy with the service.",
                                                       "Customer asked to switch to electronic billing."]))
    out = pd.DataFrame(notes).sort_values(["note_date", "customerID"]).reset_index(drop=True)
    out.insert(0, "note_id", [f"N{i:05d}" for i in range(1, len(out) + 1)])
    return out, contacts
