"""Entry point: runs the full Transcript Intelligence pipeline.

Each analysis step is an instance of BaseAnalysis (Template Method).
Config is injected once at the top and flows through every step.
"""

from __future__ import annotations

from pathlib import Path

from .action_items import ActionItemAnalysis
from .categorize import TopicCategorizationAnalysis
from .churn_risk import ChurnRiskAnalysis
from .config import DEFAULT_CONFIG, PipelineConfig
from .customer_trajectory import CustomerTrajectoryAnalysis
from .ingest import DEFAULT_DATASET_PATH, load_all_meetings
from .sentiment import SentimentAnalysis
from .talk_time import TalkTimeAnalysis

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHARTS_DIR = _PROJECT_ROOT / "output" / "charts"


def main(config: PipelineConfig = DEFAULT_CONFIG) -> None:
    base_dir = DEFAULT_CHARTS_DIR

    print(f"Dataset : {DEFAULT_DATASET_PATH}")
    df = load_all_meetings(config=config)
    print(f"Loaded  : {len(df)} meetings")
    print(df["call_type"].value_counts().to_string())

    # Each step follows the Template Method: compute -> summarize -> save_charts
    # Charts are written into named subdirectories for easy navigation.
    df = TopicCategorizationAnalysis(config).run(df, base_dir / "01_categorization")
    SentimentAnalysis(config).run(df,                                base_dir / "02_sentiment")
    ChurnRiskAnalysis(config).run(df,                                base_dir / "03_churn_risk")
    df = TalkTimeAnalysis(config).run(df,                            base_dir / "04_talk_time")
    df = ActionItemAnalysis(config).run(df,                          base_dir / "05_action_items")
    CustomerTrajectoryAnalysis(config).run(df,                       base_dir / "06_customer_trajectory")

    print(f"\nPipeline complete. Charts saved under: {base_dir}")
    print("output/charts/")
    for sub in sorted(base_dir.iterdir()):
        if sub.is_dir():
            count = sum(1 for f in sub.iterdir() if f.suffix == ".html")
            print(f"  {sub.name}/  ({count} chart{'s' if count != 1 else ''})")


if __name__ == "__main__":
    main()
