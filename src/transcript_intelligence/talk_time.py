"""Bonus 2: Aegis vs customer talk-time ratio analysis.

TalkTimeAnalysis (Template Method): inherits BaseAnalysis; thresholds and
colors are injected via PipelineConfig rather than being hardcoded.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .base import BaseAnalysis
from .config import DEFAULT_CONFIG, PipelineConfig
from .ingest import AEGIS_DOMAIN

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHARTS_DIR = _PROJECT_ROOT / "output" / "charts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _email_to_name(email: str) -> str:
    """Convert 'first.last@aegiscloud.com' to 'First Last'."""
    local = email.split("@")[0]
    return " ".join(p.capitalize() for p in local.split("."))


def compute_talk_ratios(
    speakers_data: list[dict],
    all_emails: list[str],
    config: PipelineConfig = DEFAULT_CONFIG,
) -> dict:
    """Compute per-speaker talk time and Aegis-vs-customer split."""
    aegis_names = {
        _email_to_name(e) for e in all_emails if e.endswith(config.aegis_domain)
    }

    talk_times: dict[str, float] = defaultdict(float)
    for turn in speakers_data:
        name = turn.get("speakerName", "Unknown")
        duration = turn.get("endTimeTs", 0.0) - turn.get("timestamp", 0.0)
        if duration > 0:
            talk_times[name] += duration

    aegis_total = sum(t for n, t in talk_times.items() if n in aegis_names)
    customer_total = sum(t for n, t in talk_times.items() if n not in aegis_names)
    total = aegis_total + customer_total

    return {
        "aegis_talk_ratio": round(aegis_total / total, 4) if total > 0 else 0.5,
        "aegis_total_sec": round(aegis_total, 1),
        "customer_total_sec": round(customer_total, 1),
        "total_sec": round(total, 1),
        "speaker_breakdown": dict(talk_times),
    }


# ---------------------------------------------------------------------------
# Template Method implementation
# ---------------------------------------------------------------------------

class TalkTimeAnalysis(BaseAnalysis):
    """Bonus 2 — flags meetings where Aegis talks above threshold."""

    def __init__(self, config: PipelineConfig = DEFAULT_CONFIG) -> None:
        self._config = config
        self._avg_by_type: pd.Series | None = None
        self._flagged: pd.DataFrame | None = None

    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        ratios = df.apply(
            lambda r: compute_talk_ratios(r["speakers_data"], r["all_emails"], self._config),
            axis=1,
        )
        df = df.copy()
        df["aegis_talk_ratio"] = ratios.apply(lambda x: x["aegis_talk_ratio"])
        df["aegis_total_sec"] = ratios.apply(lambda x: x["aegis_total_sec"])
        df["customer_total_sec"] = ratios.apply(lambda x: x["customer_total_sec"])

        support_thresh = self._config.support_talk_threshold
        external_thresh = self._config.external_talk_threshold

        df["talk_flag"] = False
        df.loc[
            (df["call_type"] == "customer_support") & (df["aegis_talk_ratio"] > support_thresh),
            "talk_flag",
        ] = True
        df.loc[
            (df["call_type"] == "external") & (df["aegis_talk_ratio"] > external_thresh),
            "talk_flag",
        ] = True

        df["flag_label"] = df["talk_flag"].map(
            {True: "Over-talking (flagged)", False: "Normal"}
        )

        self._avg_by_type = df.groupby("call_type")["aegis_talk_ratio"].mean().round(3)
        self._flagged = df[df["talk_flag"]]
        return df

    def _summarize(self, df: pd.DataFrame) -> None:
        print("\n=== Bonus 2: Talk Time Analysis ===")
        print("Avg Aegis talk ratio by call type:")
        print(self._avg_by_type.to_string())
        print(f"\nFlagged meetings (Aegis over-talking): {len(self._flagged)}")
        if not self._flagged.empty:
            print(
                self._flagged[["title", "call_type", "aegis_talk_ratio", "sentiment_score"]]
                .sort_values("aegis_talk_ratio", ascending=False)
                .to_string(index=False)
            )

    def _save_charts(self, df: pd.DataFrame, charts_dir: Path) -> None:
        colors = self._config.call_type_colors
        support_thresh = self._config.support_talk_threshold
        external_thresh = self._config.external_talk_threshold

        avg_df = self._avg_by_type.reset_index()
        avg_df.columns = ["call_type", "avg_aegis_ratio"]

        fig1 = go.Figure()
        for _, row in avg_df.iterrows():
            ct = row["call_type"]
            fig1.add_trace(go.Bar(
                x=[ct],
                y=[row["avg_aegis_ratio"]],
                name=ct,
                marker_color=colors.get(ct, "#888"),
                text=[f"{row['avg_aegis_ratio']:.1%}"],
                textposition="outside",
            ))
        fig1.add_hline(
            y=external_thresh,
            line_dash="dash",
            line_color="orange",
            annotation_text=f"External threshold ({external_thresh:.0%})",
            annotation_position="top right",
        )
        fig1.add_hline(
            y=support_thresh,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Support threshold ({support_thresh:.0%})",
            annotation_position="top right",
        )
        fig1.update_layout(
            title="Average Aegis Talk Ratio by Call Type",
            yaxis=dict(tickformat=".0%", range=[0, 1], title="Aegis Talk Ratio"),
            xaxis_title="Call Type",
            showlegend=False,
            height=420,
        )
        out1 = charts_dir / "bonus2_talk_ratio_by_type.html"
        fig1.write_html(str(out1))
        print(f"Chart -> {out1}")

        try:
            import statsmodels  # noqa: F401
            _trendline: str | None = "ols"
        except ImportError:
            _trendline = None

        customer_df = df[df["call_type"] != "internal"]
        fig2 = px.scatter(
            customer_df,
            x="aegis_talk_ratio",
            y="sentiment_score",
            color="flag_label",
            color_discrete_map={
                "Over-talking (flagged)": "#EF553B",
                "Normal": "#636EFA",
            },
            facet_col="call_type",
            hover_data=["title", "call_type"],
            title="Aegis Talk Ratio vs Sentiment (customer-facing calls)",
            labels={
                "aegis_talk_ratio": "Aegis Talk Ratio",
                "sentiment_score": "Sentiment Score (1-5)",
            },
            trendline=_trendline,
            trendline_scope="trace" if _trendline else None,
        )
        fig2.add_vline(x=external_thresh, line_dash="dot", line_color="orange", row="all", col="all")
        fig2.update_layout(height=460)
        out2 = charts_dir / "bonus2_talk_ratio_vs_sentiment.html"
        fig2.write_html(str(out2))
        print(f"Chart -> {out2}")


# ---------------------------------------------------------------------------
# Backward-compatible functional API (used by the notebook)
# ---------------------------------------------------------------------------

def run_talk_time_analysis(
    df: pd.DataFrame,
    charts_dir: Path = DEFAULT_CHARTS_DIR,
    config: PipelineConfig = DEFAULT_CONFIG,
) -> pd.DataFrame:
    return TalkTimeAnalysis(config).run(df, charts_dir)
