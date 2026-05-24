# Transcript Intelligence — Master Build Prompt
# Use this as your full context input to Claude CLI

---

## WHO YOU ARE / WHAT YOU ARE BUILDING

You are building a **Transcript Intelligence pipeline** for AegisCloud — a B2B SaaS company
selling a security and compliance platform (modules: Detect, Comply, Identity, LogVault).
The pipeline processes 100 meeting transcripts and extracts insights for four stakeholder personas:
Support Leaders, Sales/Account Managers, Product Managers, and Engineering Leads.

Deliverables:
1. A Python pipeline (Jupyter notebook or clean scripts) that ingests all 100 meetings
2. Task 1: Topic categorization with explained methodology
3. Task 2: Sentiment analysis across call types with trend interpretation
4. Task 3: 2–3 bonus insights (implement or describe with reasoning)

---

## THE DATASET

### Location
`./dataset/` — 100 subdirectories, each named with a ULID (e.g., `01KQ5EC1665DCFD7A6B62A59`).
Each directory = one meeting. Each meeting has exactly 6 JSON files.

### File 1: `meeting-info.json`
Meeting metadata. Schema:
```json
{
  "meetingId": "01KQ5EC1665DCFD7A6B62A59",
  "title": "Support Case #8749 - Coastal Living Co SAML Certificate Rotation Bug",
  "organizerEmail": "marcus.williams@aegiscloud.com",
  "host": "marcus.williams@aegiscloud.com",
  "startTime": "2026-03-29T15:15:00.000Z",
  "endTime": "2026-03-29T15:25:06.000Z",
  "duration": 10.1,
  "allEmails": ["marcus.williams@aegiscloud.com", "v.cruz@coastalliving.com"],
  "invitees": ["marcus.williams@aegiscloud.com", "v.cruz@coastalliving.com"]
}
```
Key fields: `title` (used for call type classification), `allEmails` (internal vs external),
`startTime` (for time-series trending), `duration` (in minutes).

### File 2: `summary.json`
LLM-generated meeting summary. **This is the richest signal file.** Schema:
```json
{
  "meetingId": "01KQ5EC1665DCFD7A6B62A59",
  "summary": "Full text summary of the meeting...",
  "actionItems": [
    "Marcus Williams: Draft updated customer communication within the hour",
    "Raj Kapoor: Send evening status update once rollout completes"
  ],
  "topics": ["outage remediation", "incident response", "customer communication"],
  "overallSentiment": "mixed-negative",
  "sentimentScore": 2.4,
  "keyMoments": [
    {
      "time": 95.0,
      "text": "Brian reveals 112 open support tickets tied to the outage",
      "type": "churn_signal",
      "speaker": "Brian Cho"
    }
  ]
}
```

**sentimentScore**: 1.0 (very negative) to 5.0 (very positive). Avg across 100 meetings = 3.42.
**overallSentiment**: One of: `very-negative`, `negative`, `mixed-negative`, `mixed-positive`, `positive`, `very-positive`
**topics**: Array of free-text tags — 351 unique values across all meetings (noisy, needs clustering)
**keyMoments.type**: One of: `concern`, `positive_pivot`, `churn_signal`, `technical_issue`, `feature_gap`, `action_item`, `praise`, `pricing_offer`
**actionItems**: Always 3–4 per meeting. Format: "PersonName: task description"

### File 3: `transcript.json`
Full conversation, sentence by sentence. Schema:
```json
{
  "data": [
    {
      "index": 0,
      "sentence": "Hi Sandra, thanks for making time this afternoon.",
      "speaker_name": "Rachel Torres",
      "speaker_id": 0,
      "sentimentType": "neutral",
      "time": 3.7,
      "endTime": 10.4,
      "averageConfidence": 0.97
    }
  ]
}
```
4,313 total sentences across 100 meetings. `sentimentType`: `positive`, `neutral`, or `negative`.
`averageConfidence`: ASR confidence 0.0–1.0. `time`/`endTime`: seconds from meeting start.

### File 4: `speakers.json`
Speaker turn-level timestamps. Used to compute talk-time ratios. Schema:
```json
[
  { "speakerName": "Marcus Williams", "timestamp": 7.1, "endTimeTs": 22.0 },
  { "speakerName": "Elena Vasquez",   "timestamp": 22.9, "endTimeTs": 27.0 }
]
```
Talk time for speaker = sum of (endTimeTs - timestamp) across all their turns.

### File 5: `events.json`
Join/Leave events for each participant. Used to detect late joiners and early leavers. Schema:
```json
[
  { "participantName": "David Kim", "timestamp": 1771673423000, "type": "Join", "time": 23.0 },
  { "participantName": "David Kim", "timestamp": 1771675232000, "type": "Leave", "time": 1823.0 }
]
```
`time` = seconds from meeting start. `timestamp` = Unix epoch ms. The first Join time for
a participant tells you how late they joined. If someone leaves before the last sentence
time, they left early.

### File 6: `speaker-meta.json`
Maps `speaker_id` (integer) → speaker name. Used to link transcript `speaker_id` to names.
```json
{ "0": "David Kim", "1": "Kendra Wallace" }
```

---

## CALL TYPE CLASSIFICATION

There are exactly 3 call types. Classify each meeting from `meeting-info.json` using this logic:

```python
def classify_call_type(title: str, all_emails: list[str]) -> str:
    title_l = title.lower()
    external_emails = [e for e in all_emails if not e.endswith('@aegiscloud.com')]
    
    if 'support case' in title_l or title_l.startswith('escalation'):
        return 'customer_support'
    elif not external_emails:
        return 'internal'
    else:
        return 'external'
```

**Distribution across 100 meetings:**
- `customer_support`: 28 meetings — short (~15 min avg), 2 participants, Aegis rep + frustrated customer
- `internal`: 30 meetings — all @aegiscloud.com, standups/planning/postmortems/roadmap
- `external`: 42 meetings — Aegis AMs + customer stakeholders, renewals/onboarding/compliance

**Aegis internal domain**: `@aegiscloud.com`
**Customer domains** (33 companies): atlasprecision.com, axiomlabs.dev, blackridgeinvest.com,
bridgeporthealth.com, brightpathcommerce.com, clearwatermed.com, coastalliving.com,
cobaltsoftware.com, crestlinewealth.com, forgeindustries.com, frostbyte.ai, harborviewbank.com,
helixdata.io, ironcladfinancial.com, ironworkscorp.com, keystonehealth.com, maplewoodgoods.com,
meridiancapital.com, nimbusplatform.com, northstarpharma.com, novaretail.com, pineridge.io,
pinnacleins.com, quantumedge.com, redwoodclinical.com, ridgelinelogistics.com,
silverlinebrands.com, steelpointmfg.com, stratoscloud.io, summittrust.com, trailheadmkt.com,
vantahealth.com

---

## DATASET STATISTICS (know these before building)

- **Date range**: 2026-02-03 to 2026-04-28 (roughly 3 months)
- **Avg meeting duration**: 30.3 min (support ~15 min, external/internal ~30–40 min)
- **Sentences per meeting**: avg ~43 (range ~20–80)
- **Action items per meeting**: always 3–4
- **Key moments per meeting**: always 4–5

**Sentiment distribution (meeting-level):**
| Label | Count |
|-------|-------|
| mixed-negative | 33 |
| mixed-positive | 33 |
| very-positive  | 21 |
| positive       | 7  |
| negative       | 4  |
| very-negative  | 2  |

**Key moment type distribution (across all meetings):**
| Type | Count |
|------|-------|
| concern | 84 |
| positive_pivot | 76 |
| churn_signal | 61 |
| technical_issue | 54 |
| feature_gap | 51 |
| action_item | 43 |
| praise | 23 |
| pricing_offer | 10 |

**Sentence-level sentiment (4,313 total sentences):**
- neutral: 2,428
- positive: 1,163
- negative: 722

**Top raw topics (from summary.json topics[] — 351 unique values):**
compliance (23), compliance reporting (19), renewal (17), churn risk (14), onboarding (9),
outage (8), incident response (8), incident communication (7), product launch (7),
platform outage (6), feature request (6), sprint planning (5), multi-framework support (5),
product roadmap (5), identity management (5), outage post-mortem (5), service outage (5),
pricing (5), roadmap planning (4), infrastructure reliability (4), billing dispute (4),
support response time (4), product bug (4), incident review (4), pci dss (4), workaround (4)

---

## TASK 1: TOPIC CATEGORIZATION

### Goal
Map 351 noisy raw topic tags into 8–10 meaningful canonical categories.
Show which meetings fall into each category, give examples, explain your methodology.

### Recommended Approach: Keyword Taxonomy (fast, explainable, auditable)
Build a mapping dict from canonical category → list of keyword patterns.
Each meeting gets assigned to the category whose keywords match most of its raw topics.
If no match or ambiguous → use summary text for LLM fallback.

### Suggested Canonical Categories (8 total)
```python
TOPIC_TAXONOMY = {
    "Compliance & Audit": [
        "compliance", "compliance reporting", "audit", "soc 2", "hipaa",
        "pci dss", "iso 27001", "gdpr", "cmmc", "multi-framework", "regulatory"
    ],
    "Incident & Outage": [
        "outage", "incident", "escalation", "remediation", "postmortem",
        "post-mortem", "platform outage", "service outage", "detect outage",
        "pipeline failure", "circuit breaker"
    ],
    "Customer Renewal & Churn": [
        "renewal", "churn", "retention", "contract", "billing", "pricing",
        "sla", "service credits", "overage", "billing dispute"
    ],
    "Product & Feature": [
        "feature request", "feature gap", "product roadmap", "product launch",
        "product feedback", "roadmap planning", "product demo", "early access",
        "product bug", "workaround"
    ],
    "Identity & Access Management": [
        "identity", "sso", "saml", "scim", "mfa", "okta", "ldap", "rbac",
        "provisioning", "access control", "deprovisioning"
    ],
    "Infrastructure & Reliability": [
        "infrastructure", "reliability", "kafka", "pipeline", "backup",
        "disaster recovery", "architecture", "performance", "load testing",
        "circuit breaker", "ingestion"
    ],
    "Onboarding & Deployment": [
        "onboarding", "deployment", "kickoff", "migration", "launch readiness",
        "integration", "connector", "configuration"
    ],
    "Internal Engineering": [
        "sprint planning", "sprint retrospective", "standup", "tech debt",
        "qa", "ci/cd", "design review", "estimation", "resource allocation"
    ]
}
```

### Implementation
```python
from pathlib import Path
import json
from collections import Counter, defaultdict

def assign_category(topics: list[str], summary_text: str) -> str:
    scores = defaultdict(int)
    topics_lower = [t.lower() for t in topics]
    
    for category, keywords in TOPIC_TAXONOMY.items():
        for kw in keywords:
            for topic in topics_lower:
                if kw in topic:
                    scores[category] += 1
    
    if scores:
        return max(scores, key=scores.get)
    
    # Fallback: scan summary text
    summary_lower = summary_text.lower()
    for category, keywords in TOPIC_TAXONOMY.items():
        for kw in keywords:
            if kw in summary_lower:
                scores[category] += 1
    
    return max(scores, key=scores.get) if scores else "Uncategorized"
```

### Expected Output
For each category: count of meetings, example meeting titles, avg sentiment score,
most common call type. Present as a table + 1 sentence of interpretation per category.

---

## TASK 2: SENTIMENT ANALYSIS

### Goal
Aggregate and compare sentiment across call types and topic categories.
Find meaningful trends — not just bar charts. Explain what each pattern means
and who should care about it.

### Data Sources
- **Meeting-level**: `summary.json` → `sentimentScore` (1.0–5.0), `overallSentiment`
- **Sentence-level**: `transcript.json` → each sentence has `sentimentType`
- **Key moments**: `summary.json` → `keyMoments[].type` (especially `churn_signal`, `concern`)

### Required Analyses

**1. Sentiment by Call Type**
```python
# Compute per call type: mean sentimentScore, distribution of overallSentiment labels
# Expected finding: customer_support will be lowest (~2.5), internal moderate (~3.4),
# external highest spread (1.4 to 4.9 depending on renewal vs onboarding)
```

**2. Sentiment Over Time**
```python
# Group meetings by week (startTime), compute avg sentimentScore per week per call type
# The Detect outage cluster (March 2026) should show a visible dip
# Look for recovery pattern in April meetings
```

**3. Sentence-Level Negativity Density**
```python
# For each meeting: negative_sentence_ratio = count(negative) / total_sentences
# High ratio meetings = where the real pain is
# Cross-reference: do meetings with churn_signal key moments have higher negativity ratio?
```

**4. Churn Signal Concentration**
```python
# Identify meetings that have >= 1 keyMoment of type "churn_signal"
# 61 churn_signal moments across all meetings
# Which customers? Which topics? What's the avg sentimentScore of these meetings?
```

**5. Sentiment by Topic Category**
```python
# Combine Task 1 categories with sentiment
# Expected: Incident & Outage = lowest, Compliance & Audit = highest
```

### Key Insight to Surface (example)
"Support calls average 2.6/5 sentiment — but the real alarm is that 14 of 28 support calls
contain at least one churn_signal key moment (50%). These cluster around 3 customers:
[names]. A support leader needs a real-time churn risk flag on these accounts."

---

## TASK 3: BONUS INSIGHTS

### Bonus 1: Churn Risk Scorecard (IMPLEMENT THIS)

**Why it matters**: Sales and CS leaders need to know which customer accounts are at risk
before the renewal call, not during it.

**How to build**:
```python
def compute_churn_risk(meetings_for_customer: list[dict]) -> dict:
    """
    For each external customer domain, aggregate across all their meetings:
    - churn_signal_count: number of keyMoments of type "churn_signal"
    - avg_sentiment: mean sentimentScore
    - negative_meeting_count: meetings with sentimentScore < 3.0
    - open_technical_issues: keyMoments of type "technical_issue" across all meetings
    - billing_disputes: "billing dispute" in topics
    - support_escalations: count of customer_support meetings for this domain
    
    Risk score = weighted formula:
    score = (churn_signal_count * 3) + (negative_meeting_count * 2) +
            (open_technical_issues * 1.5) + (billing_disputes * 2) +
            (support_escalations * 1) - (avg_sentiment * 2)
    
    Risk tier: HIGH (score > 10), MEDIUM (5-10), LOW (<5)
    """
```

**Output**: Table of all customer domains with risk tier, score, top risk factors.
Example column: `Northstar Pharma | HIGH | 14.2 | 3 churn signals, 2 billing disputes, avg sentiment 2.1`

### Bonus 2: Talk Time Ratio Analysis (IMPLEMENT THIS)

**Why it matters**: In support calls, if the Aegis rep is talking >65% of the time,
they're not listening — a known predictor of poor CSAT. In external renewal calls,
an AM dominating the conversation is a red flag.

**How to build**:
```python
def compute_talk_ratios(speakers_data: list[dict], all_emails: list[str]) -> dict:
    """
    From speakers.json, compute each speaker's total talk time.
    Then classify each speaker as 'aegis' or 'customer' based on email domain.
    
    aegis_talk_ratio = aegis_total_time / (aegis_total_time + customer_total_time)
    
    Flag if aegis_talk_ratio > 0.65 in customer_support calls (rep dominating)
    Flag if aegis_talk_ratio > 0.60 in external calls (AM not listening)
    """
```

**Output**: Per-meeting talk ratio. Summary: avg Aegis talk % by call type.
Insight: "In customer_support calls, Aegis reps spoke 58% of the time on average.
5 calls had Aegis talking >70% — all 5 have sentimentScore < 2.5."

### Bonus 3: Action Item Owner Analysis (DESCRIBE, optionally implement)

**Why it matters**: Action items from meetings often fall through. Knowing who owns the
most action items and whether follow-up meetings happen is a PM/ops superpower.

**How to build**:
```python
# From summary.json actionItems[] — format is always "PersonName: task"
# Parse out owner names
# Count action items per person across all meetings
# For Aegis internal people: are they the organizer of a subsequent meeting?
# (Check if they show up as host in a meeting 1–7 days later that shares topic keywords)
```

**Describe**: Top 5 action item owners. Which Aegis employees carry the most follow-up burden?
Are there meetings that generate action items but have no follow-up meeting in the dataset?

---

## IMPLEMENTATION STRUCTURE
```
transcript_intelligence/
├── pipeline.py           # Entry point: runs everything, prints summary stats
├── ingest.py             # load_all_meetings() → DataFrame
├── categorize.py         # Task 1: topic taxonomy + assignment
├── sentiment.py          # Task 2: aggregations + chart generation
├── churn_risk.py         # Bonus 1: churn scorecard
├── talk_time.py          # Bonus 2: talk ratio analysis
├── charts/               # Output PNGs generated by the scripts
└── README.md             # How to run, what each script does
```

OR build a single `pipeline.ipynb` with clearly separated sections.

### Core Data Loading Pattern
```python
from pathlib import Path
import json
import pandas as pd
from collections import defaultdict

DATASET_PATH = Path("./dataset")

def load_all_meetings() -> pd.DataFrame:
    records = []
    for meeting_dir in DATASET_PATH.iterdir():
        if not meeting_dir.is_dir():
            continue
        try:
            mi = json.loads((meeting_dir / "meeting-info.json").read_text())
            su = json.loads((meeting_dir / "summary.json").read_text())
            tr = json.loads((meeting_dir / "transcript.json").read_text())
            sp = json.loads((meeting_dir / "speakers.json").read_text())
            ev = json.loads((meeting_dir / "events.json").read_text())
            sm = json.loads((meeting_dir / "speaker-meta.json").read_text())
        except Exception as e:
            print(f"Error loading {meeting_dir.name}: {e}")
            continue
        
        call_type = classify_call_type(mi["title"], mi["allEmails"])
        category = assign_category(su["topics"], su["summary"])
        
        sentences = tr["data"]
        sent_counts = pd.Series([s["sentimentType"] for s in sentences]).value_counts()
        neg_ratio = sent_counts.get("negative", 0) / len(sentences) if sentences else 0
        
        churn_signals = [km for km in su["keyMoments"] if km["type"] == "churn_signal"]
        technical_issues = [km for km in su["keyMoments"] if km["type"] == "technical_issue"]
        
        records.append({
            "meeting_id": mi["meetingId"],
            "title": mi["title"],
            "start_time": pd.Timestamp(mi["startTime"]),
            "duration_min": mi["duration"],
            "call_type": call_type,
            "topic_category": category,
            "raw_topics": su["topics"],
            "sentiment_label": su["overallSentiment"],
            "sentiment_score": su["sentimentScore"],
            "summary": su["summary"],
            "action_items": su["actionItems"],
            "key_moments": su["keyMoments"],
            "churn_signal_count": len(churn_signals),
            "technical_issue_count": len(technical_issues),
            "sentence_count": len(sentences),
            "neg_sentence_ratio": neg_ratio,
            "all_emails": mi["allEmails"],
            "customer_domains": [e.split("@")[1] for e in mi["allEmails"]
                                  if not e.endswith("@aegiscloud.com")],
            "speakers_data": sp,
            "events_data": ev,
        })
    
    return pd.DataFrame(records)
```

---

## VISUALIZATION REQUIREMENTS

Use `matplotlib` + `seaborn` or `plotly`. For each analysis, produce:

1. **Task 1**: Horizontal bar chart — category vs meeting count, colored by avg sentiment
2. **Task 2a**: Grouped bar or violin plot — sentimentScore distribution by call type
3. **Task 2b**: Line chart — avg sentimentScore per week, one line per call type
4. **Task 2c**: Heatmap — topic category vs call type, cells = avg sentiment
5. **Bonus 1**: Color-coded table/bar chart — customer domains ranked by churn risk score
6. **Bonus 2**: Bar chart — avg Aegis talk % by call type, with threshold line at 60%

---

## KEY INTERPRETATIONS TO BUILD TOWARD

These are the insights that will land with a product/engineering leadership audience:

1. **The outage aftermath is visible in the data**: The Detect outage (March 2026) caused
   a cluster of low-sentiment meetings across all call types. Recovery is visible in April.

2. **Support calls are a churn early-warning system**: 50% of support calls contain a
   churn signal. These cluster on 4–5 specific customer domains. These are the accounts
   CS should be calling proactively.

3. **Compliance is the dominant external conversation topic** (23 meetings), and it has
   the highest sentiment — customers buying for compliance are engaged and satisfied.
   This is AegisCloud's strongest retention and expansion motion.

4. **Internal calls are where technical debt lives**: Feature gap and technical issue
   key moments concentrate in internal meetings, not surfaced externally. This gap
   between internal awareness and customer communication is a risk.

5. **Talk time ratios reveal listening gaps**: In the 5 most negative support calls,
   Aegis reps spoke >70% of the time. Less talking = higher satisfaction.

---

## TECH STACK

- Python 3.10+
- pandas, numpy
- matplotlib, seaborn (or plotly for interactive)
- Standard library only for ingestion (json, pathlib, collections)
- Optional: openai or anthropic SDK if you want LLM-powered re-categorization fallback
- Jupyter notebook for final presentation

No external database, no cloud services required. Everything runs locally on the dataset.

---

## WHAT NOT TO DO

- Do NOT re-run sentiment analysis from scratch on raw transcripts — the summary.json
  sentimentScore and keyMoments are already high-quality LLM output. Trust them.
- Do NOT try to build a production API or web server — clean notebook output is sufficient.
- Do NOT over-engineer topic clustering with embeddings/UMAP — the keyword taxonomy
  is explainable and auditable, which matters for a leadership presentation.
- Do NOT ignore the `keyMoments` field — it is the richest signal for bonus insights.
- Do NOT treat all external calls the same — renewal/churn calls and onboarding calls
  have opposite sentiment profiles and need separate analysis.
