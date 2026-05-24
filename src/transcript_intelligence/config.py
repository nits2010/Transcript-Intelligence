"""Configuration loader for the Transcript Intelligence pipeline.

Config data lives in config/pipeline.yaml.  This module provides:

  ConfigLoader — loads PipelineConfig from a local YAML file.
                 Call reload() to re-fetch without restarting the process.

  DEFAULT_CONFIG — pre-loaded at import time from the bundled YAML.

"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config" / "pipeline.yaml"


# ---------------------------------------------------------------------------
# Config dataclasses (pure data — no hardcoded defaults)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LoggingConfig:
    level: str          # DEBUG | INFO | WARNING | ERROR
    format: str         # "text" | "json"
    file: str | None    # path for rotating file handler, or None for console-only
    max_bytes: int
    backup_count: int


@dataclass(frozen=True)
class ChurnWeights:
    churn_signal: float
    negative_meeting: float
    technical_issue: float
    billing_dispute: float
    support_escalation: float
    sentiment_adjustment: float


@dataclass(frozen=True)
class ChurnTiers:
    high: float
    medium: float


@dataclass(frozen=True)
class PipelineConfig:
    aegis_domain: str
    support_talk_threshold: float
    external_talk_threshold: float
    followup_window_days: int
    min_trajectory_meetings: int
    trend_delta: float
    churn_weights: ChurnWeights
    churn_tiers: ChurnTiers
    call_type_colors: dict[str, str]
    tier_colors: dict[str, str]
    trend_colors: dict[str, str]
    sentiment_label_order: tuple[str, ...]
    topic_taxonomy: dict[str, list[str]]
    logging_config: LoggingConfig


# ---------------------------------------------------------------------------
# Builder: raw YAML dict -> PipelineConfig
# ---------------------------------------------------------------------------

def _build_config(data: dict[str, Any]) -> PipelineConfig:
    """Construct a PipelineConfig from a parsed YAML dict."""
    log_data = data.get("logging", {})
    return PipelineConfig(
        aegis_domain=data["aegis_domain"],
        support_talk_threshold=float(data["support_talk_threshold"]),
        external_talk_threshold=float(data["external_talk_threshold"]),
        followup_window_days=int(data["followup_window_days"]),
        min_trajectory_meetings=int(data["min_trajectory_meetings"]),
        trend_delta=float(data["trend_delta"]),
        churn_weights=ChurnWeights(**{k: float(v) for k, v in data["churn_weights"].items()}),
        churn_tiers=ChurnTiers(**{k: float(v) for k, v in data["churn_tiers"].items()}),
        call_type_colors=dict(data["call_type_colors"]),
        tier_colors=dict(data["tier_colors"]),
        trend_colors=dict(data["trend_colors"]),
        sentiment_label_order=tuple(data["sentiment_label_order"]),
        topic_taxonomy={k: list(v) for k, v in data["topic_taxonomy"].items()},
        logging_config=LoggingConfig(
            level=str(log_data.get("level", "INFO")),
            format=str(log_data.get("format", "text")),
            file=log_data.get("file") or None,
            max_bytes=int(log_data.get("max_bytes", 10_485_760)),
            backup_count=int(log_data.get("backup_count", 3)),
        ),
    )


# ---------------------------------------------------------------------------
# ConfigLoader — local file, with reload support
# ---------------------------------------------------------------------------

class ConfigLoader:
    """Loads and optionally reloads PipelineConfig from YAML.

    Supports:
      load_file(path)  — read from a local filesystem path
      reload()         — re-fetch from the last used source
      config           — property returning the current PipelineConfig
    """

    def __init__(self) -> None:
        self._config: PipelineConfig | None = None
        self._last_source: str | None = None  # path as string

    # ------------------------------------------------------------------
    # Load methods
    # ------------------------------------------------------------------

    def load_file(self, path: Path | str = DEFAULT_CONFIG_PATH) -> PipelineConfig:
        """Load config from a local YAML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        self._config = _build_config(raw)
        self._last_source = str(path)
        return self._config

    def reload(self) -> PipelineConfig:
        """Re-fetch config from the last used source (file).

        Useful for hot-reloading in a long-running process without restart.
        """
        if self._last_source is None:
            raise RuntimeError("No source loaded yet. Call load_file() first.")
        return self.load_file(self._last_source)

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    @property
    def config(self) -> PipelineConfig:
        if self._config is None:
            raise RuntimeError("Config not loaded. Call load_file() first.")
        return self._config

    @property
    def source(self) -> str | None:
        """The path or URL of the currently loaded config."""
        return self._last_source


# ---------------------------------------------------------------------------
# Module-level singleton — pre-loaded from the bundled YAML
# ---------------------------------------------------------------------------

config_loader = ConfigLoader()
DEFAULT_CONFIG = config_loader.load_file(DEFAULT_CONFIG_PATH)
