# kpi_readiness_10step

**10-step KPI readiness framework for institutional research. Pure Python core · optional Claude API for plain-language intake and AI-suggested refinements. MIT License.**

> *"The 10-step framework is the engine. AI is the power steering."*

Institutional KPI dashboards are only as trustworthy as the data and governance behind them. This pipeline validates any institutional KPI against 10 rigorous steps — spanning definition clarity, data quality, governance completeness, and visualization readiness — before it reaches a board dashboard. The core validation engine runs on pure Python with no external dependencies. No API key, no subscription, no vendor lock-in required.

Presented at **AIR Forum 2026**, Washington, D.C. · Poster 19 · May 27, 2026  
Piloted at **Norco College** (RCCD) · Presented at REACH Research Analytics Summit, Newport RI, April 2026

---

## The Problem

IR offices routinely deploy KPI dashboards before the underlying metrics have been validated for definition clarity, data quality, governance completeness, or alignment with industry standards. The result: dashboards that are visually polished but analytically unreliable.

At Norco College, applying this framework revealed:
- **10 of 13 KPIs** lacked a comparison benchmark or target
- **2 KPIs** showed significant trend changes with no annotation or explanation
- **All 13** were displayed on separate pages, obscuring cross-metric relationships

---

## Three-Module Pipeline

```
kpi_parser.py  ──►  kpi_readiness_10step.py  ──►  kpi_improver.py
─────────────       ───────────────────────       ────────────────
Plain-language      10-step validation            Refinements &
intake              Pure Python · No API          dashboard output
Claude API or       key required                  Claude API
no-API mode                                        
```

### Every pipeline run produces:

| File | Contents | Audience |
|------|----------|----------|
| `_report.json` | Full 10-step audit trail | IR staff, archival |
| `_summary.csv` | Executive one-pager | Directors, opens in Excel |
| `_chart.png` | Time-series with anomalies marked | IR staff, reports |
| `_dashboard.html` | Board-ready dashboard with Chart.js | Leadership, browser |
| `_suggestions.txt` | AI refinement candidates | Data steward |

---

## Architecture

The pipeline is three Python modules connected by JSON and output files.
Module 2 is the pure-Python validation engine and runs with no API key or
external dependencies. Modules 1 and 3 add AI-assisted intake and refinement,
and both offer a no-API path. Human review gates sit between parsing and
validation, and the Step 6 governance check is a hard gate inside the engine.

```
Module 1 — kpi_parser.py  (intake: Claude API or Level 2A no-API)
    parse_kpi() → detect_mode() → build_full_prompt()
    display_parsed_fields()
        │
        ▼
   [ Human review — confirm parsed fields before validation ]
        │
        ▼
    parsed_kpi.json
        │
        ▼
Module 2 — kpi_readiness_10step.py  (pure Python, no API, no dependencies)
    KPIInput (dataclass) → run_kpi_readiness()
    step_1_register … step_10_assess_best_practices()
        step_6_check_governance()  [ hard gate ]
        step_7_assess_readiness()  [ publish decision ]
    export_report_json() · export_report_csv() · plot_time_series()
        │
        ├──►  _report.json · _summary.csv
        └──►  _chart.png
        │
        ▼
Module 3 — kpi_improver.py  (optional)
    find_report_json() → load_report()
    get_suggestions_from_claude()
    analyze_survey_comments_with_llm()
    generate_html_dashboard()  →  _dashboard.html
    save_suggestions()         →  _suggestions.txt
```

### Modules

| Module | File | Role | Requires |
|--------|------|------|----------|
| 1 | `kpi_parser.py` | Plain-language intake, structured-field extraction, human review | Python only (Level 2A) or API key (Level 2) |
| 2 | `kpi_readiness_10step.py` | 10-step validation engine, report and chart output | Python 3.8+ only |
| 3 | `kpi_improver.py` | AI-suggested refinements, board-ready HTML dashboard, survey NLP | Python only (no-API) or API key |

### Key functions

`kpi_parser.py`
- `parse_kpi()` — unified entry point; routes to API mode or Level 2A no-API mode
- `detect_mode()` — selects the path based on whether an API key is present
- `build_full_prompt()` — assembles the self-contained prompt for no-API mode
- `display_parsed_fields()` — presents parsed fields for human confirmation

`kpi_readiness_10step.py`
- `KPIInput` — dataclass holding the KPI definition, sources, historical series, and governance fields
- `run_kpi_readiness()` — runs all ten steps and assembles the report
- `step_1_register` … `step_10_assess_best_practices()` — the ten validation steps
- `step_6_check_governance()` — hard gate; incomplete governance blocks readiness
- `step_7_assess_readiness()` — publish decision (Ready / Not Ready)
- `export_report_json()`, `export_report_csv()`, `plot_time_series()` — output writers
- `run_batch_readiness()` — validates multiple KPIs in one pass

`kpi_improver.py`
- `find_report_json()`, `load_report()` — locate and read the engine's report
- `get_suggestions_from_claude()` — AI-drafted refinement candidates
- `analyze_survey_comments_with_llm()` — optional NLP on survey comments
- `generate_html_dashboard()` — board-ready dashboard output
- `save_suggestions()` — writes the refinement file

### Data files

| File | Written by | Read by | Contents |
|------|-----------|---------|----------|
| `parsed_kpi.json` | Module 1 | Module 2 | Structured KPI fields after human review |
| `_report.json` | Module 2 | Module 3 | Full 10-step audit trail |
| `_summary.csv` | Module 2 | — | Executive one-page summary |
| `_chart.png` | Module 2 | — | Time-series chart with anomalies marked |
| `_dashboard.html` | Module 3 | — | Board-ready dashboard |
| `_suggestions.txt` | Module 3 | — | AI-drafted refinements for human review |
| `parser_prompt.txt` | Module 1 (Level 2A) | — | Exported prompt for pasting into any LLM |

### Governance gates

Human oversight is enforced at two points that AI cannot bypass: the review
of all parsed fields in Module 1 before validation runs, and the Step 6
governance check inside the engine, which blocks a Ready decision if data
owner, steward, limitations, equity risks, or human sign-off are missing.

---

## Installation

### Level 1 — Core Validation Only
**Requires: Python 3.8+ · No API key · No additional install**

```bash
# Download from GitHub, then:
python kpi_readiness_10step.py
```

Runs the demo immediately. Edit the `KPIInput` block in `main()` to validate your own KPI. Generates `_report.json` and `_summary.csv`.

---

### Level 2A — No-API Prompt-Export Mode ★ NEW
**Requires: Python 3.8+ · No API key · No additional install**

```bash
# Download from GitHub, then:
python kpi_parser.py
```

No API key? No problem. When no `ANTHROPIC_API_KEY` is detected, `kpi_parser.py` switches automatically to prompt-export mode:

```
No API key detected. Switching to no-API mode (Level 2A).

──────────────────────────────────────────────
PROMPT — paste this into your AI environment
──────────────────────────────────────────────
[full structured prompt printed here]
──────────────────────────────────────────────

Paste the prompt above into Claude.ai, ChatGPT, Copilot, or any LLM.
Copy the full JSON response it returns.
```

1. The parser prints the exact prompt it would have sent to the LLM, and saves a copy to `parser_prompt.txt`
2. Paste it into any AI environment you already have — Claude.ai, ChatGPT, Copilot, Gemini, or a local model
3. Copy the JSON response back into the console (Enter twice to finish), or load it from a saved file
4. The pipeline continues exactly as in API mode: human review of every parsed field, then automatic 10-step validation

Designed for offices where external AI API credits require procurement approval. Works in a terminal, Jupyter, Colab, or VS Code. The same governance guardrail applies — every parsed field is displayed for human confirmation before validation runs. AI never proceeds unsupervised, regardless of entry level.

---

### Level 2 — With Plain-Language Parser (Claude API)
**Requires: Python 3.8+ · Claude API key**

```bash
pip install anthropic

# Windows PowerShell — set API key (one-time):
[System.Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY', 'sk-...', 'User')

# Mac / Linux:
export ANTHROPIC_API_KEY='sk-...'

python kpi_parser.py
```

Paste any KPI description in plain language. Three historical data options: include in description, upload Excel/CSV, or no data yet. **Human review required before validation runs** — AI never proceeds unsupervised. If the API key is missing or invalid, the parser falls back cleanly to Level 2A rather than failing.

---

### Level 3 — Full Pipeline
**Requires: Python 3.8+ · Claude API key · All three modules**

```bash
pip install anthropic openpyxl matplotlib
python kpi_parser.py

# After validation completes:
python kpi_improver.py
```

`kpi_improver.py` auto-finds the latest `_report.json` and generates the board-ready HTML dashboard and AI-suggested refinements.

---

## Entry Levels at a Glance

| Level | Tools | Requires | Best for |
|-------|-------|----------|----------|
| 1 — Core only | `kpi_readiness_10step.py` | Python only | Any office, no AI budget |
| **2A — No-API mode ★ NEW** | `kpi_parser.py` + framework | Python only | Offices without approved API credits — works with any LLM |
| 2 — With parser | `kpi_parser.py` + framework | Python + API key | Remove technical friction |
| 3 — Full pipeline | All three tools | Python + API key | Complete AI-assisted experience |

---

## The 10-Step Framework

### Phase I · Define — *Describe the KPI precisely*

| Step | Name | What It Checks | Status |
|------|------|----------------|--------|
| 01 | Register Metadata | All required fields present and non-empty | Pass / Needs Attention |
| 02 | Validate Definition | Formula operator · Time period · Definition precision | Clear / Ambiguous |
| 03 | Entity Coherence | Cross-system join risk: Low / Moderate / High | Pass / Fail |

### Phase II · Validate — *Test for quality and governance*

| Step | Name | What It Checks | Status |
|------|------|----------------|--------|
| 04 | Data Quality | Outliers (z ≥ 2.5σ) · Step changes (≥25%) · Flags only, never auto-corrects | Pass / Needs Human Review |
| 05 | AI Use Assessment | Documents permitted techniques · Excludes black-box scoring | Pass (documents) |
| 06 | Governance Check | Owner · Steward · Limitations · Equity risks · Signoff **[Hard gate]** | Complete / Incomplete |
| 07 | Readiness Decision | Ready for Dashboard Use · or · Not Ready **[Publish gate]** | Ready / Not Ready |
| 08 | Summary Report | JSON audit trail · CSV executive summary · PNG time-series chart | Generated |

### Phase III · Enhance — *Advisory: design quality and standards*

| Step | Name | What It Checks | Status |
|------|------|----------------|--------|
| 09 | Design Quality | SMART (5 criteria) + Tufte visualization principles (5 criteria) | Advisory |
| 10 | Industry Standards | EDUCAUSE · AGB · NACUBO alignment · Score: X/9 | Advisory |

Steps 9–10 are advisory and do not affect the Step 7 readiness decision.

---

## Governance Architecture

Human oversight is embedded at every touchpoint — not bolted on afterward.

| Touchpoint | Oversight Mechanism |
|------------|---------------------|
| `kpi_parser.py` parsing | Human review of all parsed fields before validation runs |
| Step 4 anomaly detection | Every anomaly flagged — human must review before publishing |
| Step 6 governance check | Hard gate — incomplete governance blocks readiness |
| `kpi_improver.py` suggestions | All outputs labeled as drafts requiring human approval |
| Synthetic data | Clearly labeled as placeholder — not for publication |

### AI Governance — Step 05

| ✓ Permitted | ✗ Excluded |
|-------------|------------|
| Entity resolution across systems | Automated individual decisions |
| Anomaly detection on aggregates | Black-box scoring |
| NLP for survey comments | Auto-correction without review |
| Synthetic data — clearly labeled | Ungoverned AI output published |

The framework is LLM-agnostic. The Claude API calls in `kpi_parser.py` and `kpi_improver.py` can be replaced with any LLM API (OpenAI, Gemini, Azure OpenAI, local models) by updating the client initialization and model name. Level 2A takes this further: with no code changes at all, any analyst can run the full parser against any LLM by pasting the exported prompt.

---

## Demo Run — First-Year Retention Rate

```
Step 01  PASS       All metadata fields present
Step 02  CLEAR      Definition precise, ÷ operator confirmed
Step 03  LOW RISK   Single source IPEDS, no join required
Step 04  PASS       No anomalies — z < 2.5σ across 6-year series
Step 05  GOVERNED   NLP permitted for survey comments
Step 06  COMPLETE   Owner, steward, equity risks documented
Step 07  READY ✓    Ready for Dashboard Use
Step 08  GENERATED  report.json, summary.csv, chart.png
Step 09  5/5 SMART  All SMART criteria met
Step 09  4/5 TUFTE  80% — add comparison benchmark
Step 10  8/9        Strong Alignment — EDUCAUSE / AGB / NACUBO
```

*Tufte (Step 9.2) and AGB (Step 10) flag the same gap: missing comparison benchmark. Convergent finding — two independent frameworks, one recommendation.*

---

## Testing

```bash
python test_kpi_parser_v11.py
```

Runs 25 automated checks covering no-API activation, valid and markdown-fenced paste handling, malformed-paste retry and clean exit, backward-compatibility routing, prompt completeness, and clean API error handling. Requires Python 3.8+ only — no packages, no API key, no network access.

---

## Session Learning Outcomes

1. Identify which AI techniques are appropriate for KPI validation — and which must be excluded — with documented rationale
2. Apply the multi-entry-level pipeline to begin validating KPIs within your own office context
3. Implement a reusable 10-step validation framework aligned with EDUCAUSE, AGB, and NACUBO standards

---

## Industry Standards Referenced

- **EDUCAUSE** Data Governance Framework (2023)
- **AGB** Dashboard Metrics for Boards (2022)
- **NACUBO** KPI Framework (2024)
- **NIST** AI Risk Management Framework — AI RMF 1.0 (2023)
- **IPEDS** definitions (where applicable)

---

## Key References

- Ashby, H., & Yglesias, E. (2026, April). *From strategy to screens: Designing dashboards that support decision-making* [Presentation]. REACH Research Analytics Summit, Newport, RI.
- Doran, G. T. (1981). There's a S.M.A.R.T. way to write management's goals and objectives. *Management Review, 70*(11), 35–36.
- EDUCAUSE. (2024). *2024 EDUCAUSE AI landscape study.* EDUCAUSE.
- Few, S. (2006). *Information dashboard design.* O'Reilly.
- McGuire, L. (2017). Institutional data quality and the data integrity team. *AIR Professional Files, Summer 2017.* Association for Institutional Research.
- NIST. (2023). *Artificial intelligence risk management framework (AI RMF 1.0).* NIST AI 100-1. U.S. Department of Commerce.
- Swing, R. L., Jones, D., & Ross, L. E. (2016). *The AIR national survey of institutional research offices.* Association for Institutional Research.
- Teshome, S. (2025). Key performance indicators in higher education: A systematic review. *International Journal of Education, Management, and Technology.*
- Tufte, E. R. (2001). *The visual display of quantitative information* (2nd ed.). Graphics Press.
- Webber, K. (2023). AI in higher education: Implications for institutional research. *eAIR Newsletter.* Association for Institutional Research.

---

## Citation

```
Yglesias, E. (2026). Starting small with AI: Building trustworthy KPI dashboards.
Paper presented at AIR Forum 2026, Washington, D.C.
github.com/ElmYgl/kpi_readiness_10step
```

---

## About

**Elmer Yglesias** · Chief Data Officer, St. John's College  
[elmerdata.ai](https://elmerdata.ai) · [Elmer.Yglesias@sjc.edu](mailto:Elmer.Yglesias@sjc.edu)  
ORCID: [0009-0004-9538-2159](https://orcid.org/0009-0004-9538-2159)

Conducted with **Hayley Ashby, Ed.D.**, Norco College (RCCD)

---

**MIT License · Copyright © 2026 Elmer Yglesias · Free to use, modify, and distribute with attribution.**
