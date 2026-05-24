# Transcript Intelligence — Pipeline Architecture

---

## High-Level Architecture

> What the system is: layers, modules, and data flow from raw files to output.

```mermaid
flowchart TD
    classDef cfgStyle   fill:#0f2942,stroke:#3b82f6,color:#e0f0ff,rx:6
    classDef ingestStyle fill:#0f3320,stroke:#22c55e,color:#dcfce7,rx:6
    classDef analysisStyle fill:#2d1457,stroke:#a855f7,color:#f3e8ff,rx:6
    classDef dataStyle  fill:#1c1c1c,stroke:#6b7280,color:#d1d5db,rx:6
    classDef outputStyle fill:#431407,stroke:#f97316,color:#ffedd5,rx:6

    RAW["Raw Dataset\n100 JSON folders per meeting\nmeeting-info · summary · transcript\nspeakers · events · speaker-meta"]:::dataStyle

    subgraph CONFIG["  Config Layer  "]
        YAML["config/pipeline.yaml"]:::cfgStyle
        PC["PipelineConfig\nfrozen dataclass"]:::cfgStyle
        YAML -->|"ConfigLoader\nload_file / load_url / reload()"| PC
    end

    subgraph INGEST["  Phase 1 · Ingestion  "]
        INP["ingest.py\nclassify_call_type()\nload_all_meetings()"]:::ingestStyle
    end

    DF["Full DataFrame\n100 rows × 18 columns\ncall_type · sentiment · churn signals\naction items · speakers · domains"]:::dataStyle

    subgraph ANALYSES["  Phases 2 – 7 · Analysis  "]
        direction LR
        P2["categorize.py"]:::analysisStyle
        P3["sentiment.py"]:::analysisStyle
        P4["churn_risk.py"]:::analysisStyle
        P5["talk_time.py"]:::analysisStyle
        P6["action_items.py"]:::analysisStyle
        P7["customer_trajectory.py"]:::analysisStyle
        P2 --> P3 --> P4 --> P5 --> P6 --> P7
    end

    subgraph OUTPUT["  Output  "]
        CHARTS["17 Plotly HTML Charts\noutput/charts/"]:::outputStyle
        NB["pipeline.ipynb\nNarrative Report"]:::outputStyle
        CHARTS --> NB
    end

    RAW --> INGEST
    PC -->|"injected into every step"| INGEST
    PC -->|"injected into every step"| ANALYSES
    INP --> DF
    DF --> ANALYSES
    ANALYSES --> CHARTS
```



---

## Execution Sequence

> How the system runs: who calls what, in what order, and the Template Method lifecycle inside each analysis step.

```mermaid
sequenceDiagram
    actor User
    participant R  as run_pipeline.py
    participant P  as pipeline.py · main()
    participant CL as ConfigLoader
    participant I  as ingest.py
    participant B  as BaseAnalysis subclass
    participant FS as output/charts/

    User ->> R  : python run_pipeline.py
    R    ->> P  : main()

    Note over P,CL: Config loaded once — shared by all steps
    P    ->> CL : load_file(config/pipeline.yaml)
    CL  -->> P  : PipelineConfig (frozen dataclass)

    P    ->> I  : load_all_meetings(config)
    Note over I : classify_call_type() runs per meeting<br/>Strategy chain: Support → Internal → External
    I   -->> P  : DataFrame  100 rows × 18 cols

    loop Each of 6 analysis phases
        P    ->> B  : AnalysisClass(config).run(df, charts_dir)
        Note over B : Template Method lifecycle
        B    ->> B  : _compute(df)  — derive columns, store state on self
        B    ->> B  : _summarize(df) — print findings to console
        B    ->> FS : _save_charts(df, charts_dir) — write .html files
        B   -->> P  : enriched DataFrame (passed to next step)
    end

    P   -->> User: Pipeline complete · 17 charts in output/charts/
```



---

## Design Patterns

> Why the system is structured this way: the four patterns, their abstract contracts, and their concrete implementations.

```mermaid
flowchart TD
    classDef abstractStyle fill:#1e3a5f,stroke:#60a5fa,color:#dbeafe,font-style:italic
    classDef concreteStyle fill:#14532d,stroke:#4ade80,color:#dcfce7
    classDef chainStyle    fill:#431407,stroke:#fb923c,color:#ffedd5
    classDef tmStyle       fill:#2d1457,stroke:#c084fc,color:#f3e8ff
    classDef ruleStyle     fill:#1c1c2e,stroke:#6b7280,color:#e5e7eb,font-size:12px

    subgraph S1["Strategy A · Call Type Classification  (ingest.py)"]
        direction TB
        CTS["«interface»\nCallTypeStrategy\n+ matches(title, emails) bool\n+ label str"]:::abstractStyle
        SUP["_SupportCaseStrategy\ntitle has 'Support Case' or 'Escalation'"]:::concreteStyle
        INT["_InternalMeetingStrategy\nno external email addresses"]:::concreteStyle
        EXT["_ExternalMeetingStrategy\ncatch-all — always true"]:::concreteStyle
        RULE1["Ordered chain · first match wins\nSupport → Internal → External"]:::ruleStyle
        CTS --> SUP & INT & EXT
        SUP & INT & EXT --> RULE1
    end

    subgraph S2["Strategy B · Topic Categorization  (categorize.py)"]
        direction TB
        CS["«interface»\nCategorizationStrategy\n+ score(topics, summary) dict"]:::abstractStyle
        KW["_TopicKeywordStrategy\nscores raw_topics list against\n8 categories × 80+ keywords"]:::concreteStyle
        SUM["_SummaryTextStrategy\nfallback — scans LLM summary text\nwhen keyword scores are empty"]:::concreteStyle
        RULE2["First non-empty score dict wins"]:::ruleStyle
        CS --> KW & SUM
        KW & SUM --> RULE2
    end

    subgraph COR["Chain of Responsibility · Churn Risk  (churn_risk.py)"]
        direction TB
        RF["«interface»\nRiskFactor\n+ contribution(meetings) float\n+ describe(meetings) str"]:::abstractStyle
        F1["_ChurnSignalFactor"]:::chainStyle
        F2["_NegativeMeetingFactor"]:::chainStyle
        F3["_TechnicalIssueFactor"]:::chainStyle
        F4["_BillingDisputeFactor"]:::chainStyle
        F5["_SupportEscalationFactor"]:::chainStyle
        F6["_SentimentAdjustmentFactor"]:::chainStyle
        RULE3["Total Score = Σ all contributions\nHIGH ≥ 10 · MEDIUM ≥ 5 · LOW < 5"]:::ruleStyle
        RF --> F1 & F2 & F3 & F4 & F5 & F6
        F1 & F2 & F3 & F4 & F5 & F6 --> RULE3
    end

    subgraph TM["Template Method · All Analysis Modules  (base.py)"]
        direction TB
        BA["«abstract»\nBaseAnalysis\n+ run(df, charts_dir)  ← fixed order\n# _compute(df)\n# _summarize(df)\n# _save_charts(df, dir)"]:::abstractStyle
        TCA["TopicCategorizationAnalysis\ncategorize.py"]:::tmStyle
        SA["SentimentAnalysis\nsentiment.py"]:::tmStyle
        CRA["ChurnRiskAnalysis\nchurn_risk.py"]:::tmStyle
        TTA["TalkTimeAnalysis\ntalk_time.py"]:::tmStyle
        AIA["ActionItemAnalysis\naction_items.py"]:::tmStyle
        CTA["CustomerTrajectoryAnalysis\ncustomer_trajectory.py"]:::tmStyle
        RULE4["Lifecycle order is immutable\nSubclasses override steps, never run()"]:::ruleStyle
        BA --> TCA & SA & CRA & TTA & AIA & CTA
        TCA & SA & CRA & TTA & AIA & CTA --> RULE4
    end
```



---

## Phase Reference

### Phase 0 — Configuration (`config.py` + `config/pipeline.yaml`)


| Component                      | Responsibility                              |
| ------------------------------ | ------------------------------------------- |
| `ConfigLoader.load_file(path)` | Read YAML from disk                         |
| `ConfigLoader.load_url(url)`   | Fetch YAML from HTTP/HTTPS (stdlib only)    |
| `ConfigLoader.reload()`        | Hot-reload from last source without restart |
| `PipelineConfig`               | Frozen dataclass — single source of truth   |
| `ChurnWeights`                 | 6 risk-factor weights                       |
| `ChurnTiers`                   | HIGH / MEDIUM score thresholds              |


**Externalised values:** `aegis_domain`, talk thresholds, follow-up window, trajectory minimums, trend delta, all churn weights, tier thresholds, Plotly color maps, sentiment label order, full 8-category topic taxonomy (~80 keywords).

---

### Phase 1 — Ingestion (`ingest.py`)


| Function                                    | Output                                             |
| ------------------------------------------- | -------------------------------------------------- |
| `classify_call_type(title, emails, config)` | `"customer_support"` / `"internal"` / `"external"` |
| `load_all_meetings(dataset_path, config)`   | DataFrame — 100 rows × 18 columns                  |


---

### Phase 2 — Topic Categorization (`categorize.py`)

8 canonical categories mapped across ~80 keywords. Charts: `categorization_distribution.html`

---

### Phase 3 — Sentiment Analysis (`sentiment.py`)

6 charts: Violin by call type · Weekly trend · Heatmap · Churn signal matrix · Score distribution · Call-type facet bar.

---

### Phase 4 — Churn Risk Scorecard (`churn_risk.py`)

Risk tiers: **HIGH** ≥ 10 · **MEDIUM** ≥ 5 · **LOW** < 5. Charts: scorecard bar · tier distribution.

---

### Phase 5 — Talk Time (`talk_time.py`)

`aegis_talk_ratio` vs benchmarks (support ≥ 0.65, external ≥ 0.60). Charts: benchmark bar · outlier scatter.

---

### Phase 6 — Action Items (`action_items.py`)

Parses `"Owner: task"` format. Detects orphaned meetings (action items with no follow-up within `followup_window_days`). Charts: burden bar · orphaned meetings.

---

### Phase 7 — Customer Trajectory (`customer_trajectory.py`)

Requires ≥ 3 meetings per customer. Trend delta ≥ 0.30 = Improving / ≤ -0.30 = Declining / else Stable. Charts: classification bar · per-customer line · heatmap.