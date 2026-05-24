
# Transcript Intelligence — Session Summary

## What Was Built
An end-to-end meeting transcript analytics pipeline for AegisCloud's 100-meeting dataset (Feb–Apr 2026). The system processes three call types:
* `customer_support` (28 meetings)
* `external` (42 meetings)
* `internal` (30 meetings)

---

## Project Structure

```text
src/transcript_intelligence/
    ├── base.py                 # NEW — abstract interfaces for all design patterns
    ├── config.py               # NEW — YAML-backed ConfigLoader + PipelineConfig dataclass
    ├── ingest.py               # Strategy pattern for call type classification
    ├── categorize.py           # Strategy pattern for topic categorization + BaseAnalysis
    ├── sentiment.py            # BaseAnalysis subclass (6 charts)
    ├── churn_risk.py           # Chain of Responsibility for risk factors + BaseAnalysis
    ├── talk_time.py            # BaseAnalysis subclass
    ├── action_items.py         # BaseAnalysis subclass
    ├── customer_trajectory.py  # BaseAnalysis subclass
    ├── pipeline.py             # Orchestrator using class instances
    ├── __init__.py
    └── __main__.py
config/
    └── pipeline.yaml           # NEW — all hardcoded values externalized here
notebooks/
    └── pipeline.ipynb          # Narrative Jupyter notebook
docs/
    ├── task1_topic_categorization.md
    ├── task2_sentiment_analysis.md
    ├── bonus1_churn_risk.md
    ├── bonus2_talk_time.md
    ├── bonus3_action_items.md
    ├── bonus4_customer_trajectory.md
    └── build_plan/
        ├── MASTER_PROMPT.md
        └── build_plan.png      # Architecture diagram (shown in README)
run_pipeline.py                 # Root entry point (no install needed)
requirements.txt                # pandas, plotly, statsmodels, pyyaml, kaleido, jupyter
pyproject.toml
.vscode/
    └── settings.json           # markdown.preview.localFileSecurityPolicy: allow

```

---

## Design Patterns Applied

### Strategy — Call Type Classification (`ingest.py`)

Three concrete strategies tried in order:


$$\text{\_SupportCaseStrategy} \longrightarrow \text{\_InternalMeetingStrategy} \longrightarrow \text{\_ExternalMeetingStrategy}$$


This unified workflow completely replaces the original `if/elif` conditional ladder inside `classify_call_type()`.

### Strategy — Topic Categorization (`categorize.py`)

Evaluates through `_TopicKeywordStrategy` (matches raw topic tags) $\longrightarrow$ `_SummaryTextStrategy` (fallback scans LLM summary text). The first strategy that returns non-empty scores wins, completely replacing the rigid `if not scores:` fallback block.

### Chain of Responsibility — Churn Risk Scoring (`churn_risk.py`)

Utilizes six distinct `RiskFactor` classes:

1. `_ChurnSignalFactor`
2. `_NegativeMeetingFactor`
3. `_TechnicalIssueFactor`
4. `_BillingDisputeFactor`
5. `_SupportEscalationFactor`
6. `_SentimentAdjustmentFactor`

Each class cleanly encapsulates its weight configuration and a descriptive `describe()` label for logging top factors.

$$\text{Total Score} = \sum \text{all contributions}$$

New business risk dimensions can be injected into the chain without refactoring or touching existing components.

### Template Method — All Analysis Modules (`base.py` $\rightarrow$ all 6 modules)

`BaseAnalysis.run(df, charts_dir)` orchestrates an immutable lifecycle execution order:

$$\text{\_compute()} \longrightarrow \text{\_summarize()} \longrightarrow \text{\_save_charts()}$$

Intermediate computations are securely state-stored on `self` by `_compute()` for the subsequent reporting and exporting phases.

* **Concrete Implementations:** `TopicCategorizationAnalysis`, `SentimentAnalysis`, `ChurnRiskAnalysis`, `TalkTimeAnalysis`, `ActionItemAnalysis`, and `CustomerTrajectoryAnalysis`.
* **Backwards Compatibility:** Standard legacy `run_*` functions were retained as thin wrappers so existing notebooks function out-of-the-box without regressions.

### Config System (`config.py` + `config/pipeline.yaml`)

`PipelineConfig` is structured as a frozen dataclass with zero hardcoded Python fallbacks—all initial inputs are sourced purely from the externalized YAML configuration. The unified `ConfigLoader` natively supports:

* `load_file(path)` — Targets local disk YAML configurations.
* `load_url(url)` — Streamlines remote configuration fetching over HTTP/HTTPS (leveraging standard libraries exclusively, remaining entirely dependency-free).
* `reload()` — Triggers immediate configuration re-fetching from its last source origin to achieve hot-reloading mechanics without forcing service crashes or application reboots.

#### Scope Externalizations

Unified control fields moved cleanly out of execution layers include:

* `aegis_domain`
* `support_talk_threshold` (0.65) / `external_talk_threshold` (0.60)
* `followup_window_days` (7) / `min_trajectory_meetings` (3) / `trend_delta` (0.30)
* All 6 granular churn risk weights
* `HIGH/MEDIUM` risk tier categorization thresholds (10/5)
* System-wide Plotly color definitions & categorical sentiment layer ordering
* Full topic taxonomy definitions (8 categories mapping across ~80 discrete keywords)

#### Hot-Reload Usage Example

```python
from transcript_intelligence.config import config_loader

# Dynamically pull config state updates on-the-fly without stopping execution
config_loader.load_url("[https://your-server.com/configs/pipeline.yaml](https://your-server.com/configs/pipeline.yaml)")

```

---

## Bugs Fixed During Session

* **Missing Dependencies:** `statsmodels` was missing from environment profiles; dynamically appended to `requirements.txt`. Implemented structural `try/except ImportError` blocks so that OLS trendline rendering gracefully falls back rather than crashing operations.
* **Visualization Engine:** `plotly` and `kaleido` components were explicitly re-installed to secure systematic image rendering configurations.
* **Windows Console Encoding Crash:** Standard Unicode characters (like `→`) within primary terminal `print()` expressions generated decoding failures across standard Windows `cp1252` terminal layouts; safely sanitized down to ASCII standard `->`.
* **Invalid Plotly Schema:** Resolved an invocation failure where `px.colors.sequential.RdYlGn` was missing by properly targeting the diverging color schema route: `px.colors.diverging.RdYlGn`.
* **VS Code Preview Blocks:** Fixed an environment security restriction where standard markdown editors restricted showing engine graphics by initializing an explicit project rule inside `.vscode/settings.json` specifying: `"markdown.preview.localFileSecurityPolicy": "allow"`.
* **Image Reference Corruptions:** Rectified broken static absolute paths linking documentation assets (`/docs/build_plan/build_plan.png`) over to clean relative routing schemas (`docs/build_plan/build_plan.png`).
* **Jupyter Isolated Runtime Failures:** Fixed execution issues by explicitly binding a localized isolated notebook kernel mapped under `transcript-intelligence` via the execution command: `python -m ipykernel install --user`.

---

## README Sections Covered

1. **Problem Statement** (Sourced verbatim from the technical task overview)
2. **Solution** (An executive high-level single-sentence pipeline summary)
3. **Dataset** (Deconstructs the 6-file storage schema, essential parsing headers, and distribution splits across call categories)
4. **Build Plan** (Embedded blueprint map extracted out of `docs/build_plan/build_plan.png`)
5. **Project Structure** (Explains execution directories through an intuitive layout tree)
6. **Architecture & Design Decisions** (Clear evaluation mapping 5 core system architectural compromises alongside trade-off insights)
7. **Quick Start** (3 executable environments: native scripts, live editable source code packaging, or visual notebook workflows)
8. **Output Index** (An analytics matrix summarizing 17 functional Plotly generated data charts)
9. **Analyses Documentation** (A matrix catalog linking core parsing packages directly over to deeper written structural document files)

---

## Pipeline Output (Verified Working)

* Successfully exports **17 interactive Plotly HTML visualization graphs** written securely into `output/charts/` (and fully maintained under the local `.gitignore` ruleset).
* Execution of `python run_pipeline.py` systematically parses across all 100 enterprise sessions seamlessly with **zero compiler execution errors**, completing the full data lifecycle sweep end-to-end in approximately **10 seconds**.

```
