# Bonus 1 — Churn Risk Scorecard

## Problem Statement

Sales and CS leaders need to know which customer accounts are at risk **before** the
renewal call, not during it. Currently, churn is often discovered reactively — when a
customer says "we're evaluating alternatives" on a call. The signals were there earlier:
in support tickets, negative sentiment trends, billing disputes, and churn signals
embedded in meeting transcripts.

---

## What This Module Does

For each external customer domain, we aggregate signals across **all** their meetings
(customer_support + external call types) and compute a weighted risk score. The result
is a ranked scorecard with three risk tiers.

---

## The Risk Score Formula

```
score = (churn_signal_count × 3)
      + (negative_meeting_count × 2)
      + (open_technical_issues × 1.5)
      + (billing_disputes × 2)
      + (support_escalations × 1)
      − (avg_sentiment × 2)
```

### Weight rationale

| Signal | Weight | Why |
|---|---|---|
| `churn_signal_count` | ×3 | Direct voice-of-customer churn signal. A customer explicitly referencing alternatives, cancellation, or disappointment is the strongest predictor. |
| `billing_disputes` | ×2 | Contractual friction is a near-certain churn precursor. A billing dispute means the relationship is already adversarial. |
| `negative_meeting_count` | ×2 | Sustained negativity (multiple below-3.0 meetings) > one bad call. Pattern matters more than a single data point. |
| `open_technical_issues` | ×1.5 | Unresolved tech problems erode trust incrementally. A customer who has filed 3 bug reports and hasn't seen fixes is quietly angry. |
| `support_escalations` | ×1 | Frequency signal. Multiple support cases = high-maintenance relationship or product quality gap. |
| `avg_sentiment` | ×−2 | Positive sentiment offsets risk. A customer at 4.5 avg with one churn signal is far less at risk than one at 2.1. |

### Risk Tiers

| Tier | Score threshold | Recommended action |
|---|---|---|
| HIGH | > 10 | Executive Business Review required before next renewal. CS + Sales leadership involved. |
| MEDIUM | 5–10 | Account manager check-in within 2 weeks. Review open technical issues. |
| LOW | < 5 | Standard renewal process. Consider for expansion / upsell. |

---

## Actual Results (100-meeting dataset)

**Tier breakdown: 7 HIGH | 4 MEDIUM | 21 LOW**

| Tier | # Accounts | Score Range |
|---|---|---|
| HIGH | 7 | 10.95 – 15.00 |
| MEDIUM | 4 | 5.80 – 9.10 |
| LOW | 21 | −9.60 – 4.60 |

**TOP HIGH-RISK accounts:**

| Domain | Score | Churn Signals | Avg Sentiment | Support Escalations |
|---|---|---|---|---|
| brightpathcommerce.com | 15.00 | 3 | 3.25 | 2 |
| summittrust.com | 14.27 | 3 | 2.87 | 2 |
| ridgelinelogistics.com | 14.23 | 3 | 2.63 | 2 |
| silverlinebrands.com | 12.75 | 2 | 3.38 | 3 |
| northstarpharma.com | 11.30 | 3 | 2.10 | 1 |

**Key observations from the data:**

- **The combination signal is real.** All 7 HIGH-risk accounts have at least 2 churn signals AND at least 1 support escalation — it's never a single factor that pushes a score above 10. This validates the multi-factor weighting design.

- **Compliance-heavy accounts are AegisCloud's most stable customers.** The most negative scores (redwoodclinical.com at −5.0, keystonehealth.com at −7.3, bridgeporthealth.com at −8.2) all belong to healthcare/compliance customers with zero churn signals and avg sentiment above 4.0. The sentiment adjustment factor correctly drives their scores negative — they are not at risk.

- **northstarpharma.com is the highest-risk account with the worst avg sentiment (2.10).** Three churn signals in only 2 meetings is an extreme concentration — every meeting has signalled a problem. This account needs an immediate executive review.

- **Support escalation count alone is a weak predictor.** `forgeindustries.com` has 2 support escalations but scores only 1.30 because avg sentiment is 4.10 and no churn signals are present — they file tickets because they're active users, not because they're leaving.

---

## Implementation Notes

**File:** `transcript_intelligence/churn_risk.py`

**Key functions:**
- `compute_churn_risk(meetings: list[dict]) → dict` — computes all signals + score for one domain
- `build_churn_scorecard(df) → pd.DataFrame` — aggregates across all domains, saves charts

**How domains are identified:**
- From `all_emails` in meeting-info.json: any email not ending in `@aegiscloud.com`
  contributes its domain (e.g. `v.cruz@coastalliving.com` → `coastalliving.com`)
- Internal meetings are excluded (no customer domain)
- One customer may have multiple domains if they use multiple emails (rare)

**Charts generated:**
- `bonus1_churn_scorecard.html` — horizontal bar chart ranked by score, coloured by tier
- `bonus1_churn_scatter.html` — scatter: avg_sentiment vs score, bubble size = meeting count

**Output DataFrame columns:**
`customer_domain, tier, score, churn_signal_count, avg_sentiment, negative_meeting_count,
open_technical_issues, billing_disputes, support_escalations, meeting_count, top_factors`

---

## Iteration Ideas

1. **Time-decay weighting**: recent signals should weight more than signals from 3 months ago.
   A customer who had a bad January but a great March is recovering — don't penalise them equally.

2. **Industry-specific thresholds**: a financial services customer may have 5 support tickets
   and still be healthy; a startup with 2 tickets may be churning. Calibrate thresholds by segment.

3. **Renewal date proximity**: if a HIGH-risk customer renews in 30 days, the urgency is
   critical. Cross-reference the scorecard with renewal dates from CRM.

4. **Comparison to previous period**: "Customer X score went from 6 → 14 in the last month" is
   more actionable than a static score. Momentum matters.

5. **CRM integration**: push HIGH-risk flags directly to Salesforce/HubSpot as account health
   alerts, so the AM sees the warning in their daily workflow without opening a separate tool.
