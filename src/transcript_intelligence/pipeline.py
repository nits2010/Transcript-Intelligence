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
from .logger import get_logger, setup_logging
from .sentiment import SentimentAnalysis
from .talk_time import TalkTimeAnalysis

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHARTS_DIR = _PROJECT_ROOT / "output" / "charts"

_log = get_logger(__name__)


def main(config: PipelineConfig = DEFAULT_CONFIG) -> None:
    lc = config.logging_config
    setup_logging(level=lc.level, fmt=lc.format, file=lc.file,
                  max_bytes=lc.max_bytes, backup_count=lc.backup_count)

    base_dir = DEFAULT_CHARTS_DIR

    _log.info("Dataset : %s", DEFAULT_DATASET_PATH)
    df = load_all_meetings(config=config)
    _log.info("Loaded  : %d meetings", len(df))
    _log.info("Call type distribution:\n%s", df["call_type"].value_counts().to_string())

    # Each step follows the Template Method: compute -> summarize -> save_charts
    # Charts are written into named subdirectories for easy navigation.
    df = TopicCategorizationAnalysis(config).run(df, base_dir / "01_categorization")
    SentimentAnalysis(config).run(df,                                base_dir / "02_sentiment")
    ChurnRiskAnalysis(config).run(df,                                base_dir / "03_churn_risk")
    df = TalkTimeAnalysis(config).run(df,                            base_dir / "04_talk_time")
    df = ActionItemAnalysis(config).run(df,                          base_dir / "05_action_items")
    CustomerTrajectoryAnalysis(config).run(df,                       base_dir / "06_customer_trajectory")

    _log.info("Pipeline complete. Charts saved under: %s", base_dir)
    for sub in sorted(base_dir.iterdir()):
        if sub.is_dir():
            count = sum(1 for f in sub.iterdir() if f.suffix == ".html")
            _log.info("  %s/  (%d chart%s)", sub.name, count, "s" if count != 1 else "")


if __name__ == "__main__":
    main()
