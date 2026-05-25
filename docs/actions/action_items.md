# Bonus 3 — Action Item Owner Analysis

## Problem Statement

Every meeting generates 3–4 action items. But who actually owns them? And do the
responsible people follow through? Action items that don't generate follow-up activity are
**execution gaps** — commitments made to customers (or internally) that silently disappear.

This analysis answers two questions:
1. **Burden distribution**: which Aegis employees carry the most action item weight?
2. **Follow-through gaps**: which meetings generate action items with no detectable follow-up?

---

## What This Module Does

### Step 1: Parse action item owners

Every `actionItems[]` entry follows the format `"PersonName: task description"`.
We extract the owner with a simple regex: `^([^:]+):`.

Example:
```
"Marcus Williams: Document the call and escalate reliability concerns to CS team"
→ owner: "Marcus Williams"
```

We then count how many action items each person owns across all 100 meetings.

### Step 2: Tag owners as Aegis vs customer

We derive the set of Aegis names from `@aegiscloud.com` emails in each meeting.
Owners who appear in this set are Aegis employees. Others are customer-side commitments.

### Step 3: Detect orphaned meetings

**Definition:** A meeting is "orphaned" if none of its Aegis action-item owners appear
as a participant in a *subsequent* meeting within 7 days that shares at least one
common topic keyword.

**Logic:**
```python
for each owner of an action item in meeting M:
    look for any future meeting within 7 days where:
        - this owner is an Aegis participant
        - the meeting shares ≥1 topic keyword with M
    if found → M has a follow-up
if no owner generates a follow-up → M is orphaned
```

**Why topic overlap matters:** An Aegis employee might have 10 meetings in a week.
We only count a follow-up as relevant if the meeting is *about the same topic*.
This avoids false positives (e.g. a standup that happens to include the same person).

---

## Why This Matters

### For Product Managers
- Which Aegis employees are action-item bottlenecks? If one engineer owns 20% of all
  customer-facing action items and leaves, customer commitments at risk.
- Track whether product action items (feature requests, bug fixes) generate internal
  engineering follow-up — or disappear into the void.

### For Engineering Leads
- A disproportionate action item load on specific engineers signals a resource allocation
  problem. Either redistribute or hire.
- Orphaned internal engineering meetings (sprint planning items with no follow-up
  sprint review in the dataset) expose delivery rhythm gaps.

### For Support Leaders
- Support calls with no follow-up meeting are customer commitments unmet. "We'll escalate
  this to engineering" followed by silence is a churn accelerator.
- Track orphaned support meetings by customer domain — some customers may be systemically
  falling through the cracks.

---

## Actual Results (100-meeting dataset)

### Burden Distribution

**62 unique action item owners** across 100 meetings (≈300–400 total action items).

Top 10 owners:

| Owner | Action Items | Aegis? |
|---|---|---|
| Maria Santos | 31 | ✅ |
| David Kim | 24 | ✅ |
| Sarah Chen | 23 | ✅ |
| Elena Vasquez | 20 | ✅ |
| Kevin O'Brien | 19 | ❌ (customer) |
| Aisha Johnson | 18 | ✅ |
| Priya Patel | 15 | ✅ |
| Marcus Williams | 15 | ✅ |
| Daniel Okafor | 14 | ✅ |
| Lisa Park | 14 | ✅ |

**Maria Santos owns 31 action items — 29% more than the second-highest.** If she leaves, customer commitments across multiple active accounts are at immediate risk. This is a single point of failure in AegisCloud's execution layer.

**Kevin O'Brien (customer-side) is in the top 5.** He owns 19 action items, more than most Aegis employees. This is a signal that customers are being asked to do significant pre-work — worth investigating whether AegisCloud's onboarding or support process is offloading too much burden onto the customer.

### The 76% Orphan Rate — The Most Actionable Finding

**76 of 100 meetings (76%) are orphaned**: none of their Aegis action-item owners appear in a follow-up meeting on the same topic within 7 days.

| Call Type | Orphaned | Total | Orphan Rate |
|---|---|---|---|
| customer_support | 24 | 28 | **86%** |
| external | 31 | 42 | **74%** |
| internal | 21 | 30 | **70%** |

**Customer support is worst at 86%.** "We'll escalate this to engineering" and "I'll send you the advisory by EOD" are the most common action items on support calls — and they have the lowest follow-through rate in the dataset. These are direct commitments made to customers who are already frustrated. When they go unmet, it's not just an execution failure — it's a churn accelerator.

This finding is not about effort or intent. It's about the absence of a structured follow-up cadence. The data suggests that AegisCloud's meeting rhythm does not consistently generate the downstream meetings that would close the loop on customer commitments.

---

## Implementation Notes

**File:** `transcript_intelligence/action_items.py`

**Key functions:**
- `parse_owner(action_item) → str` — regex extraction of owner name
- `run_action_item_analysis(df) → df` — full analysis + charts

**Columns added to DataFrame:**
- `has_followup`: bool — True if a topic-linked follow-up meeting was found within 7 days
- `action_item_owners`: comma-separated string of parsed owners for the meeting

**Configuration constants:**
- `FOLLOW_UP_WINDOW_DAYS = 7` — window for follow-up detection (adjustable)

**Charts generated:**
- `bonus3_action_item_owners.html` — top 15 owners (Aegis vs customer), horizontal bar
- `bonus3_followup_rate.html` — orphaned vs followed-up meetings stacked bar by call type
- `bonus3_aegis_burden.html` — Aegis-only top owners, burden concentration chart

---

## Iteration Ideas

1. **Action item lifecycle tracking**: beyond "was there a follow-up meeting?", look for
   the *specific* action item being addressed. If the action item is "send patch advisory"
   and the next meeting with that customer doesn't mention the advisory → still orphaned.

2. **Owner workload dashboard**: a running table of every Aegis employee's open action items
   (across all meetings, sorted by date assigned) — a lightweight project management view
   built entirely from meeting data.

3. **Customer-side action items**: parse action items where the owner is a customer name.
   Did the customer do their homework? If a customer was asked to "send their compliance
   framework requirements" and the next meeting doesn't reference them — the ball is in
   their court, not ours.

4. **Action item aging**: track how many days pass between when an action item is assigned
   and when the relevant follow-up meeting happens. Chronic lag on specific action types
   (e.g. "engineering will fix") is a product execution signal.

5. **Meeting-type follow-up chains**: visualise the directed graph of meetings — "support
   call A generated action item → led to internal standup B → led to external update call C".
   This reveals whether the escalation-to-resolution pipeline is functioning.
