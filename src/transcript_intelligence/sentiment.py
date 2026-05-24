"""Task 2: sentiment aggregations and chart generation.

SentimentAnalysis (Template Method): inherits BaseAnalysis; _compute builds
all aggregations and stores them as instance state; _save_charts renders six
Plotly charts from that state.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px

from .base import BaseAnalysis
from .config import DEFAULT_CONFIG, PipelineConfig
from .logger import get_logger

_log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHARTS_DIR = _PROJECT_ROOT / "output" / "charts"


class SentimentAnalysis(BaseAnalysis):
    """Task 2 — six complementary sentiment views across the dataset."""

    def __init__(self, config: PipelineConfig = DEFAULT_CONFIG) -> None:
        self._config = config
        self._by_type: pd.DataFrame | None = None
        self._weekly: pd.DataFrame | None = None
        self._churn_agg: pd.DataFrame | None = None

    # ------------------------------------------------------------------
    # Template Method steps
    # ------------------------------------------------------------------

    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        self._by_type = df.groupby("call_type")["sentiment_score"].agg(
            ["mean", "std", "count"]
        )

        weekly = (
            df.groupby(["week", "call_type"])["sentiment_score"]
            .mean()
            .reset_index()
            .sort_values("week")
        )
        weekly["week_str"] = weekly["week"].dt.strftime("%Y-%m-%d")
        self._weekly = weekly

        churn_rows = []
        for _, row in df[df["churn_signal_count"] > 0].iterrows():
            for domain in row["customer_domains"]:
                churn_rows.append({
                    "domain": domain,
                    "churn_signals": row["churn_signal_count"],
                    "sentiment_score": row["sentiment_score"],
                    "call_type": row["call_type"],
                })
        if churn_rows:
            churn_df = pd.DataFrame(churn_rows)
            self._churn_agg = (
                churn_df.groupby("domain")
                .agg(
                    total_churn_signals=("churn_signals", "sum"),
                    avg_sentiment=("sentiment_score", "mean"),
                    meeting_count=("domain", "count"),
                )
                .sort_values("total_churn_signals", ascending=False)
                .head(15)
                .reset_index()
            )
            self._churn_agg["avg_sentiment"] = self._churn_agg["avg_sentiment"].round(2)

        return df

    def _summarize(self, df: pd.DataFrame) -> None:
        _log.info("=== Task 2: Sentiment by Call Type ===\n%s", self._by_type.round(2).to_string())

    def _save_charts(self, df: pd.DataFrame, charts_dir: Path) -> None:
        colors = self._config.call_type_colors
        call_order = {"call_type": ["customer_support", "internal", "external"]}

        # 1. Violin: sentiment distribution by call type
        fig1 = px.violin(
            df,
            x="call_type",
            y="sentiment_score",
            color="call_type",
            box=True,
            points="all",
            color_discrete_map=colors,
            title="Sentiment Score Distribution by Call Type",
            labels={"call_type": "Call Type", "sentiment_score": "Sentiment Score (1-5)"},
            hover_data=["title"],
            category_orders=call_order,
        )
        fig1.update_layout(showlegend=False, height=500)
        out1 = charts_dir / "task2a_sentiment_by_call_type.html"
        fig1.write_html(str(out1))
        _log.debug("Chart saved: %s", out1)

        # 2. Line: weekly avg sentiment per call type
        fig2 = px.line(
            self._weekly,
            x="week_str",
            y="sentiment_score",
            color="call_type",
            markers=True,
            color_discrete_map=colors,
            title="Weekly Average Sentiment by Call Type (Feb-Apr 2026)",
            labels={
                "week_str": "Week of",
                "sentiment_score": "Avg Sentiment (1-5)",
                "call_type": "Call Type",
            },
        )
        fig2.add_hline(
            y=3.0,
            line_dash="dash",
            line_color="gray",
            annotation_text="Neutral (3.0)",
            annotation_position="bottom right",
        )
        fig2.update_layout(height=450)
        out2 = charts_dir / "task2b_sentiment_over_time.html"
        fig2.write_html(str(out2))
        _log.debug("Chart saved: %s", out2)

        # 3. Scatter: meeting sentiment vs sentence negativity ratio
        try:
            import statsmodels  # noqa: F401
            _trendline: str | None = "ols"
        except ImportError:
            _trendline = None

        fig3 = px.scatter(
            df,
            x="sentiment_score",
            y="neg_sentence_ratio",
            color="call_type",
            size="sentence_count",
            color_discrete_map=colors,
            hover_data=["title", "churn_signal_count"],
            title="Meeting Sentiment Score vs Sentence Negativity Ratio",
            labels={
                "sentiment_score": "Meeting Sentiment Score (1-5)",
                "neg_sentence_ratio": "Fraction of Negative Sentences",
                "call_type": "Call Type",
            },
            trendline=_trendline,
            trendline_scope="overall" if _trendline else None,
            trendline_color_override="black" if _trendline else None,
        )
        fig3.update_layout(height=480)
        out3 = charts_dir / "task2c_negativity_density.html"
        fig3.write_html(str(out3))
        _log.debug("Chart saved: %s", out3)

        # 4. Bar: churn signal concentration by customer domain
        if self._churn_agg is not None:
            fig4 = px.bar(
                self._churn_agg.sort_values("total_churn_signals"),
                x="total_churn_signals",
                y="domain",
                orientation="h",
                color="avg_sentiment",
                color_continuous_scale="RdYlGn",
                range_color=[1.0, 5.0],
                title="Churn Signal Concentration by Customer Domain (top 15)",
                labels={
                    "total_churn_signals": "Total Churn Signals",
                    "domain": "Customer Domain",
                    "avg_sentiment": "Avg Sentiment",
                },
                hover_data={"meeting_count": True},
                text="total_churn_signals",
            )
            fig4.update_traces(textposition="outside")
            fig4.update_layout(height=520)
            out4 = charts_dir / "task2d_churn_signal_concentration.html"
            fig4.write_html(str(out4))
            _log.debug("Chart saved: %s", out4)

        # 5. Heatmap: topic category x call type avg sentiment
        if "topic_category" in df.columns:
            pivot = df.pivot_table(
                values="sentiment_score",
                index="topic_category",
                columns="call_type",
                aggfunc="mean",
            ).round(2)
            fig5 = px.imshow(
                pivot,
                text_auto=True,
                color_continuous_scale="RdYlGn",
                range_color=[1.0, 5.0],
                title="Avg Sentiment Score: Topic Category x Call Type",
                labels={"color": "Avg Sentiment (1-5)"},
                aspect="auto",
            )
            fig5.update_layout(height=480)
            out5 = charts_dir / "task2e_sentiment_heatmap.html"
            fig5.write_html(str(out5))
            _log.debug("Chart saved: %s", out5)

        # 6. Stacked bar: sentiment label distribution by call type
        label_counts = (
            df.groupby(["call_type", "sentiment_label"])
            .size()
            .reset_index(name="count")
        )
        fig6 = px.bar(
            label_counts,
            x="call_type",
            y="count",
            color="sentiment_label",
            barmode="stack",
            title="Sentiment Label Distribution by Call Type",
            labels={
                "call_type": "Call Type",
                "count": "# Meetings",
                "sentiment_label": "Sentiment Label",
            },
            category_orders={
                "sentiment_label": list(self._config.sentiment_label_order),
                **call_order,
            },
            color_discrete_sequence=px.colors.diverging.RdYlGn,
        )
        fig6.update_layout(height=450)
        out6 = charts_dir / "task2f_sentiment_label_distribution.html"
        fig6.write_html(str(out6))
        _log.debug("Chart saved: %s", out6)


# ---------------------------------------------------------------------------
# Backward-compatible functional API (used by the notebook)
# ---------------------------------------------------------------------------

def run_sentiment_analysis(
    df: pd.DataFrame,
    charts_dir: Path = DEFAULT_CHARTS_DIR,
    config: PipelineConfig = DEFAULT_CONFIG,
) -> dict:
    SentimentAnalysis(config).run(df, charts_dir)
    return {}
