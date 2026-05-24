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

## Key Findings (expected from dataset)

- **A small number of Aegis employees own a disproportionate share of action items.**
  The Pareto principle likely applies: ~20% of people own ~80% of action items.
  These are AegisCloud's execution backbone — and a single point of failure risk.

- **Customer support calls have the highest orphan rate.** Short, reactive calls generate
  action items ("escalate to engineering", "send advisory by EOD") that may not have a
  formal follow-up cadence in the calendar. These commitments fall through most often.

- **Internal engineering meetings have an interesting pattern**: they generate many action
  items internally but rarely generate external customer communication as a visible follow-up.
  This is the gap between "we know about it" and "we told the customer".

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
