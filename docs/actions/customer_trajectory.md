# Bonus 4 — Customer Sentiment Trajectory

## Problem Statement

A single sentiment score tells you how one meeting went. A **trajectory** tells you
where a customer relationship is heading. The difference is the difference between
a snapshot and a story.

A customer at 3.5 sentiment who has been at 4.8, 4.2, 3.9, 3.5 is in freefall.
A customer at 3.5 who has been at 2.1, 2.8, 3.2, 3.5 is recovering and building trust.
The same score means opposite things.

This analysis builds per-customer sentiment timelines for all customers with 3+ meetings
and classifies each relationship as **improving**, **stable**, or **declining**.

---

## What This Module Does

### Step 1: Build per-customer timelines

We flatten the DataFrame: for each external-touching meeting (customer_support + external),
we create one row per customer domain present. This gives us a time-ordered series of
sentiment scores per customer.

Internal meetings are excluded — they don't reflect customer health directly.

### Step 2: Filter for statistical reliability

Only customers with `>= 3 meetings` are included in trajectory analysis.
A customer with 1–2 meetings doesn't have enough data points to establish a trend.
The threshold is configurable via `MIN_MEETINGS`.

### Step 3: Classify trend direction

We split each customer's timeline into first half and second half:
```
first_half_avg = avg sentiment of meetings 1..n//2
second_half_avg = avg sentiment of meetings n//2..n
delta = second_half_avg - first_half_avg

improving  if delta > +0.3
declining  if delta < -0.3
stable     otherwise (within ±0.3)
```

The 0.3 threshold (`TREND_DELTA`) is a design choice: it's large enough to filter
noise but small enough to catch meaningful directional shifts.

---

## Why This Matters

### For Sales / Account Managers

**Declining accounts** are early warning signals — especially those whose trajectory
is crossing the 3.0 neutral line downward. These customers haven't said "we're leaving"
yet, but the data shows the relationship is deteriorating. A proactive executive business
review here can change the outcome.

**Improving accounts** that started rough (onboarding friction, early bugs) and are now
trending positive are ideal **expansion targets**. They've survived a rough patch, trust
is building, and they're primed for an upsell conversation on additional AegisCloud modules.

### For Support Leaders

A customer whose support call sentiment is declining over multiple interactions signals
that your support team is not resolving the underlying issue — only firefighting each
individual incident. The trajectory reveals the pattern that individual call scores hide.

### For Product Managers

If multiple customers are declining on the same topic category (e.g. Infrastructure &
Reliability), that's a product problem — not a sales or support problem. Trajectory
analysis by topic category reveals where the product is losing trust.

---

## Key Findings (expected from dataset)

- **Improving accounts** are most likely to be onboarding customers who had initial
  friction (integration issues, configuration complexity) but are now stable and satisfied.
  These are AegisCloud's success stories.

- **Declining accounts** often have the Detect outage visible as a turning point in their
  timeline — their sentiment dropped in March and hasn't recovered by April. These are
  the accounts most at risk of using the outage as justification for a competitive evaluation.

- **Stable accounts** at high sentiment (3.8–4.5) are the core of AegisCloud's retained
  customer base — compliance-heavy, low-maintenance, good renewal prospects.

- **Stable accounts at low sentiment** (consistently below 3.0) are the most dangerous.
  They're not improving, they're not escalating — they're quietly preparing to leave.

---

## Charts

| Chart | File | Description |
|---|---|---|
| Timeline | `bonus4_customer_trajectory.html` | Multi-line chart: one line per customer, x=date, y=sentiment |
| Trend summary | `bonus4_trend_summary.html` | Horizontal bar: avg sentiment + trend colour per customer |
| Monthly heatmap | `bonus4_monthly_heatmap.html` | Customer × Month heatmap of avg sentiment |

All charts are interactive Plotly HTML — hover to see meeting title, call type,
churn signal count.

---

## Implementation Notes

**File:** `transcript_intelligence/customer_trajectory.py`

**Key functions:**
- `_classify_trend(first_half, second_half) → str` — trend label logic
- `run_customer_trajectory(df) → pd.DataFrame` — full analysis + charts

**Configuration constants:**
- `MIN_MEETINGS = 3` — minimum meetings for trajectory inclusion
- `TREND_DELTA = 0.3` — threshold for classifying trend direction (on a 1–5 scale)

**Output DataFrame:** `trends_df` with columns:
`domain, meeting_count, avg_sentiment, first_half_avg, second_half_avg, trend,
total_churn_signals, date_range`

---

## Combining with Churn Scorecard

The trajectory and churn scorecard are most powerful together:

| Scenario | Trajectory | Churn Score | Interpretation |
|---|---|---|---|
| 🔴 Immediate risk | declining | HIGH | Executive escalation needed this week |
| 🟠 Watch closely | declining | MEDIUM | AM check-in within 2 weeks |
| 🟡 Recovering | improving | HIGH | Risk is dropping — continue nurturing |
| 🟢 Strong | improving | LOW | Expansion opportunity |
| ⚪ Stable risk | stable | HIGH | Static — might need a new engagement strategy |
| 🟢 Retained | stable | LOW | Core customer — protect and refer |

---

## Iteration Ideas

1. **Granular timeline**: weekly instead of meeting-by-meeting — smooth curves for
   customers with irregular meeting cadences.

2. **Topic-filtered trajectory**: "How is this customer trending specifically on Compliance
   topics?" — isolate one concern area rather than aggregate all meetings.

3. **Predicted future score**: fit a simple linear regression to each customer's timeline
   and project 30/60/90 day sentiment. Flag customers projected to cross 3.0 downward
   before their renewal date.

4. **Cohort analysis**: group customers by onboarding date, industry, or AegisCloud module.
   Which cohorts have the best trajectory patterns? What do the declining cohorts have in common?

5. **Competitive signal detection**: scan `summary` text for competitor mentions in declining
   accounts. A declining customer who mentions "we're looking at CrowdStrike" is at terminal
   risk — flag differently from one who just had a rough quarter.
