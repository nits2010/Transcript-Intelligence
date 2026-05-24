# Transcript Intelligence — Take-Home Assignment

## Background
You're joining a team at a B2B enterprise SaaS company. The company captures call transcripts from across the organization:
* **Customer Support Calls:** Customers reaching out with operational or system issues.
* **External Calls:** Account managers speaking with clients regarding renewals, platform adoption, and feedback.
* **Internal Calls:** Engineering syncs, cross-team escalations, and product planning discussions.

The team is building a product called **Transcript Intelligence** — a tool designed to help diverse internal stakeholders (Support Leaders, Sales Managers, Product Managers, Engineering Leads) make better, data-driven decisions using these transcripts. 

You will receive approximately 100 sample transcripts across these three call types as your starting dataset. Your job is to explore the dataset, extract meaningful insights, and demonstrate your analytical and engineering approach.

---

## Deliverables & Core Tasks

### 1. Topic Modeling & Classification Pipeline
Build a pipeline that processes raw transcripts and categorizes them by topic or structural theme.
* **Requirements:** * Exhibit the final categories identified within the dataset.
  * Explain and justify your architectural approach (e.g., LLM-based zero-shot/few-shot classification, unsupervised clustering like K-Means/LDA, rule-based, or a hybrid mechanism).
  * Provide concrete examples of transcripts mapping to each identified category.
* **Focus:** We value your underlying engineering reasoning, trade-off analysis, and processing logic over just the raw output.

### 2. Sentiment Analysis & Trend Extraction
Generate a structured sentiment analysis across the different call types and identify operational trends.
* **Requirements:**
  * Do not just produce static visualizations or raw scores — synthesize what these trends indicate.
  * If anomalies, spikes, or patterns stand out (e.g., low sentiment in specific internal calls vs. high satisfaction in renewal calls), provide a clear hypothesis on what they indicate and why a business stakeholder should care.

### 3. Advanced Insight Generation (Open-Ended)
Explore beyond standard classification and sentiment. Think about the unique persona-based needs of different organizational stakeholders who would interact with a Transcript Intelligence tool.
* **Requirements:**
  * Brainstorm and document **at least 2–3 additional insight ideas** that add non-obvious value to the business.
  * *Options:* You can choose to fully implement functional prototypes of these insights, or simply describe them thoroughly alongside a strong product/technical justification for why they matter.