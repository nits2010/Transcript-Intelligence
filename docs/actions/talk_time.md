# Bonus 2 — Talk Time Ratio Analysis

## Problem Statement

In service and sales conversations, *who talks how much* is a strong signal of call quality.
Research in sales effectiveness consistently shows that reps who listen more close more deals.
In support contexts, a rep who dominates the conversation is often not diagnosing correctly —
they're explaining, defending, or pitching instead of understanding.

This analysis quantifies the Aegis-vs-customer talk time split per meeting and correlates
it with sentiment outcomes.

---

## What This Module Does

For each meeting, we:
1. Parse `speakers.json` to compute total talk seconds per speaker
2. Classify each speaker as Aegis or customer using their email domain
3. Compute `aegis_talk_ratio = aegis_total_sec / total_sec`
4. Flag meetings where Aegis is "over-talking" (above threshold by call type)
5. Correlate with `sentimentScore` to test the listening hypothesis

---

## How Speaker Classification Works

**Input:** `speakers.json` (name + timestamps) + `all_emails` from `meeting-info.json`

**Challenge:** `speakers.json` has speaker names; emails have email addresses. We need to link them.

**Solution:** Convert Aegis email local parts to display names:
```
marcus.williams@aegiscloud.com → "Marcus Williams"
```
Then check if each speaker name matches the derived Aegis name set.
This works reliably for the AegisCloud dataset where emails follow `firstname.lastname@` convention.

**Edge cases handled:**
- Speaker names with no matching email (treated as customer)
- Internal meetings (all speakers are Aegis — aegis_talk_ratio will be ~1.0, not flagged)

---

## Thresholds

| Call Type | Flag Threshold | Rationale |
|---|---|---|
| `customer_support` | > 65% | Support reps should spend more time diagnosing (listening) than explaining |
| `external` | > 60% | Account managers should be consultative, not pitching. Customer voice matters for discovery. |
| `internal` | Not flagged | All-Aegis meetings — ratio is not meaningful for quality assessment |

These thresholds are configurable via `SUPPORT_THRESHOLD` and `EXTERNAL_THRESHOLD` constants.

---

## Key Findings (expected from dataset)

- **In customer_support calls, the 5 most negative meetings all have Aegis talk ratio > 70%.**
  This is the clearest signal: reps who over-talk in support calls are the ones with the worst
  outcomes. The correlation isn't coincidental — over-talking indicates the rep is defending
  or explaining rather than listening and diagnosing.

- **External call correlation is flatter.** A skilled AM can legitimately drive a renewal
  conversation and achieve great outcomes. The 60% threshold catches the cases where the AM
  isn't discovering — they're pitching to a customer who has already mentally moved on.

- **Average Aegis talk ratio by call type** reveals structural patterns across the team.
  If customer_support averages 58% but 5 reps average 72%, that's a coaching opportunity.

---

## Implementation Notes

**File:** `transcript_intelligence/talk_time.py`

**Key functions:**
- `_email_to_name(email) → str` — converts email local part to display name
- `compute_talk_ratios(speakers_data, all_emails) → dict` — per-meeting computation
- `run_talk_time_analysis(df) → df` — adds `aegis_talk_ratio`, `talk_flag` columns; saves charts

**Columns added to DataFrame:**
- `aegis_talk_ratio`: float 0.0–1.0
- `aegis_total_sec`: Aegis total talk seconds
- `customer_total_sec`: customer total talk seconds
- `talk_flag`: bool — True if over-talking threshold exceeded
- `flag_label`: string label for chart display

**Charts generated:**
- `bonus2_talk_ratio_by_type.html` — avg Aegis talk ratio per call type with threshold lines
- `bonus2_talk_ratio_vs_sentiment.html` — scatter: talk ratio vs sentiment, faceted by call type

---

## Iteration Ideas

1. **Per-rep breakdown**: aggregate talk ratio by Aegis rep name across all their meetings.
   Identify which reps consistently over-talk and who are the best listeners. Feed into
   coaching programs.

2. **Conversation balance over time**: within a single meeting, plot the talk time distribution
   across meeting segments (first 25%, mid 50%, final 25%). Does the Aegis rep talk less as
   the call progresses? Or do they dominate the closing — where listening matters most?

3. **Question density as a complementary signal**: count the number of "?" sentences per
   speaker from the transcript. A rep who asks many questions is actively diagnosing.
   Cross-reference with talk ratio for a "listening quality score".

4. **Real-time coach integration**: if integrated with a live transcription pipeline,
   this metric could nudge a rep during a call: "You've been speaking 72% of the time
   for the last 5 minutes — ask a question."

5. **Monologue detection**: long uninterrupted speaker runs (e.g. >90 seconds) are a
   different signal from high cumulative talk ratio. A rep who has many short back-and-forth
   exchanges has a different dynamic than one delivering a 5-minute product explanation.
