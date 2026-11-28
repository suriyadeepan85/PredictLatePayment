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
# Varied, natural wording (D-104): no fixed "reason" line, and the reason is sometimes not stated.
REASONS = {
    "wrong amount": ["the total doesn't match their PO", "they say we charged more than was agreed",
                     "the amount looks wrong to them"],
    "duplicate charge": ["they think this was billed twice", "it looks like a repeat of last month's invoice to them"],
    "pricing": ["the unit price isn't their contract rate", "they won't accept the new price",
                "they were quoted a lower rate"],
    "goods or service issue": ["part of the delivery arrived damaged", "the work wasn't finished as ordered",
                               "some items never arrived"],
    "other": ["they want proof of delivery first", "they have questions about some of the line items"],
}
OPENERS = ["Customer is disputing invoice {inv} ({amt}){why}.", "Customer won't pay {inv} ({amt}) for now{why}.",
           "Call about {inv}: customer is contesting the charge{why}.", "AP team pushed back on {inv} ({amt}){why}.",
           "Customer has put {inv} on hold{why}.", "Customer challenged invoice {inv}{why}."]
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


def generate_notes(invoices, seed=42, generic_share=0.33, dispute_like_share=0.2,
                   late_noted_share=0.3, reason_stated_share=0.7):
    """Return (notes_raw, contacts). One row per note.

    late_noted_share: share of disputed invoices whose dispute thread starts only after the
    Stage 2 date (between it and the due date), so it is invisible at scoring (D-104, A-008).
    """
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
            reason = rng.choice(list(REASONS))
            why = f": {rng.choice(REASONS[reason])}" if rng.random() < reason_stated_share else ""
            if rng.random() < late_noted_share:          # noted only after the Stage 2 date
                lo, hi = cutoff + pd.Timedelta(days=1), r.due_date
                if hi < lo:
                    hi = lo
            else:
                lo, hi = start, cutoff
            d0 = _date_between(lo, hi, rng)
            add(r, d0, "invoice dispute", rng.choice(OPENERS).format(inv=r.invoice_id, amt=amt, why=why))
            d, cutoff_thread = d0, hi
            for _ in range(rng.integers(0, 3)):
                d = _date_between(d, cutoff_thread, rng)
                add(r, d, "invoice dispute", rng.choice([
                    f"Follow-up on the disputed invoice {r.invoice_id}; customer still waiting for our review.",
                    f"Sent supporting documents for {r.invoice_id}; customer has not confirmed yet.",
                    f"Customer frustrated about the delay resolving {r.invoice_id}."]))
            if rng.random() < 0.3:
                d = _date_between(d, cutoff_thread, rng)
                add(r, d, "invoice dispute", rng.choice([f"Customer asked to escalate the dispute on {r.invoice_id} to a manager.",
                                                         f"Customer wants a manager to review {r.invoice_id}."]))
            if rng.random() < 0.25:                      # realistic contradiction: resolved disputes
                d = _date_between(d, cutoff_thread, rng)
                add(r, d, "invoice dispute", f"Dispute on {r.invoice_id} resolved; customer accepted the explanation and will pay as normal.")
        if rng.random() < generic_share:                 # routine notes on any invoice, disputed or not (D-109)
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
                                                       "Customer asked to switch to electronic billing.",
                                                       "Customer's payment run is on hold until month end; no issue with the invoice.",
                                                       "AP team pushed back their payment run by a week due to a system upgrade."]))
    out = pd.DataFrame(notes).sort_values(["note_date", "customerID"]).reset_index(drop=True)
    out.insert(0, "note_id", [f"N{i:05d}" for i in range(1, len(out) + 1)])
    return out, contacts
