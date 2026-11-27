# Decisions and observations

Format and rules: `specs/methodology.md`. Claude records as PROPOSED; only the owner changes status.

Seeded on November 26, 2026 from the planning conversation (November 13 to 26). Records the owner has already agreed to in chat are still PROPOSED until confirmed here.

## Scope and governance

| ID | Type | Statement | Status | By | Evidence |
|---|---|---|---|---|---|
| D-001 | decision | Hackathon scope is Stage 1 only: score each invoice when it's created. Due November 30, 2026. Deliverables: a deck and a working application | PROPOSED | Owner | Owner, Nov 24: "stage one is sufficient for now" |
| D-002 | observation | Judges are delivery leaders and AI practice heads | PROPOSED | Owner | Owner, Nov 24 |
| D-003 | decision | No client data. The client's problem may be described; no client or customer names | PROPOSED | Owner | Owner, Nov 24: "Do not name customers like Walmart, Target" |
| D-004 | decision | Stage 2 (interaction notes, 10-day re-check) is deferred until after the hackathon | PROPOSED | Owner | Owner, Nov 24: "We'll think about stage 2 later" |
| D-005 | decision | The model must not flag customers unfairly | PROPOSED | Owner | Owner, Nov 24: "It should not unfairly flag" |
| D-006 | decision | Light build: Claude builds in session, repo holds all state, owner approves at gates G1 (data contract), G2 (features), G3 (model and fairness results), G6 (demo script). Folders are laid out so it can grow into the full multi-agent build later | PROPOSED | Claude | Spec v2, section 17 |
| D-007 | decision | Conversation-to-specification methodology, lean version (3 record files, evidence by file path) | APPROVED (owner, Nov 26) | Owner | Owner, Nov 26: "yes push"; `specs/methodology.md` |
| D-008 | decision | Repo is authoritative for build specs; spec v2 (Claude Doc) is the product and pitch narrative; spec v1 kept unchanged | PROPOSED | Claude | `CLAUDE.md` |
| D-009 | decision | Repository: github.com/suriyadeepan85/PredictLatePayment | PROPOSED | Owner | Owner, Nov 24 |

## Data

| ID | Type | Statement | Status | By | Evidence |
|---|---|---|---|---|---|
| D-010 | decision | Customer Invoices (50,000 rows, Kaggle) trains and tests Stage 1. IBM Late Payment Histories is used only to show reusability | PROPOSED | Owner | Owner, Nov 21: "Let's use what you proposed for data" |
| D-011 | decision | Raw data never goes into git; kept in `data/raw/`, verified by SHA-256 | PROPOSED | Claude | `.gitignore`, `docs/data_contract.md` section 1 |
| D-012 | decision | Late = paid more than **3 days** after the due date. Configurable. (Set to 5 days, then changed to 3 the same day) | PROPOSED | Owner | Owner, Nov 26: "change the grace period to 3 days" |
| D-013 | decision | Split by time at October 1, 2019. Open invoices are a demo replay set, never used for accuracy | PROPOSED | Claude | Chart 1, `docs/img/data_profile_grace3.png` |
| D-014 | decision | Column roles and quality rules Q1 to Q13 as written in the data contract | PROPOSED | Claude | `docs/data_contract.md` sections 4 and 5 |
| D-015 | decision | Drop the 131 invoices whose due date is before their invoice date | PROPOSED | Claude | `docs/data_contract.md`, rule Q6 |
| D-016 | decision | Payment terms are measured from the baseline date, not the posting date | PROPOSED | Claude | `docs/data_contract.md` section 4 |
| D-017 | decision | Customer names are masked as "Customer 0001" and so on, everywhere | PROPOSED | Claude | `docs/data_contract.md` section 8 |
| D-018 | decision | Profiling lives in a notebook the owner can run in SageMaker or locally | PROPOSED | Owner | Owner, Nov 26: "create"; `notebooks/01_profile_data.ipynb` |

## Model, evaluation and fairness

| ID | Type | Statement | Status | By | Evidence |
|---|---|---|---|---|---|
| D-020 | decision | Model: XGBoost on payment history built as of each invoice date; reasons in plain words from SHAP values | PROPOSED | Claude | Spec v2, section 8 |
| D-021 | decision | Measure AUC and the share of late invoices caught in the top 20% of flags against a "late last time" baseline. Never plain accuracy | PROPOSED | Claude | Chart 3 (15% late rate) |
| D-022 | decision | Fairness: names and customer IDs are never inputs; flag rates, false alarms and misses compared by business unit; no group's false-alarm rate above 1.25 times the overall rate unless that group genuinely pays late more often | PROPOSED | Claude | Spec v2, section 11; chart 4 |

## Application

| ID | Type | Statement | Status | By | Evidence |
|---|---|---|---|---|---|
| D-030 | decision | Streamlit app. Must: control panel, risk dashboard, invoice detail, model evidence. Should: Bedrock outreach draft, business impact page, IBM setup page. Could: AWS deployment, alerts | PROPOSED | Claude | Spec v2, sections 1.1 and 16 |
| D-031 | decision | The AI drafts outreach; a human approves; nothing is sent automatically; every draft is logged | PROPOSED | Claude | Spec v2, section 16 |

## Observations from the data (3-day grace)

| ID | Type | Statement | Status | By | Evidence |
|---|---|---|---|---|---|
| D-040 | observation | 1,161 exact duplicate rows; every repeated doc_id is an exact copy | PROPOSED | Claude | Notebook section 3 |
| D-041 | observation | All open invoices were posted after all paid ones | PROPOSED | Claude | Chart 1 |
| D-042 | observation | Late share: 42% at 0 days, 15% at 3, 9% at 5, 7% at 7 | PROPOSED | Claude | Chart 3 |
| D-043 | observation | Late rate by business unit: U001/USD 11%, CA02/CAD 54%, U002 50%, U013 42%; overall 15% | PROPOSED | Claude | Chart 4 |
| D-044 | observation | 27% of rows come from 2 customer numbers with retailer-like names; up to 11 name spellings per customer number | PROPOSED | Claude | Notebook section 8 |
| D-045 | observation | 861 of 1,423 customers have fewer than 5 invoices; 99% of open invoices' customers have paid history | PROPOSED | Claude | Notebook sections 5 and 7 |
| D-046 | observation | The dataset has no grace-period or reminder field | PROPOSED | Claude | `docs/data_contract.md` section 3 |
| D-047 | observation | After cleaning: 48,702 invoices; train 26,522 (15.3% late), test 12,526 (13.5% late), replay 9,654 | PROPOSED | Claude | `docs/data_contract.md` section 6 |

## Added November 26, 2026 (voice session, written up in text)

| ID | Type | Statement | Status | By | Evidence |
|---|---|---|---|---|---|
| D-050 | decision | Bring the LLM note features back into scope: synthetic interaction notes, an LLM extracts signals, signals become model features. Reverses D-004 | PROPOSED | Owner | Owner, Nov 26 (voice): "you want the note features back in scope" |
| D-051 | decision | Two predictions: on the invoice date (Stage 1) and 10 days before the due date (Stage 2, using notes) | PROPOSED | Owner | Owner, Nov 26 (voice): "prediction on invoice day and prediction on 10th day before due date" |
| D-052 | decision | Nothing is dropped from scope. Build order: model and core screens, then note features and Stage 2, then outreach draft, business impact page and IBM setup page | PROPOSED | Owner | Owner, Nov 26 (voice): "I don't want to drop anything" |
| D-053 | decision | Every approved decision is turned into the specs used for detailed development | PROPOSED | Owner | Owner, Nov 26 (voice) |
| D-054 | decision | Change requests (CRs) govern spec changes in the full build; the hackathon build uses direct owner approval | PROPOSED | Owner | Owner, Nov 26 (voice): "use CR for any changes" |
| D-055 | decision | Component specs for the hackathon: data contract, feature list, note features, evaluation and fairness, app screens, demo script. Role specs (coordinator, ML, LLM, app, DevOps, reviewer) come with the full build | PROPOSED | Claude | Voice session, Nov 26 |
| D-056 | decision | The grace period is counted in calendar days | APPROVED (owner, Nov 26) | Owner | Owner, Nov 26: answered "Calendar days" to Q-009 |
| D-057 | decision | Adopt the owner's data contract v1.1 as the base and extend it to v1.2 with a notes section and the 10-day scoring time | APPROVED (owner, Nov 26) | Owner | Owner, Nov 26: answered "Yes, extend to v1.2" to Q-011 |
| D-058 | observation | Prior paid invoices at scoring time: 0 for 10.7% of training invoices but only 1.1% of test and 1.0% of replay invoices; 10 or more for 93% of test invoices. Late rate falls with history: 27% (0 prior), 23% (1-4), 19% (5-9), 13% (10+) | PROPOSED | Claude | History count profile, Nov 26 |
| D-059 | decision | Two models: Stage 1 trained and measured on the 50,000-row data (authentic); Stage 2 (note features, 10 days before due) trained and measured on IBM, where notes describe real disputes | APPROVED (owner, Nov 26) | Owner | Owner, Nov 26: answered "Yes, two models" to Q-008 |
| D-060 | decision | All data profiling, data preparation, feature engineering and visualizations live in notebooks the owner can run. Shared logic sits in `src/` and the notebooks import it, so notebooks, app and tests use the same code | PROPOSED | Owner | Owner, Nov 26: "For all the data profiling, another data related things I need, visualizations and everything I need the notebook" |
| D-061 | decision | History groups by prior paid invoices at scoring time: none = 0, limited = 1 to 4, enough = 5 or more | APPROVED (owner, Nov 26) | Owner | Owner, Nov 26: answered "Approve 0 / 1-4 / 5+" to Q-010; `notebooks/02_history_profile.ipynb` |
| D-062 | decision | Stage 2 scoring time is the due date minus 10 calendar days; the IBM Disputed flag is used only to generate notes, never as a model input. Input part revised by D-064 | PROPOSED | Claude | `docs/data_contract.md` v1.2, sections 4 and 5 |
| D-063 | decision | Dataset A column roles, quality rules Q1 to Q13 (including dropping 131 invoices due before their invoice date) and the October 1, 2019 time split | APPROVED (owner, Nov 26) | Owner | Owner, Nov 26: answered "Approve" at G1 |
| D-064 | decision | Stage 2 uses the same inputs as Stage 1, with customer history frozen at the invoice date, plus note signals. The notes are the only new information, so any gain over Stage 1 is the notes' contribution | APPROVED (owner, Nov 26) | Owner | Owner, Nov 26 (voice): "same as stage 1 model parameters with additional fields involved from the notes"; "we can consider only the notes for stage two"; `docs/data_contract.md` v1.3 section 4 |
| D-065 | decision | Notes link to customerID (required); invoiceNumber only when the note is about a specific invoice; each note carries a topic (invoice dispute, claim, missing PO, contact change, payment promise, general query) | APPROVED (owner, Nov 26) | Owner | Owner, Nov 26: "should we link the customer ID of the notes and dispute to the records instead of invoice number level?"; contract v1.3 section 6 |
| D-066 | decision | Note mix: every Disputed = Yes invoice gets a dispute thread; of undisputed invoices, 67% get no notes and 33% get a generic note; one in five generic notes reads like a dispute (raised and resolved). The note reader is checked against the topic labels | APPROVED (owner, Nov 26) | Owner | Owner, Nov 26 (voice): "Dispute flag Y means there will be notes generated in sync with that flag"; "let's put it as 33% instead of 25%"; "Yeah, that should be fine" |
| D-067 | decision | Contract section 6 renamed "Notes data rules" and approved as written in v1.3 | APPROVED (owner, Nov 26) | Owner | Owner, Nov 26 (voice): "Yeah, that covers" |
| D-068 | decision | IBM (Dataset B) split by invoice date: train before July 1, 2013 (1,930 invoices, 30.3% late); test from July 1, 2013 (536, 21.5% late, 122 disputed). TimeSeriesSplit used as a stability check | APPROVED (owner, Nov 26) | Owner | Owner, Nov 26 (voice): "I'm okay with that. But I want the notebook with the relevant code from scikit-learn"; `notebooks/03_ibm_split.ipynb` |
| D-069 | observation | In all 5 TimeSeriesSplit folds on IBM, disputed invoices are late 44% to 66% of the time versus 15% to 21% for undisputed ones. Late rate by country code: 391 18%, 897 28%, 770 30%, 406 33%, 818 36% (overall 28.4%) | PROPOSED | Claude | `notebooks/03_ibm_split.ipynb`; `docs/img/ibm_split.png` |
