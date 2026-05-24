"""Abstract base classes for the Transcript Intelligence pipeline.

Three design patterns are defined here:
  - Strategy       : CallTypeStrategy, CategorizationStrategy
  - Chain of Resp. : RiskFactor
  - Template Method: BaseAnalysis
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Strategy — call type classification
# ---------------------------------------------------------------------------

class CallTypeStrategy(ABC):
    """Decides whether a meeting belongs to a particular call type."""

    @abstractmethod
    def matches(self, title: str, external_emails: list[str]) -> bool:
        """Return True if this strategy applies to the given meeting."""

    @property
    @abstractmethod
    def label(self) -> str:
        """The call_type label emitted when this strategy matches."""


# ---------------------------------------------------------------------------
# Strategy — topic categorization
# ---------------------------------------------------------------------------

class CategorizationStrategy(ABC):
    """Scores canonical topic categories from available meeting signals.

    Strategies are tried in order; the first one that returns a non-empty
    score dict is used.  This lets keyword matching take precedence over
    the summary-text fallback without an explicit if/else in the caller.
    """

    @abstractmethod
    def score(self, topics: list[str], summary: str) -> dict[str, int]:
        """Return {category: score} mapping. Empty dict means no signal."""


# ---------------------------------------------------------------------------
# Chain of Responsibility — churn risk factors
# ---------------------------------------------------------------------------

class RiskFactor(ABC):
    """One independent contributor to a customer's churn risk score.

    Each concrete factor encapsulates its weight and the raw data access
    pattern.  The chain is summed in compute_churn_risk() so that new
    factors can be added without touching existing ones.
    """

    @abstractmethod
    def contribution(self, meetings: list[dict]) -> float:
        """Numeric contribution (positive = more risk, negative = less)."""

    @abstractmethod
    def describe(self, meetings: list[dict]) -> str | None:
        """Human-readable label for this factor, or None when value is zero."""


# ---------------------------------------------------------------------------
# Template Method — analysis pipeline steps
# ---------------------------------------------------------------------------

class BaseAnalysis(ABC):
    """Common skeleton for every analysis step.

    Subclasses implement _compute, _summarize, and _save_charts.
    run() calls them in order and returns the (possibly enriched) DataFrame.

    Intermediate state needed across the three steps is stored on self by
    _compute so that _summarize and _save_charts can access it without
    recomputing.
    """

    def run(self, df: pd.DataFrame, charts_dir: Path) -> pd.DataFrame:
        """Execute the full analysis: compute → summarize → save charts."""
        charts_dir.mkdir(parents=True, exist_ok=True)
        result_df = self._compute(df)
        self._summarize(result_df)
        self._save_charts(result_df, charts_dir)
        return result_df

    @abstractmethod
    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """Derive new columns or build result DataFrame; store side-outputs
        as instance attributes for use in _summarize and _save_charts."""

    @abstractmethod
    def _summarize(self, df: pd.DataFrame) -> None:
        """Print a concise console summary of key findings."""

    @abstractmethod
    def _save_charts(self, df: pd.DataFrame, charts_dir: Path) -> None:
        """Write all Plotly HTML charts produced by this analysis."""
