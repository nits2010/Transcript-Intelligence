"""Bonus 1: customer churn risk scorecard.

RiskFactor (Chain of Responsibility): each factor independently computes its
contribution to the total risk score.  Adding a new signal means adding one
class — existing factors are untouched.

ChurnRiskAnalysis (Template Method): inherits BaseAnalysis and exposes the
scorecard DataFrame as self.result_df for the pipeline to consume.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd
import plotly.express as px

from .base import BaseAnalysis, RiskFactor
from .config import DEFAULT_CONFIG, PipelineConfig
from .logger import get_logger

_log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHARTS_DIR = _PROJECT_ROOT / "output" / "charts"


# ---------------------------------------------------------------------------
# Concrete risk factors (Chain of Responsibility)
# ---------------------------------------------------------------------------

class _ChurnSignalFactor(RiskFactor):
    def __init__(self, weight: float) -> None:
        self._weight = weight

    def contribution(self, meetings: list[dict]) -> float:
        return sum(m["churn_signal_count"] for m in meetings) * self._weight

    def describe(self, meetings: list[dict]) -> str | None:
        n = sum(m["churn_signal_count"] for m in meetings)
        return f"{n} churn signals" if n else None


class _NegativeMeetingFactor(RiskFactor):
    def __init__(self, weight: float) -> None:
        self._weight = weight

    def contribution(self, meetings: list[dict]) -> float:
        return sum(1 for m in meetings if m["sentiment_score"] < 3.0) * self._weight

    def describe(self, meetings: list[dict]) -> str | None:
        n = sum(1 for m in meetings if m["sentiment_score"] < 3.0)
        return f"{n} negative meetings" if n else None


class _TechnicalIssueFactor(RiskFactor):
    def __init__(self, weight: float) -> None:
        self._weight = weight

    def contribution(self, meetings: list[dict]) -> float:
        return sum(m["technical_issue_count"] for m in meetings) * self._weight

    def describe(self, meetings: list[dict]) -> str | None:
        n = sum(m["technical_issue_count"] for m in meetings)
        return f"{n} tech issues" if n else None


class _BillingDisputeFactor(RiskFactor):
    def __init__(self, weight: float) -> None:
        self._weight = weight

    def contribution(self, meetings: list[dict]) -> float:
        return (
            sum(
                1 for m in meetings
                if any("billing" in t.lower() for t in m["raw_topics"])
            )
            * self._weight
        )

    def describe(self, meetings: list[dict]) -> str | None:
        n = sum(
            1 for m in meetings
            if any("billing" in t.lower() for t in m["raw_topics"])
        )
        return f"{n} billing disputes" if n else None


class _SupportEscalationFactor(RiskFactor):
    def __init__(self, weight: float) -> None:
        self._weight = weight

    def contribution(self, meetings: list[dict]) -> float:
        return sum(1 for m in meetings if m["call_type"] == "customer_support") * self._weight

    def describe(self, meetings: list[dict]) -> str | None:
        n = sum(1 for m in meetings if m["call_type"] == "customer_support")
        return f"{n} support cases" if n else None


class _SentimentAdjustmentFactor(RiskFactor):
    """Higher avg sentiment reduces total risk score (negative contribution)."""

    def __init__(self, weight: float) -> None:
        self._weight = weight

    def contribution(self, meetings: list[dict]) -> float:
        avg = sum(m["sentiment_score"] for m in meetings) / len(meetings)
        return -avg * self._weight

    def describe(self, meetings: list[dict]) -> str | None:
        return None  # implicit — not shown as a labelled risk factor


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def _build_risk_factors(config: PipelineConfig) -> list[RiskFactor]:
    w = config.churn_weights
    return [
        _ChurnSignalFactor(w.churn_signal),
        _NegativeMeetingFactor(w.negative_meeting),
        _TechnicalIssueFactor(w.technical_issue),
        _BillingDisputeFactor(w.billing_dispute),
        _SupportEscalationFactor(w.support_escalation),
        _SentimentAdjustmentFactor(w.sentiment_adjustment),
    ]


def compute_churn_risk(
    meetings: list[dict],
    config: PipelineConfig = DEFAULT_CONFIG,
) -> dict:
    """Aggregate risk factors via the chain and return a scored record."""
    factors = _build_risk_factors(config)
    score = sum(f.contribution(meetings) for f in factors)
    top_factors = [
        desc for f in factors if (desc := f.describe(meetings)) is not None
    ]

    avg_sentiment = sum(m["sentiment_score"] for m in meetings) / len(meetings)
    tiers = config.churn_tiers
    tier = "HIGH" if score > tiers.high else ("MEDIUM" if score >= tiers.medium else "LOW")

    return {
        "score": round(score, 2),
        "tier": tier,
        "churn_signal_count": sum(m["churn_signal_count"] for m in meetings),
        "avg_sentiment": round(avg_sentiment, 2),
        "negative_meeting_count": sum(1 for m in meetings if m["sentiment_score"] < 3.0),
        "open_technical_issues": sum(m["technical_issue_count"] for m in meetings),
        "billing_disputes": sum(
            1 for m in meetings
            if any("billing" in t.lower() for t in m["raw_topics"])
        ),
        "support_escalations": sum(
            1 for m in meetings if m["call_type"] == "customer_support"
        ),
        "meeting_count": len(meetings),
        "top_factors": ", ".join(top_factors) if top_factors else "none",
    }


# ---------------------------------------------------------------------------
# Template Method implementation
# ---------------------------------------------------------------------------

class ChurnRiskAnalysis(BaseAnalysis):
    """Bonus 1 — builds a churn risk scorecard per customer domain.

    The derived scorecard DataFrame is stored on self.result_df after run().
    """

    def __init__(self, config: PipelineConfig = DEFAULT_CONFIG) -> None:
        self._config = config
        self.result_df: pd.DataFrame = pd.DataFrame()

    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        customer_facing = df[df["call_type"] != "internal"].copy()

        domain_meetings: dict[str, list[dict]] = defaultdict(list)
        for _, row in customer_facing.iterrows():
            row_dict = row.to_dict()
            for domain in row["customer_domains"]:
                domain_meetings[domain].append(row_dict)

        rows = []
        for domain, meetings in domain_meetings.items():
            risk = compute_churn_risk(meetings, self._config)
            risk["customer_domain"] = domain
            rows.append(risk)

        self.result_df = (
            pd.DataFrame(rows)
            .sort_values("score", ascending=False)
            .reset_index(drop=True)
        )
        return df  # input df unchanged

    def _summarize(self, df: pd.DataFrame) -> None:
        display_cols = [
            "customer_domain", "tier", "score", "churn_signal_count",
            "avg_sentiment", "support_escalations", "meeting_count",
        ]
        _log.info(
            "=== Bonus 1: Churn Risk Scorecard ===\n%s",
            self.result_df[display_cols].to_string(index=False),
        )

    def _save_charts(self, df: pd.DataFrame, charts_dir: Path) -> None:
        colors = self._config.tier_colors
        sdf = self.result_df

        fig1 = px.bar(
            sdf.sort_values("score"),
            x="score",
            y="customer_domain",
            orientation="h",
            color="tier",
            color_discrete_map=colors,
            title="Customer Churn Risk Scorecard",
            labels={"score": "Risk Score", "customer_domain": "Customer Domain"},
            hover_data={
                "churn_signal_count": True,
                "avg_sentiment": True,
                "negative_meeting_count": True,
                "support_escalations": True,
                "top_factors": True,
            },
            text="score",
            category_orders={"tier": ["HIGH", "MEDIUM", "LOW"]},
        )
        fig1.update_traces(textposition="outside")
        fig1.update_layout(height=max(400, len(sdf) * 22))
        out1 = charts_dir / "bonus1_churn_scorecard.html"
        fig1.write_html(str(out1))
        _log.debug("Chart saved: %s", out1)

        fig2 = px.scatter(
            sdf,
            x="avg_sentiment",
            y="score",
            color="tier",
            color_discrete_map=colors,
            size="meeting_count",
            hover_data=["customer_domain", "churn_signal_count", "top_factors"],
            title="Churn Risk Score vs Average Sentiment (bubble = # meetings)",
            labels={"avg_sentiment": "Avg Sentiment (1-5)", "score": "Risk Score"},
            text="customer_domain",
        )
        fig2.update_traces(textposition="top center")
        fig2.update_layout(height=520)
        out2 = charts_dir / "bonus1_churn_scatter.html"
        fig2.write_html(str(out2))
        _log.debug("Chart saved: %s", out2)


# ---------------------------------------------------------------------------
# Backward-compatible functional API (used by the notebook)
# ---------------------------------------------------------------------------

def build_churn_scorecard(
    df: pd.DataFrame,
    charts_dir: Path = DEFAULT_CHARTS_DIR,
    config: PipelineConfig = DEFAULT_CONFIG,
) -> pd.DataFrame:
    analysis = ChurnRiskAnalysis(config)
    analysis.run(df, charts_dir)
    return analysis.result_df
