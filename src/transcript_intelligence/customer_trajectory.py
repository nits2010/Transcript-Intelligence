"""Bonus 4: Customer sentiment trajectory — how satisfaction evolves over time.

CustomerTrajectoryAnalysis (Template Method): inherits BaseAnalysis; the
minimum meeting count and trend delta are injected via PipelineConfig.
The derived trends DataFrame is exposed as self.result_df after run().
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px

from .base import BaseAnalysis
from .config import DEFAULT_CONFIG, PipelineConfig

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHARTS_DIR = _PROJECT_ROOT / "output" / "charts"


# ---------------------------------------------------------------------------
# Template Method implementation
# ---------------------------------------------------------------------------

class CustomerTrajectoryAnalysis(BaseAnalysis):
    """Bonus 4 — per-customer sentiment trend classification over time.

    The trends summary DataFrame is stored on self.result_df after run().
    """

    def __init__(self, config: PipelineConfig = DEFAULT_CONFIG) -> None:
        self._config = config
        self.result_df: pd.DataFrame = pd.DataFrame()
        self._tl_filtered: pd.DataFrame = pd.DataFrame()
        self._qualified: list[str] = []

    def _classify_trend(self, first_half: float, second_half: float) -> str:
        delta = second_half - first_half
        if delta > self._config.trend_delta:
            return "improving"
        if delta < -self._config.trend_delta:
            return "declining"
        return "stable"

    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        min_meetings = self._config.min_trajectory_meetings

        rows = []
        for _, row in df[df["call_type"] != "internal"].iterrows():
            for domain in row["customer_domains"]:
                rows.append({
                    "domain": domain,
                    "start_time": row["start_time"],
                    "sentiment_score": row["sentiment_score"],
                    "call_type": row["call_type"],
                    "title": row["title"],
                    "churn_signal_count": row["churn_signal_count"],
                    "sentiment_label": row["sentiment_label"],
                })

        tl = pd.DataFrame(rows).sort_values("start_time")
        domain_counts = tl["domain"].value_counts()
        qualified = domain_counts[domain_counts >= min_meetings].index.tolist()
        tl_filtered = tl[tl["domain"].isin(qualified)].copy()

        trends = []
        for domain in qualified:
            cust = tl_filtered[tl_filtered["domain"] == domain].sort_values("start_time")
            mid = len(cust) // 2
            first_half = (
                cust.iloc[:mid]["sentiment_score"].mean() if mid > 0
                else cust["sentiment_score"].mean()
            )
            second_half = cust.iloc[mid:]["sentiment_score"].mean()
            trend = self._classify_trend(first_half, second_half)
            trends.append({
                "domain": domain,
                "meeting_count": len(cust),
                "avg_sentiment": round(cust["sentiment_score"].mean(), 2),
                "first_half_avg": round(first_half, 2),
                "second_half_avg": round(second_half, 2),
                "trend": trend,
                "total_churn_signals": int(cust["churn_signal_count"].sum()),
                "date_range": (
                    f"{cust['start_time'].min().strftime('%b %d')} - "
                    f"{cust['start_time'].max().strftime('%b %d')}"
                ),
            })

        self.result_df = pd.DataFrame(trends).sort_values("avg_sentiment")
        self._tl_filtered = tl_filtered
        self._qualified = qualified
        return df  # input df unchanged

    def _summarize(self, df: pd.DataFrame) -> None:
        min_meetings = self._config.min_trajectory_meetings
        print(f"\n=== Bonus 4: Customer Sentiment Trajectory ===")
        print(
            f"Tracking {len(self._qualified)} customers with {min_meetings}+ meetings "
            f"({len(self._tl_filtered)} data points)"
        )
        print("\nCustomer trend summary:")
        print(self.result_df.to_string(index=False))

    def _save_charts(self, df: pd.DataFrame, charts_dir: Path) -> None:
        colors = self._config.trend_colors
        min_meetings = self._config.min_trajectory_meetings

        fig1 = px.line(
            self._tl_filtered,
            x="start_time",
            y="sentiment_score",
            color="domain",
            markers=True,
            title=f"Customer Sentiment Over Time — customers with {min_meetings}+ meetings",
            labels={
                "start_time": "Date",
                "sentiment_score": "Sentiment Score (1-5)",
                "domain": "Customer",
            },
            hover_data=["call_type", "title", "churn_signal_count", "sentiment_label"],
        )
        fig1.add_hline(
            y=3.0,
            line_dash="dash",
            line_color="gray",
            annotation_text="Neutral (3.0)",
            annotation_position="bottom right",
        )
        fig1.update_yaxes(range=[1, 5.2])
        fig1.update_layout(height=540, legend_title_text="Customer Domain")
        out1 = charts_dir / "bonus4_customer_trajectory.html"
        fig1.write_html(str(out1))
        print(f"Chart -> {out1}")

        fig2 = px.bar(
            self.result_df.sort_values("avg_sentiment"),
            x="avg_sentiment",
            y="domain",
            orientation="h",
            color="trend",
            color_discrete_map=colors,
            title="Customer Avg Sentiment & Trend Direction",
            labels={"avg_sentiment": "Avg Sentiment (1-5)", "domain": "Customer Domain"},
            hover_data=[
                "meeting_count", "first_half_avg", "second_half_avg",
                "total_churn_signals", "date_range",
            ],
            text="avg_sentiment",
        )
        fig2.add_vline(x=3.0, line_dash="dash", line_color="gray",
                       annotation_text="Neutral", annotation_position="top")
        fig2.update_traces(textposition="outside")
        fig2.update_layout(height=max(400, len(self.result_df) * 24))
        out2 = charts_dir / "bonus4_trend_summary.html"
        fig2.write_html(str(out2))
        print(f"Chart -> {out2}")

        tl = self._tl_filtered.copy()
        tl["month"] = tl["start_time"].dt.to_period("M").astype(str)
        monthly_pivot = (
            tl.pivot_table(
                values="sentiment_score",
                index="domain",
                columns="month",
                aggfunc="mean",
            ).round(2)
        )
        if not monthly_pivot.empty:
            fig3 = px.imshow(
                monthly_pivot,
                text_auto=True,
                color_continuous_scale="RdYlGn",
                range_color=[1.0, 5.0],
                title="Customer Sentiment Heatmap by Month",
                labels={"color": "Avg Sentiment (1-5)", "x": "Month", "y": "Customer"},
                aspect="auto",
            )
            fig3.update_layout(height=max(380, len(self._qualified) * 26))
            out3 = charts_dir / "bonus4_monthly_heatmap.html"
            fig3.write_html(str(out3))
            print(f"Chart -> {out3}")


# ---------------------------------------------------------------------------
# Backward-compatible functional API (used by the notebook)
# ---------------------------------------------------------------------------

def run_customer_trajectory(
    df: pd.DataFrame,
    charts_dir: Path = DEFAULT_CHARTS_DIR,
    config: PipelineConfig = DEFAULT_CONFIG,
) -> pd.DataFrame:
    analysis = CustomerTrajectoryAnalysis(config)
    analysis.run(df, charts_dir)
    return analysis.result_df
