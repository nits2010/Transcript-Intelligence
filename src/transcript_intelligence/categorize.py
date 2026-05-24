"""Task 1: topic taxonomy and category assignment.

CategorizationStrategy (Strategy pattern): strategies are tried in order;
the first that returns a non-empty score dict wins.  This replaces the
if/else fallback with a clean chain of responsibility over scoring strategies.

TopicCategorizationAnalysis (Template Method): inherits BaseAnalysis and
implements _compute / _summarize / _save_charts.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd
import plotly.express as px

from .base import BaseAnalysis, CategorizationStrategy
from .config import DEFAULT_CONFIG, PipelineConfig
from .logger import get_logger

_log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHARTS_DIR = _PROJECT_ROOT / "output" / "charts"


# ---------------------------------------------------------------------------
# Concrete categorization strategies (Strategy pattern)
# ---------------------------------------------------------------------------

class _TopicKeywordStrategy(CategorizationStrategy):
    """Score categories by matching keywords against the raw topics[] array."""

    def __init__(self, taxonomy: dict[str, list[str]]) -> None:
        self._taxonomy = taxonomy

    def score(self, topics: list[str], summary: str) -> dict[str, int]:
        scores: dict[str, int] = defaultdict(int)
        topics_lower = [t.lower() for t in topics]
        for category, keywords in self._taxonomy.items():
            for kw in keywords:
                for topic in topics_lower:
                    if kw in topic:
                        scores[category] += 1
        return dict(scores)


class _SummaryTextStrategy(CategorizationStrategy):
    """Fallback: scan the LLM summary text when topic tags yield no signal."""

    def __init__(self, taxonomy: dict[str, list[str]]) -> None:
        self._taxonomy = taxonomy

    def score(self, topics: list[str], summary: str) -> dict[str, int]:
        scores: dict[str, int] = defaultdict(int)
        summary_lower = summary.lower()
        for category, keywords in self._taxonomy.items():
            for kw in keywords:
                if kw in summary_lower:
                    scores[category] += 1
        return dict(scores)


# ---------------------------------------------------------------------------
# Category assignment (uses strategy chain)
# ---------------------------------------------------------------------------

def assign_category(
    topics: list[str],
    summary_text: str,
    config: PipelineConfig = DEFAULT_CONFIG,
) -> tuple[str, str | None]:
    """Return (primary_category, secondary_category | None).

    Walks the strategy chain; uses the first strategy that produces scores.
    Returns the top-two categories for cross-cutting analysis.
    """
    strategies: list[CategorizationStrategy] = [
        _TopicKeywordStrategy(config.topic_taxonomy),
        _SummaryTextStrategy(config.topic_taxonomy),
    ]

    for strategy in strategies:
        scores = strategy.score(topics, summary_text)
        if scores:
            sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            primary = sorted_cats[0][0]
            secondary = (
                sorted_cats[1][0]
                if len(sorted_cats) > 1 and sorted_cats[1][1] > 0
                else None
            )
            return primary, secondary

    return "Uncategorized", None


# ---------------------------------------------------------------------------
# Template Method implementation
# ---------------------------------------------------------------------------

class TopicCategorizationAnalysis(BaseAnalysis):
    """Task 1 — assigns canonical topic categories to every meeting."""

    def __init__(self, config: PipelineConfig = DEFAULT_CONFIG) -> None:
        self._config = config
        self._summary_table: pd.DataFrame | None = None

    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        results = df.apply(
            lambda r: assign_category(r["raw_topics"], r["summary"], self._config),
            axis=1,
        )
        df = df.copy()
        df["topic_category"] = results.apply(lambda x: x[0])
        df["secondary_category"] = results.apply(lambda x: x[1])

        self._summary_table = (
            df.groupby("topic_category")
            .agg(
                count=("meeting_id", "count"),
                avg_sentiment=("sentiment_score", "mean"),
                dominant_call_type=("call_type", lambda x: x.value_counts().index[0]),
            )
            .sort_values("count", ascending=False)
        )
        self._summary_table["avg_sentiment"] = self._summary_table["avg_sentiment"].round(2)
        return df

    def _summarize(self, df: pd.DataFrame) -> None:
        _log.info("=== Task 1: Topic Categorization ===\n%s", self._summary_table.to_string())

    def _save_charts(self, df: pd.DataFrame, charts_dir: Path) -> None:
        chart_df = self._summary_table.reset_index().sort_values("count")
        fig = px.bar(
            chart_df,
            x="count",
            y="topic_category",
            orientation="h",
            color="avg_sentiment",
            color_continuous_scale="RdYlGn",
            range_color=[1.0, 5.0],
            title="Topic Categories — Meeting Count & Avg Sentiment",
            labels={
                "count": "# Meetings",
                "topic_category": "Category",
                "avg_sentiment": "Avg Sentiment (1-5)",
            },
            hover_data={"dominant_call_type": True},
            text="count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=480, coloraxis_colorbar=dict(title="Avg Sentiment"))
        out = charts_dir / "task1_topic_categories.html"
        fig.write_html(str(out))
        _log.debug("Chart saved: %s", out)


# ---------------------------------------------------------------------------
# Backward-compatible functional API (used by the notebook)
# ---------------------------------------------------------------------------

def run_categorization(
    df: pd.DataFrame,
    charts_dir: Path = DEFAULT_CHARTS_DIR,
    config: PipelineConfig = DEFAULT_CONFIG,
) -> pd.DataFrame:
    return TopicCategorizationAnalysis(config).run(df, charts_dir)
