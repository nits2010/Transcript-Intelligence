"""Configuration loader for the Transcript Intelligence pipeline.

Config data lives in config/pipeline.yaml.  This module provides:

  ConfigLoader — loads PipelineConfig from a local YAML file or a remote URL.
                 Call reload() to re-fetch without restarting the process.

  DEFAULT_CONFIG — pre-loaded at import time from the bundled YAML so that
                   all existing code (modules, notebook) works with zero changes.

Remote refresh example:
    from transcript_intelligence.config import config_loader
    config_loader.load_url("https://internal.example.com/configs/pipeline.yaml")
    new_cfg = config_loader.config  # now in effect for next pipeline run
"""

from __future__ import annotations

import urllib.request
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


# ---------------------------------------------------------------------------
# Builder: raw YAML dict -> PipelineConfig
# ---------------------------------------------------------------------------

def _build_config(data: dict[str, Any]) -> PipelineConfig:
    """Construct a PipelineConfig from a parsed YAML dict."""
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
    )


# ---------------------------------------------------------------------------
# ConfigLoader — local file or remote URL, with reload support
# ---------------------------------------------------------------------------

class ConfigLoader:
    """Loads and optionally reloads PipelineConfig from YAML.

    Supports:
      load_file(path)  — read from a local filesystem path
      load_url(url)    — fetch from an HTTP/HTTPS URL (no extra deps)
      reload()         — re-fetch from the last used source
      config           — property returning the current PipelineConfig
    """

    def __init__(self) -> None:
        self._config: PipelineConfig | None = None
        self._last_source: str | None = None  # path or URL as string

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

    def load_url(self, url: str) -> PipelineConfig:
        """Fetch config YAML from a remote URL and apply it immediately.

        Example:
            config_loader.load_url("https://internal.example.com/configs/pipeline.yaml")
        """
        with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310
            raw = yaml.safe_load(response.read().decode("utf-8"))
        self._config = _build_config(raw)
        self._last_source = url
        return self._config

    def reload(self) -> PipelineConfig:
        """Re-fetch config from the last used source (file or URL).

        Useful for hot-reloading in a long-running process without restart.
        """
        if self._last_source is None:
            raise RuntimeError("No source loaded yet. Call load_file() or load_url() first.")
        if self._last_source.startswith(("http://", "https://")):
            return self.load_url(self._last_source)
        return self.load_file(self._last_source)

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    @property
    def config(self) -> PipelineConfig:
        if self._config is None:
            raise RuntimeError("Config not loaded. Call load_file() or load_url() first.")
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
