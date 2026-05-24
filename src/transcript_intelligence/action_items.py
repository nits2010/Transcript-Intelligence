"""Bonus 3: Action item owner analysis — burden distribution and follow-up gaps.

ActionItemAnalysis (Template Method): inherits BaseAnalysis; the follow-up
window is injected via PipelineConfig.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import plotly.express as px

from .base import BaseAnalysis
from .config import DEFAULT_CONFIG, PipelineConfig
from .ingest import AEGIS_DOMAIN

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHARTS_DIR = _PROJECT_ROOT / "output" / "charts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_owner(action_item: str) -> str:
    """Extract owner from 'PersonName: task description' format."""
    match = re.match(r"^([^:]+):", action_item.strip())
    return match.group(1).strip() if match else "Unknown"


def _email_to_name(email: str) -> str:
    local = email.split("@")[0]
    return " ".join(p.capitalize() for p in local.split("."))


# ---------------------------------------------------------------------------
# Template Method implementation
# ---------------------------------------------------------------------------

class ActionItemAnalysis(BaseAnalysis):
    """Bonus 3 — action item ownership and orphaned meeting detection."""

    def __init__(self, config: PipelineConfig = DEFAULT_CONFIG) -> None:
        self._config = config
        self._owner_counter: Counter = Counter()
        self._top_owners_df: pd.DataFrame = pd.DataFrame()
        self._orphaned_count: int = 0

    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        window = self._config.followup_window_days
        aegis_domain = self._config.aegis_domain

        owner_counter: Counter = Counter()
        meeting_owners: dict[str, list[str]] = {}
        all_aegis_names: set[str] = set()

        for _, row in df.iterrows():
            owners = [parse_owner(ai) for ai in row["action_items"]]
            meeting_owners[row["meeting_id"]] = owners
            for o in owners:
                owner_counter[o] += 1
            for e in row["all_emails"]:
                if e.endswith(aegis_domain):
                    all_aegis_names.add(_email_to_name(e))

        top_owners_df = pd.DataFrame(
            owner_counter.most_common(), columns=["owner", "action_item_count"]
        )
        top_owners_df["is_aegis"] = top_owners_df["owner"].isin(all_aegis_names)

        host_timeline: dict[str, list[dict]] = defaultdict(list)
        for _, row in df.iterrows():
            for e in row["all_emails"]:
                if e.endswith(aegis_domain):
                    name = _email_to_name(e)
                    host_timeline[name].append({
                        "meeting_id": row["meeting_id"],
                        "start_time": row["start_time"],
                        "raw_topics": {t.lower() for t in row["raw_topics"]},
                    })

        orphaned_ids: set[str] = set()
        for _, row in df.iterrows():
            mid = row["meeting_id"]
            owners = meeting_owners.get(mid, [])
            this_topics = {t.lower() for t in row["raw_topics"]}
            has_followup = False

            for owner in owners:
                if owner not in all_aegis_names:
                    continue
                for future_mtg in host_timeline.get(owner, []):
                    if future_mtg["meeting_id"] == mid:
                        continue
                    delta = (future_mtg["start_time"] - row["start_time"]).days
                    if 0 < delta <= window and (this_topics & future_mtg["raw_topics"]):
                        has_followup = True
                        break
                if has_followup:
                    break

            if not has_followup:
                orphaned_ids.add(mid)

        df = df.copy()
        df["has_followup"] = ~df["meeting_id"].isin(orphaned_ids)
        df["action_item_owners"] = df["meeting_id"].map(
            lambda mid: ", ".join(meeting_owners.get(mid, []))
        )

        self._owner_counter = owner_counter
        self._top_owners_df = top_owners_df
        self._orphaned_count = len(orphaned_ids)
        self._window = window
        return df

    def _summarize(self, df: pd.DataFrame) -> None:
        print("\n=== Bonus 3: Action Item Owner Analysis ===")
        print(f"Total unique action item owners: {len(self._owner_counter)}")
        print("\nTop 10 owners by action item count:")
        print(self._top_owners_df.head(10).to_string(index=False))
        print(
            f"\nOrphaned meetings (no topic-linked follow-up within {self._window}d): "
            f"{self._orphaned_count} of {len(df)}"
        )

    def _save_charts(self, df: pd.DataFrame, charts_dir: Path) -> None:
        top15 = self._top_owners_df.head(15).sort_values("action_item_count")
        top15 = top15.copy()
        top15["owner_type"] = top15["is_aegis"].map(
            {True: "Aegis Employee", False: "Customer / External"}
        )
        fig1 = px.bar(
            top15,
            x="action_item_count",
            y="owner",
            orientation="h",
            color="owner_type",
            color_discrete_map={
                "Aegis Employee": "#636EFA",
                "Customer / External": "#00CC96",
            },
            title="Top 15 Action Item Owners — Follow-up Burden",
            labels={"action_item_count": "# Action Items Assigned", "owner": "Person"},
            text="action_item_count",
        )
        fig1.update_traces(textposition="outside")
        fig1.update_layout(height=500, legend_title_text="Owner Type")
        out1 = charts_dir / "bonus3_action_item_owners.html"
        fig1.write_html(str(out1))
        print(f"Chart -> {out1}")

        followup_stats = (
            df.groupby(["call_type", "has_followup"])
            .size()
            .reset_index(name="count")
        )
        followup_stats["status"] = followup_stats["has_followup"].map(
            {True: "Has Follow-up", False: "Orphaned"}
        )
        fig2 = px.bar(
            followup_stats,
            x="call_type",
            y="count",
            color="status",
            barmode="stack",
            color_discrete_map={"Has Follow-up": "#00CC96", "Orphaned": "#EF553B"},
            title=f"Meeting Follow-up Rate by Call Type (within {self._window} days, same topic)",
            labels={"call_type": "Call Type", "count": "# Meetings", "status": "Status"},
            text="count",
            category_orders={"call_type": ["customer_support", "internal", "external"]},
        )
        fig2.update_traces(textposition="inside")
        fig2.update_layout(height=420)
        out2 = charts_dir / "bonus3_followup_rate.html"
        fig2.write_html(str(out2))
        print(f"Chart -> {out2}")

        aegis_owners = (
            self._top_owners_df[self._top_owners_df["is_aegis"]]
            .head(12)
            .sort_values("action_item_count")
        )
        fig3 = px.bar(
            aegis_owners,
            x="action_item_count",
            y="owner",
            orientation="h",
            color="action_item_count",
            color_continuous_scale="Blues",
            title="Aegis Employee Action Item Burden (cross-meeting total)",
            labels={"action_item_count": "Total Action Items", "owner": "Aegis Employee"},
            text="action_item_count",
        )
        fig3.update_traces(textposition="outside")
        fig3.update_layout(height=460, showlegend=False)
        out3 = charts_dir / "bonus3_aegis_burden.html"
        fig3.write_html(str(out3))
        print(f"Chart -> {out3}")


# ---------------------------------------------------------------------------
# Backward-compatible functional API (used by the notebook)
# ---------------------------------------------------------------------------

def run_action_item_analysis(
    df: pd.DataFrame,
    charts_dir: Path = DEFAULT_CHARTS_DIR,
    config: PipelineConfig = DEFAULT_CONFIG,
) -> pd.DataFrame:
    return ActionItemAnalysis(config).run(df, charts_dir)
