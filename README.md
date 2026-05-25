# Transcript Intelligence — AegisCloud

## Problem Statement - Transcript Intelligence

### Background

You're joining a team at a B2B enterprise SaaS company. The company captures call transcripts from across the organization:

- **Customer Support Calls:** Customers reaching out with operational or system issues.
- **External Calls:** Account managers speaking with clients regarding renewals, platform adoption, and feedback.
- **Internal Calls:** Engineering syncs, cross-team escalations, and product planning discussions.

The team is building a product called **Transcript Intelligence** — a tool designed to help diverse internal stakeholders (Support Leaders, Sales Managers, Product Managers, Engineering Leads) make better, data-driven decisions using these transcripts. 

### Input

You will receive approximately 100 sample transcripts across these three call types as your starting dataset. Your job is to explore the dataset, extract meaningful insights, and demonstrate your analytical and engineering approach.

### Deliverables & Core Tasks

#### 1. Topic Modeling & Classification Pipeline

Build a pipeline that processes raw transcripts and categorizes them by topic or structural theme.

- **Requirements:** * Exhibit the final categories identified within the dataset.
  - Explain and justify your architectural approach (e.g., LLM-based zero-shot/few-shot classification, unsupervised clustering like K-Means/LDA, rule-based, or a hybrid mechanism).
  - Provide concrete examples of transcripts mapping to each identified category.
- **Focus:** Value your underlying engineering reasoning, trade-off analysis, and processing logic over just the raw output.

#### 2. Sentiment Analysis & Trend Extraction

Generate a structured sentiment analysis across the different call types and identify operational trends.

- **Requirements:**
  - Do not just produce static visualizations or raw scores — synthesize what these trends indicate.
  - If anomalies, spikes, or patterns stand out (e.g., low sentiment in specific internal calls vs. high satisfaction in renewal calls), provide a clear hypothesis on what they indicate and why a business stakeholder should care.

#### 3. Advanced Insight Generation (Open-Ended)

Explore beyond standard classification and sentiment. Think about the unique persona-based needs of different organizational stakeholders who would interact with a Transcript Intelligence tool.

- **Requirements:**
  - Brainstorm and document **at least 2–3 additional insight ideas** that add non-obvious value to the business.
  - *Options:* You can choose to fully implement functional prototypes of these insights, or simply describe them thoroughly alongside a strong product/technical justification for why they matter.

---

## Solution

End-to-end meeting transcript analytics pipeline for AegisCloud's 100-meeting dataset.
Surfaces insights for four stakeholder personas: Support Leaders, Sales/Account Managers,
Product Managers, and Engineering Leads.

---

## Dataset

**100 meetings** across Feb–Apr 2026, each stored as a ULID-named directory under `dataset/`.
Every meeting contains exactly 6 JSON files:


| File                | What it holds                                                                                |
| ------------------- | -------------------------------------------------------------------------------------------- |
| `meeting-info.json` | Meeting Id, Title, organizer Email, participant emails, start/end time, duration, invitees   |
| `summary.json`      | LLM-generated summary, action items, topic tags, sentiment score (1–5), key moments          |
| `transcript.json`   | Full conversation sentence-by-sentence with speaker, timestamp, and sentence-level sentiment |
| `speakers.json`     | Speaker turn timestamps — used to compute who talked how much                                |
| `events.json`       | Join/leave events per participant — used to detect late joiners or early leavers             |
| `speaker-meta.json` | Maps speaker ID integers to names                                                            |


**Key fields used in analysis:**

- `sentimentScore` (1.0–5.0) and `overallSentiment` label — from `summary.json`, LLM-generated, treated as ground truth
- `keyMoments[].type` — one of: `churn_signal`, `concern`, `technical_issue`, `feature_gap`, `positive_pivot`, `praise`, `pricing_offer`, `action_item`
- `topics[]` — free-text tags (351 unique values across all meetings), mapped to 8 canonical categories
- `actionItems[]` — always 3–4 per meeting, format `"PersonName: task description"`
- `allEmails` — used to classify call type (internal vs external vs support)

**Call type distribution:**


| Call Type          | Count | Description                                                                        |
| ------------------ | ----- | ---------------------------------------------------------------------------------- |
| `external`         | 42    | Account manager + customer stakeholders — renewals, onboarding, compliance reviews |
| `internal`         | 30    | All `@aegiscloud.com` — standups, planning, postmortems, roadmap syncs             |
| `customer_support` | 28    | Aegis rep + customer — operational issues, escalations                             |


---

## Build Plan

[See Architecture Plan](https://github.com/nits2010/Transcript-Intelligence/blob/main/docs/build_plan/build_plan.md)

---

## Project Structure

```
├── src/
│   └── transcript_intelligence/    # Python package
│       ├── __init__.py
│       ├── __main__.py             # python -m transcript_intelligence
│       ├── ingest.py               # Data loading + call type classification
│       ├── categorize.py           # Task 1: topic taxonomy (8 categories)
│       ├── sentiment.py            # Task 2: 6 sentiment analyses
│       ├── churn_risk.py           # Bonus 1: customer churn risk scorecard
│       ├── talk_time.py            # Bonus 2: Aegis vs customer talk ratio
│       ├── action_items.py         # Bonus 3: action item burden + orphan detection
│       ├── customer_trajectory.py  # Bonus 4: per-customer sentiment trend
│       └── pipeline.py             # Orchestrates all modules
├── notebooks/
│   └── pipeline.ipynb              # Narrative Jupyter notebook 
├── docs/
│   ├── topic_categorization.md
│   ├── sentiment_analysis.md
│   ├── churn_risk.md
│   ├── talk_time.md
│   ├── action_items.md
│   └── customer_trajectory.md
├── dataset/                        # Raw meeting data (100 ULID directories)
├── output/
│   └── charts/                     # Generated Plotly HTML charts (gitignored)
├── run_pipeline.py                 # Root entry point (no install needed)
├── pyproject.toml
└── requirements.txt
```

---

## Architecture & Design Decisions

### Overall Approach

The pipeline is deliberately **analytics-first, not ML-first**. The dataset already contains LLM-generated signals (`sentimentScore`, `keyMoments`, `overallSentiment`) of high quality. Re-running NLP or training models on top of this would add complexity without meaningful accuracy gain. The engineering effort was directed at aggregation, cross-signal correlation, and surfacing actionable patterns — not generating new signals from raw text.

---

### Decision 1 — Topic Categorization: Keyword Taxonomy over Embeddings / LDA

**Chosen:** Hand-crafted keyword taxonomy mapping 351 noisy raw topic tags into 8 canonical categories.

**Alternatives considered:**


| Approach                      | Why rejected                                                                                  |
| ----------------------------- | --------------------------------------------------------------------------------------------- |
| LDA / topic modeling          | Unsupervised — produces opaque clusters that shift with random seed. Hard to explain to a VP. |
| Sentence embeddings + K-Means | Requires embedding model, GPU or API call, non-deterministic clusters, no business label.     |
| LLM zero-shot classification  | Adds latency and API cost per meeting; overkill when topics are already semi-structured tags. |


**Trade-off accepted:** A keyword taxonomy can misclassify meetings whose topics are rare or ambiguous. Mitigated with a summary-text fallback scan and a secondary category field. Coverage is auditable — adding a keyword extends it without retraining.

---

### Decision 2 — Sentiment: Trust the LLM Output, Don't Re-Score

**Chosen:** Use `sentimentScore` (1–5) and `overallSentiment` from `summary.json` as ground truth.

The dataset was generated by an LLM that read full transcripts. Running VADER or a BERT model on individual sentences to re-derive a meeting-level score would be noisier and ignore context. Sentence-level `sentimentType` from `transcript.json` is used only for the negativity-density metric (fraction of negative sentences per meeting), which adds a second signal layer rather than replacing the first.

**Trade-off accepted:** We have no validation set to audit the LLM scores. Accepted because the problem statement explicitly treats these as input data, not model outputs to improve.

---

### Decision 3 — Bonus Insights: Chosen for Stakeholder Coverage

We implemented 4, each targeting a different persona:


| Bonus                | Insight                                                                                 | Primary Stakeholder     |
| -------------------- | --------------------------------------------------------------------------------------- | ----------------------- |
| Churn Risk Scorecard | Weighted risk score per customer domain from signals across all their meetings          | Sales / CS Leader       |
| Talk Time Ratio      | Aegis vs customer talk share per meeting; flags over-talking reps                       | Support Leader          |
| Action Item Burden   | Who owns the most follow-up work; which meetings generate orphaned action items         | PM / Engineering Lead   |
| Customer Trajectory  | Per-customer sentiment trend (improving / stable / declining) across the 3-month window | Sales / Account Manager |


Talk Time and Customer Trajectory were chosen over alternatives (e.g., late-joiner analysis, ASR confidence heatmaps) because they surface **behavioral and relationship signals** that are invisible in raw sentiment scores — exactly the "non-obvious value" the problem statement asks for.

---

### Decision 4 — Scale: What Changes Beyond 100 Meetings

The current pipeline loads all meetings into a single in-memory DataFrame. This is appropriate for a 100-meeting analytics assignment (completes in ~10 seconds) and keeps the design simple and auditable. At production scale (100k+ meetings) the following changes would be required:

| Layer | Current | At Scale |
|---|---|---|
| Ingestion | Sequential `for dir in path.iterdir()` | Parallel reads via `ThreadPoolExecutor`, or streaming from object storage (S3/GCS) |
| Storage | In-memory DataFrame | Database backing store (Postgres / DuckDB / BigQuery) — incremental runs process only new meetings |
| Churn scorecard | Full-table scan on each run | Pre-compute domain summaries incrementally as meetings arrive; materialise as a table |
| Config | YAML file, `reload()` for hot-swap | Already supports `load_url()` — point at a remote config endpoint for fleet-wide updates without redeploy |

The design patterns (Template Method, Strategy, Chain of Responsibility) are scale-agnostic — they govern how each analysis step is structured internally, not how data flows through the system.

---

### Decision 6 — Output Format: Interactive HTML over Static Images

**Chosen:** Plotly HTML charts saved to `output/charts/`.

Static PNGs require a render pipeline and lose hover/drill-down. Interactive HTML opens in any browser with no server, making the output shareable as a file drop. For a leadership presentation this is strictly better — stakeholders can hover over a specific customer's bar to see their score components without running code.

**Trade-off accepted:** HTML files are larger than PNGs but HTLM provides interactive behaviour vs static. 

---

## Quick Setup Guilde

### Setup (virtual environment recommended)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Option A — Run directly (no install required)

```bash
python run_pipeline.py
```

### Option B — Install as editable package (enables CLI command)

```bash
pip install -e .
transcript-intelligence
```

### Option C — Jupyter notebook (recommended for presentation)

```bash
cd notebooks
jupyter notebook pipeline.ipynb
```

---

## Output

All charts are saved as interactive Plotly HTML to `output/charts/`.
Open any `.html` file directly in a browser — no server required.


| Chart file                                 | Analysis                                                    |
| ------------------------------------------ | ----------------------------------------------------------- |
| `task1_topic_categories.html`              | Meeting count per topic category, coloured by avg sentiment |
| `task2a_sentiment_by_call_type.html`       | Violin: sentiment distribution by call type                 |
| `task2b_sentiment_over_time.html`          | Weekly trend lines — Detect outage dip visible in March     |
| `task2c_negativity_density.html`           | Scatter: meeting sentiment vs sentence negativity ratio     |
| `task2d_churn_signal_concentration.html`   | Customer domains with most churn signals                    |
| `task2e_sentiment_heatmap.html`            | Heatmap: topic category × call type avg sentiment           |
| `task2f_sentiment_label_distribution.html` | Stacked bar: sentiment labels by call type                  |
| `bonus1_churn_scorecard.html`              | Customer churn risk ranked by score, coloured by tier       |
| `bonus1_churn_scatter.html`                | Risk score vs avg sentiment scatter                         |
| `bonus2_talk_ratio_by_type.html`           | Avg Aegis talk ratio by call type with thresholds           |
| `bonus2_talk_ratio_vs_sentiment.html`      | Talk ratio vs sentiment, flagged outliers                   |
| `bonus3_action_item_owners.html`           | Top 15 action item owners (Aegis vs customer)               |
| `bonus3_followup_rate.html`                | Orphaned vs followed-up meetings by call type               |
| `bonus3_aegis_burden.html`                 | Aegis employee action item burden                           |
| `bonus4_customer_trajectory.html`          | Per-customer sentiment timeline                             |
| `bonus4_trend_summary.html`                | Customer avg sentiment + trend direction                    |
| `bonus4_monthly_heatmap.html`              | Customer × month sentiment heatmap                          |


---

## Analyses


| Module                   | Task                           | Doc                                                                      |
| ------------------------ | ------------------------------ | ------------------------------------------------------------------------ |
| `categorize.py`          | Task 1 — Topic Categorization  | [docs/actions/topic_categorization.md](docs/actions/topic_categorization.md) |
| `sentiment.py`           | Task 2 — Sentiment Analysis    | [docs/actions/sentiment_analysis.md](docs/actions/sentiment_analysis.md)     |
| `churn_risk.py`          | Bonus 1 — Churn Risk Scorecard | [docs/actions/churn_risk.md](docs/actions/churn_risk.md)                     |
| `talk_time.py`           | Bonus 2 — Talk Time Analysis   | [docs/actions/talk_time.md](docs/actions/talk_time.md)                       |
| `action_items.py`        | Bonus 3 — Action Item Owners   | [docs/actions/action_items.md](docs/actions/action_items.md)                 |
| `customer_trajectory.py` | Bonus 4 — Customer Trajectory  | [docs/actions/customer_trajectory.md](docs/actions/customer_trajectory.md)   |


