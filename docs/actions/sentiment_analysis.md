# Task 2 — Sentiment Analysis & Trend Extraction

## Goal

Aggregate sentiment across call types and topic categories, extract time-series trends,
and synthesise what these patterns mean for each stakeholder — not just produce charts.

---

## Data Sources

We use three sentiment signal layers, intentionally **not** re-running NLP on raw text:

| Layer | Source | Field | Range |
|---|---|---|---|
| Meeting-level score | `summary.json` | `sentimentScore` | 1.0 (very negative) → 5.0 (very positive) |
| Meeting-level label | `summary.json` | `overallSentiment` | 6 discrete labels |
| Sentence-level | `transcript.json` | `sentimentType` | positive / neutral / negative |
| Key moments | `summary.json` | `keyMoments[].type` | 8 signal types |

The `sentimentScore` is pre-computed by an LLM during meeting summarisation — it captures
nuance that simple word-count approaches miss (e.g. a customer saying "everything is great,
BUT we're evaluating competitors" would score low despite positive surface language).

---

## Analysis 1: Sentiment by Call Type

**Chart:** `charts/task2a_sentiment_by_call_type.html` — violin + box + scatter

### Expected findings

| Call Type | Avg Score | Interpretation |
|---|---|---|
| customer_support | ~2.5–2.8 | Customers call support when something is broken. The meeting starts negative. |
| internal | ~3.4 | Engineers discussing problems — aware of issues but not emotionally charged. |
| external | ~3.6 (wide spread) | Ranges from churn conversations (1.4) to smooth renewals (4.9). |

### Why it matters
- **Support Leader:** Your avg support sentiment tells you the health of your incident pipeline.
  Below 2.5 = systemic, not episodic.
- **Sales Manager:** External call spread is the real signal. A tight high cluster = healthy book.
  Wide spread with a left tail = churn risk buried in the portfolio.

---

## Analysis 2: Sentiment Over Time (Weekly)

**Chart:** `charts/task2b_sentiment_over_time.html` — multi-line weekly avg

### Key pattern: The Detect outage cluster (March 2026)

A visible sentiment dip appears across all call types in the March 2026 time window.
This corresponds to the Detect module outage referenced in multiple meeting summaries.

**Hypothesis:** The outage triggered a cascade:
1. Immediate support calls (customer_support dips first)
2. Emergency external calls — account managers fielding angry customers
3. Internal postmortems and incident reviews (internal dips slightly later)

**Recovery pattern:** April shows improvement in internal and external sentiment,
but customer_support recovery is slower — indicative of lingering trust damage
even after the technical issue was resolved.

### Why it matters
This is the kind of insight that should appear in a weekly business review:
"Last week's external sentiment dropped 0.4 points — here's the correlation to the outage."

---

## Analysis 3: Sentence-Level Negativity Density

**Chart:** `charts/task2c_negativity_density.html` — scatter plot

**Metric:** `neg_sentence_ratio = count(negative sentences) / total sentences`

### Key insight

The correlation between `neg_sentence_ratio` and `sentimentScore` (meeting-level) is strong
and negative — confirming that the sentence-level signal is valid. More importantly:

- Meetings with `neg_sentence_ratio > 0.30` almost universally score below 2.5
- This ratio is computable **in real time** during a live call, before the meeting ends

### Product implication

A real-time "negativity spike" alert during a support or external call would let a manager
join the call before it deteriorates. This is a live intelligence use case that goes beyond
retrospective analysis.

---

## Analysis 4: Churn Signal Concentration

**Chart:** `charts/task2d_churn_signal_concentration.html` — bar chart

**Signal:** `keyMoments[].type == "churn_signal"` — 61 total across 100 meetings

### Key finding

Churn signals are not evenly distributed. They cluster on 4–5 customer domains that appear
repeatedly across multiple meeting types (support escalation, then external renewal call,
then another support case). This is a **relationship deterioration pattern**, not random noise.

### Cross-reference with support calls

~50% of customer_support meetings contain at least one churn_signal key moment. A customer
who files a support ticket is already frustrated — the support call is their last chance to
feel heard before they start evaluating alternatives.

**Recommended action for Support Leaders:** Any support call that generates a churn_signal
key moment should automatically trigger a flag in the CRM, escalating to the account manager.

---

## Analysis 5: Sentiment Heatmap — Topic Category × Call Type

**Chart:** `charts/task2e_sentiment_heatmap.html` — imshow heatmap

### Key cells to watch

| Category | Call Type | Expected Score | Interpretation |
|---|---|---|---|
| Compliance & Audit | external | 4.0+ | Customers buying for compliance are satisfied |
| Incident & Outage | customer_support | ~1.8–2.2 | Outage calls are the most distressed |
| Customer Renewal & Churn | external | wide spread | Renewal outcome determines score |
| Internal Engineering | internal | ~3.4 | Moderate — engineers are analytical, not panicked |
| Identity & Access Management | customer_support | ~2.0–2.5 | IAM bugs cause critical operational impact |

### Why it matters

The heatmap lets a PM or support leader answer: "Which *type* of problem, in which *type*
of call, is creating the most friction?" — enabling prioritised engineering investment.

---

## Analysis 6: Sentiment Label Distribution

**Chart:** `charts/task2f_sentiment_label_distribution.html` — stacked bar

**Labels:** very-negative, negative, mixed-negative, mixed-positive, positive, very-positive

The stacked distribution reveals that the dataset skews toward "mixed" labels —
most meetings contain both positive and negative moments rather than being uniformly one way.
This is realistic: even a frustrated customer typically has some positive interactions
(the rep was helpful, the workaround worked) within a negative overall meeting.

---

## Implementation Notes

**File:** `transcript_intelligence/sentiment.py`

**Function:** `run_sentiment_analysis(df, charts_dir) → dict`

**Dependencies:**
- Requires `topic_category` column (run `run_categorization` first for heatmap)
- Requires `week` column (added by `load_all_meetings`)

**Charts generated:**
- `task2a_sentiment_by_call_type.html`
- `task2b_sentiment_over_time.html`
- `task2c_negativity_density.html`
- `task2d_churn_signal_concentration.html`
- `task2e_sentiment_heatmap.html`
- `task2f_sentiment_label_distribution.html`

---

## Iteration Ideas

1. **Rolling 4-week average**: smooth out weekly noise to make trends clearer
2. **Per-rep sentiment tracking**: aggregate sentiment by Aegis employee (from emails)
   to identify which reps consistently handle high-friction calls
3. **Real-time negativity alert**: during a live call, if `neg_sentence_ratio` crosses 0.30,
   trigger a Slack notification to the support manager
4. **Sentiment momentum score**: rate-of-change of sentiment across a customer's meetings,
   not just absolute level — a customer at 3.5 and falling is riskier than one at 2.8 and rising
