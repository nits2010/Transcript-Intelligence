"""Load meeting JSON files into a pandas DataFrame.

CallTypeStrategy (Strategy pattern): each concrete strategy encapsulates one
classification rule.  classify_call_type() walks the ordered chain and returns
the label of the first matching strategy — no if/elif ladder needed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .base import CallTypeStrategy
from .config import DEFAULT_CONFIG, PipelineConfig

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_PATH = _PROJECT_ROOT / "dataset"

# Keep as a module-level alias so other modules can do `from .ingest import AEGIS_DOMAIN`
AEGIS_DOMAIN = DEFAULT_CONFIG.aegis_domain


# ---------------------------------------------------------------------------
# Concrete call type strategies (Strategy pattern)
# ---------------------------------------------------------------------------

class _SupportCaseStrategy(CallTypeStrategy):
    """Title starts with 'Support Case #...' or 'Escalation ...'."""

    @property
    def label(self) -> str:
        return "customer_support"

    def matches(self, title: str, external_emails: list[str]) -> bool:
        t = title.lower()
        return "support case" in t or t.startswith("escalation")


class _InternalMeetingStrategy(CallTypeStrategy):
    """No external (non-Aegis) email addresses on the invite."""

    @property
    def label(self) -> str:
        return "internal"

    def matches(self, title: str, external_emails: list[str]) -> bool:
        return not external_emails


class _ExternalMeetingStrategy(CallTypeStrategy):
    """Catch-all — external participants present, not a support case."""

    @property
    def label(self) -> str:
        return "external"

    def matches(self, title: str, external_emails: list[str]) -> bool:
        return True


# Ordered chain: first match wins
_CALL_TYPE_STRATEGIES: list[CallTypeStrategy] = [
    _SupportCaseStrategy(),
    _InternalMeetingStrategy(),
    _ExternalMeetingStrategy(),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_call_type(
    title: str,
    all_emails: list[str],
    config: PipelineConfig = DEFAULT_CONFIG,
) -> str:
    """Classify a meeting via an ordered chain of CallTypeStrategy instances."""
    external_emails = [e for e in all_emails if not e.endswith(config.aegis_domain)]
    for strategy in _CALL_TYPE_STRATEGIES:
        if strategy.matches(title, external_emails):
            return strategy.label
    return "external"


def load_all_meetings(
    dataset_path: Path | None = None,
    config: PipelineConfig = DEFAULT_CONFIG,
) -> pd.DataFrame:
    """Load all meetings from dataset subdirectories into a DataFrame."""
    path = dataset_path or DEFAULT_DATASET_PATH
    records = []

    for meeting_dir in sorted(path.iterdir()):
        if not meeting_dir.is_dir():
            continue
        try:
            mi = json.loads((meeting_dir / "meeting-info.json").read_text(encoding="utf-8"))
            su = json.loads((meeting_dir / "summary.json").read_text(encoding="utf-8"))
            tr = json.loads((meeting_dir / "transcript.json").read_text(encoding="utf-8"))
            sp = json.loads((meeting_dir / "speakers.json").read_text(encoding="utf-8"))
            ev = json.loads((meeting_dir / "events.json").read_text(encoding="utf-8"))
            sm = json.loads((meeting_dir / "speaker-meta.json").read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  [skip] {meeting_dir.name}: {e}")
            continue

        call_type = classify_call_type(mi["title"], mi["allEmails"], config)

        sentences = tr.get("data", [])
        sent_counts: dict[str, int] = {}
        for s in sentences:
            t = s.get("sentimentType", "neutral")
            sent_counts[t] = sent_counts.get(t, 0) + 1
        total = len(sentences) or 1
        neg_ratio = sent_counts.get("negative", 0) / total

        key_moments = su.get("keyMoments", [])
        churn_signals = [km for km in key_moments if km.get("type") == "churn_signal"]
        technical_issues = [km for km in key_moments if km.get("type") == "technical_issue"]

        customer_domains = list({
            e.split("@")[1]
            for e in mi["allEmails"]
            if not e.endswith(config.aegis_domain)
        })

        records.append({
            "meeting_id": mi["meetingId"],
            "title": mi["title"],
            "start_time": pd.Timestamp(mi["startTime"]),
            "duration_min": float(mi.get("duration", 0.0)),
            "call_type": call_type,
            "raw_topics": su.get("topics", []),
            "sentiment_label": su.get("overallSentiment", ""),
            "sentiment_score": float(su.get("sentimentScore", 3.0)),
            "summary": su.get("summary", ""),
            "action_items": su.get("actionItems", []),
            "key_moments": key_moments,
            "churn_signal_count": len(churn_signals),
            "technical_issue_count": len(technical_issues),
            "sentence_count": len(sentences),
            "neg_sentence_ratio": round(neg_ratio, 4),
            "all_emails": mi["allEmails"],
            "customer_domains": customer_domains,
            "speakers_data": sp,
            "events_data": ev,
            "speaker_meta": sm,
        })

    df = pd.DataFrame(records)
    df["week"] = df["start_time"].dt.to_period("W").dt.start_time
    return df
