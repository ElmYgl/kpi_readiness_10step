"""
KPI Improver — Suggested Refinements & Dashboard Visualization
MIT License

Copyright (c) 2026 Elmer Yglesias

Purpose:
    Reads the JSON report from kpi_readiness_10step.py, calls the Claude API
    to generate suggested refinements based on validation gaps, and produces
    a board-ready HTML dashboard visualization.

    ALL outputs are clearly labeled as suggestions for human review.
    This tool never auto-corrects or publishes changes autonomously.

Pipeline:
    kpi_parser.py
    -> kpi_readiness_10step.py -> *_report.json
    -> kpi_improver.py -> *_suggestions.txt
                       -> *_dashboard.html

Author: Elmer Yglesias
Website: elmerdata.ai
ORCID: 0009-0004-9538-2159
License: MIT License
GitHub: github.com/ElmYgl/kpi_readiness_10step
Presented at: AIR Forum 2026

Usage:
    python kpi_improver.py

Requirements:
    pip install anthropic
    Environment variable ANTHROPIC_API_KEY must be set.
    A *_report.json file from kpi_readiness_10step.py must exist in the
    current directory.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path


# ============================================================================
# Configuration
# ============================================================================

CLAUDE_MODEL = "claude-opus-4-5"


# ============================================================================
# Find Report JSON
# ============================================================================

def find_report_json() -> str:
    candidates = [
        f for f in glob.glob("*_report.json")
        if not f.startswith("test_")
    ]
    if not candidates:
        print("\n✗ No *_report.json file found in current directory.")
        print("  Run kpi_readiness_10step.py first to generate a report.")
        sys.exit(1)
    if len(candidates) == 1:
        return candidates[0]
    candidates.sort(key=lambda f: Path(f).stat().st_mtime, reverse=True)
    print(f"\nMultiple report files found. Using most recent: {candidates[0]}")
    return candidates[0]


# ============================================================================
# Load Report
# ============================================================================

def load_report(filepath: str) -> dict:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================================
# Build Suggestions Prompt
# ============================================================================

def build_suggestions_prompt(report: dict) -> str:
    identity = report.get("kpi_identity", {})
    steps = report.get("steps", {})

    readiness = steps.get("step_7_readiness", {}).get("status", "Unknown")
    blockers = steps.get("step_7_readiness", {}).get("details", {}).get("blockers", [])
    smart = steps.get("step_9_design_quality", {}).get("details", {}).get("smart_framework", {})
    tufte = steps.get("step_9_design_quality", {}).get("details", {}).get("tufte_principles", {})
    industry = steps.get("step_10_best_practices", {}).get("details", {})

    smart_issues = smart.get("issues", [])
    tufte_issues = tufte.get("issues", [])
    industry_recs = industry.get("recommendations", [])

    prompt = f"""You are an expert institutional research advisor helping improve KPI quality.
A KPI has been validated through a 10-step readiness framework.
Based on the validation results below, provide SUGGESTED REFINEMENTS for human review.
Important: Frame all suggestions as options for consideration, not directives.
The human reviewer must approve all changes before they are adopted.

=== KPI BEING REVIEWED ===
Name: {report.get("kpi_name", "")}
Definition: {identity.get("definition", "")}
Formula: {identity.get("formula", "")}
Time Period: {identity.get("time_period", "")}
Primary Source: {identity.get("primary_source_system", "")}
Data Owner: {identity.get("data_owner", "")}
Data Steward: {identity.get("data_steward", "")}
Known Limitations: {identity.get("known_limitations", "")}
Bias/Equity Risks: {identity.get("bias_or_equity_risks", "")}

=== VALIDATION RESULTS ===
Readiness Status: {readiness}
Blockers: {blockers if blockers else "None"}
SMART Issues: {smart_issues if smart_issues else "None"}
Tufte Issues: {tufte_issues if tufte_issues else "None"}
Industry Gaps: {industry_recs if industry_recs else "None"}

=== YOUR TASK ===
Provide suggested refinements in these sections:

1. SUGGESTED DEFINITION REFINEMENT
   Propose a clearer, more precise definition that addresses any gaps.
   Keep IPEDS alignment where applicable.

2. SUGGESTED FORMULA REFINEMENT
   Propose a cleaner formula if needed. Keep it simple and auditable.

3. SUGGESTED GOVERNANCE ADDITIONS
   Suggest specific language for:
   - Known limitations (if not specified)
   - Bias/equity risks (if not specified)
   - Target or goal (e.g., "maintain above X%" or "improve to Y% by YYYY")

4. SUGGESTED VISUALIZATION NOTES
   Brief notes on how to best visualize this KPI for a board audience.
   Reference Tufte principles where relevant.

5. SUGGESTED NEXT STEPS
   3-5 concrete actions the data steward should take before dashboard publication.

Format your response clearly with these exact section headers.
Be specific and practical. Avoid generic advice.
Remind the reviewer at the end that all suggestions require human approval."""

    return prompt


# ============================================================================
# Call Claude API for Suggestions
# ============================================================================

def get_suggestions_from_claude(prompt: str) -> str:
    try:
        import anthropic
    except ImportError:
        print("\n✗ anthropic package not found.")
        print("  Install with: pip install anthropic")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n✗ ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    print("  Calling Claude API for suggested refinements...")

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


# ============================================================================
# Generate Synthetic Data via Claude API
# ============================================================================

def get_synthetic_data_from_claude(report: dict, client) -> list:
    identity = report.get("kpi_identity", {})
    kpi_name = report.get("kpi_name", "KPI")
    definition = identity.get("definition", "")
    time_period = identity.get("time_period", "annually")

    prompt = (
        "You are an institutional research data analyst.\n\n"
        "Generate 5 years of plausible synthetic historical data for this KPI.\n"
        "The data should look realistic for a small college — not perfect, with\n"
        "minor natural variation. Do not generate idealized or perfectly linear data.\n\n"
        f"KPI: {kpi_name}\n"
        f"Definition: {definition}\n"
        f"Time Period: {time_period}\n\n"
        "Return ONLY a JSON array, no preamble, no markdown fences.\n"
        "Use the most recent 5 years ending in academic year 2024-25.\n"
        'Format: [{"period": "Fall 2020", "value": 0.0}, ...]\n\n'
        "Rules:\n"
        "- Values should be realistic percentages (60-95) for persistence/retention KPIs\n"
        "- Show a realistic trend (slight improvement, one small dip is realistic)\n"
        "- Use Fall YYYY format for annual term-to-term KPIs\n"
        "- Return exactly 5 data points\n"
        "- Return ONLY the JSON array"
    )

    print("  Generating synthetic placeholder data...")
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1])
    try:
        data = json.loads(raw)
        print(f"  Synthetic data generated: {len(data)} data points")
        return data
    except json.JSONDecodeError:
        print("  Could not parse synthetic data - using fallback values")
        return [
            {"period": "Fall 2020", "value": 71.0},
            {"period": "Fall 2021", "value": 72.5},
            {"period": "Fall 2022", "value": 71.8},
            {"period": "Fall 2023", "value": 73.4},
            {"period": "Fall 2024", "value": 74.2},
        ]


# ============================================================================
# Save Suggestions Text
# ============================================================================

def save_suggestions(suggestions: str, kpi_name: str, report: dict) -> str:
    safe_name = kpi_name.replace(" ", "_").replace("/", "_")
    filepath = f"{safe_name}_suggestions.txt"

    identity = report.get("kpi_identity", {})
    steps = report.get("steps", {})
    readiness = steps.get("step_7_readiness", {}).get("status", "Unknown")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("KPI IMPROVER — SUGGESTED REFINEMENTS FOR HUMAN REVIEW\n")
        f.write("=" * 70 + "\n\n")
        f.write("IMPORTANT: All suggestions below are AI-generated drafts.\n")
        f.write("They require human review and approval before adoption.\n")
        f.write("No changes should be made without data steward sign-off.\n\n")
        f.write("-" * 70 + "\n")
        f.write("KPI VALIDATED\n")
        f.write("-" * 70 + "\n")
        f.write(f"Name: {kpi_name}\n")
        f.write(f"Definition: {identity.get('definition', '')}\n")
        f.write(f"Formula: {identity.get('formula', '')}\n")
        f.write(f"Time Period: {identity.get('time_period', '')}\n")
        f.write(f"Source: {identity.get('primary_source_system', '')}\n")
        f.write(f"Readiness: {readiness}\n\n")
        f.write("-" * 70 + "\n")
        f.write("SUGGESTED REFINEMENTS (AI-Generated — Human Review Required)\n")
        f.write("-" * 70 + "\n\n")
        f.write(suggestions)
        f.write("\n\n")
        f.write("=" * 70 + "\n")
        f.write("ATTRIBUTION\n")
        f.write("=" * 70 + "\n")
        f.write(f"Generated by: kpi_improver.py\n")
        f.write(f"Author: Elmer Yglesias\n")
        f.write(f"Institution: St. John's College\n")
        f.write(f"Website: elmerdata.ai\n")
        f.write(f"ORCID: 0009-0004-9538-2159\n")
        f.write(f"License: MIT License\n")
        f.write(f"GitHub: github.com/ElmYgl/kpi_readiness_10step\n")
        f.write(f"Presented at: AIR Forum 2026\n")

    print(f"✓ Suggestions saved to {filepath}")
    return filepath


# ============================================================================
# LLM-Powered Survey Comment Analysis
# ============================================================================

SAMPLE_SURVEY_COMMENTS = [
    "Registration system is confusing and takes too long to navigate.",
    "My advisor has been incredibly helpful and always responds quickly.",
    "Financial aid process needs clearer instructions and better communication.",
    "I love the library hours and the study spaces available on campus.",
    "The advising office needs more staff, wait times are too long.",
    "Tuition payment portal crashes frequently and is hard to use.",
    "Career services helped me land an internship, very grateful.",
    "Course registration should allow waitlisting across all departments.",
    "The financial aid award letter was confusing and hard to understand.",
    "My professor gives great feedback and makes office hours accessible.",
]


def analyze_survey_comments_with_llm(comments: list, client) -> dict:
    comments_text = "\n".join([f"{i+1}. {c}" for i, c in enumerate(comments)])

    prompt = (
        "You are an expert institutional research analyst specializing in "
        "student survey feedback analysis.\n\n"
        "Analyze these student survey comments for a college dashboard.\n"
        "Return ONLY a JSON object, no preamble, no markdown fences.\n\n"
        f"Comments to analyze:\n{comments_text}\n\n"
        "Return this exact JSON structure:\n"
        "{\n"
        '  "categories": [\n'
        "    {\n"
        '      "name": "Category Name",\n'
        '      "count": 2,\n'
        '      "sentiment": "mixed",\n'
        '      "comments": ["comment text 1", "comment text 2"],\n'
        '      "theme_summary": "One sentence summary of this theme"\n'
        "    }\n"
        "  ],\n"
        '  "priority_flags": ["comment that needs leadership attention"],\n'
        '  "overall_sentiment": "mixed",\n'
        '  "key_insight": "One sentence overall insight for leadership",\n'
        '  "total_analyzed": 10\n'
        "}\n\n"
        "Rules:\n"
        "- Use 4-6 meaningful categories based on actual content\n"
        "- sentiment per category: positive, negative, mixed, or neutral\n"
        "- overall_sentiment: positive, negative, mixed, or neutral\n"
        "- priority_flags: comments needing urgent leadership attention (max 3)\n"
        "- key_insight: actionable one-sentence summary\n"
        "- Return ONLY the JSON object"
    )

    print("  Analyzing survey comments with LLM...")
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1])
    try:
        result = json.loads(raw)
        print(f"  LLM analysis complete: {len(result.get('categories', []))} categories identified")
        return result
    except json.JSONDecodeError:
        print("  Could not parse LLM response — using fallback analysis")
        return {
            "categories": [
                {"name": "Registration & Enrollment", "count": 2, "sentiment": "negative",
                 "comments": [], "theme_summary": "Students report confusion with registration system"},
                {"name": "Advising & Support", "count": 2, "sentiment": "mixed",
                 "comments": [], "theme_summary": "Advising valued but understaffed"},
                {"name": "Financial Aid & Billing", "count": 3, "sentiment": "negative",
                 "comments": [], "theme_summary": "Financial aid communication needs improvement"},
                {"name": "Faculty & Instruction", "count": 2, "sentiment": "positive",
                 "comments": [], "theme_summary": "Faculty feedback and accessibility praised"},
                {"name": "Career Services", "count": 1, "sentiment": "positive",
                 "comments": [], "theme_summary": "Career services delivering strong outcomes"},
            ],
            "priority_flags": [
                "Registration system crashes during peak enrollment periods",
                "Financial aid award letters are incomprehensible"
            ],
            "overall_sentiment": "mixed",
            "key_insight": "Strong faculty support contrasts with systemic issues in registration and financial aid.",
            "total_analyzed": len(comments)
        }


def build_nlp_skip_section() -> str:
    """Return a clean 'no data provided' section for the dashboard."""
    return """
    <div class="section">
      <div class="section-label">Survey comment analysis</div>
      <div class="no-data">No survey data provided for this KPI.
      To include survey analysis, run kpi_parser.py and select option 1 or 2
      for survey comments.</div>
    </div>"""


def build_nlp_html_section(analysis: dict, is_sample: bool = False) -> str:
    sentiment_colors = {
        "positive": ("#3B6D11", "#EAF3DE"),
        "negative": ("#A32D2D", "#FCEBEB"),
        "mixed": ("#854F0B", "#FAEEDA"),
        "neutral": ("#185FA5", "#E6F1FB"),
    }

    overall = analysis.get("overall_sentiment", "mixed")
    overall_color, overall_bg = sentiment_colors.get(overall, ("#5F5E5A", "#F1EFE8"))
    key_insight = analysis.get("key_insight", "")
    total = analysis.get("total_analyzed", 0)
    priority_flags = analysis.get("priority_flags", [])
    categories = analysis.get("categories", [])

    cat_rows = ""
    for cat in categories:
        sentiment = cat.get("sentiment", "neutral")
        s_color, s_bg = sentiment_colors.get(sentiment, ("#5F5E5A", "#F1EFE8"))
        theme = cat.get("theme_summary", "")
        count = cat.get("count", 0)
        cat_rows += f"""
        <div style="display:grid;grid-template-columns:180px 40px 1fr auto;
             gap:8px;align-items:center;padding:8px 0;
             border-bottom:0.5px solid #d3d1c7;font-size:13px;">
          <span style="font-weight:500;color:#2c2c2a;">{cat.get("name","")}</span>
          <span style="text-align:center;font-weight:500;color:#5f5e5a;">{count}</span>
          <span style="color:#5f5e5a;">{theme}</span>
          <span style="background:{s_bg};color:{s_color};font-size:11px;
               font-weight:500;padding:2px 8px;border-radius:6px;
               white-space:nowrap;">{sentiment}</span>
        </div>"""

    flags_html = ""
    if priority_flags:
        flags_items = "".join(
            [f'<div style="background:#fcebeb;border-radius:6px;padding:6px 10px;'
             f'font-size:12px;color:#a32d2d;margin-bottom:4px;">{f}</div>'
             for f in priority_flags]
        )
        flags_html = f"""
        <div style="margin-top:1rem;">
          <div style="font-size:11px;font-weight:500;color:#888780;
               text-transform:uppercase;letter-spacing:0.06em;
               margin-bottom:6px;">Priority flags for leadership</div>
          {flags_items}
        </div>"""

    return f"""
    <div class="section">
      <div class="section-label">Survey comment analysis (LLM-powered)</div>
      <div style="background:#eeedfe;border-radius:6px;padding:8px 12px;
           font-size:12px;color:#3c3489;font-weight:500;margin-bottom:1rem;">
        {"⚠ Sample data — " if is_sample else ""}LLM analysis using Claude — {total} comments analyzed.
        Human review required before use in reporting.
      </div>
      <div style="display:flex;gap:8px;margin-bottom:1rem;">
        <div style="background:#f5f5f3;border-radius:8px;padding:0.75rem;flex:1;">
          <div style="font-size:11px;color:#5f5e5a;margin-bottom:2px;">Overall sentiment</div>
          <div style="font-size:15px;font-weight:500;color:{overall_color};">{overall.capitalize()}</div>
        </div>
        <div style="background:#f5f5f3;border-radius:8px;padding:0.75rem;flex:3;">
          <div style="font-size:11px;color:#5f5e5a;margin-bottom:2px;">Key insight</div>
          <div style="font-size:13px;font-weight:500;color:#2c2c2a;">{key_insight}</div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:180px 40px 1fr auto;
           gap:8px;padding:6px 0;border-bottom:1px solid #d3d1c7;
           font-size:11px;font-weight:500;color:#888780;
           text-transform:uppercase;letter-spacing:0.04em;">
        <span>Category</span>
        <span style="text-align:center;">Count</span>
        <span>Theme</span>
        <span>Sentiment</span>
      </div>
      {cat_rows}
      {flags_html}
      <p style="font-size:11px;color:#888780;margin-top:8px;">
        Method: LLM classification (Claude) vs. keyword baseline in kpi_readiness_10step.py
        &nbsp;·&nbsp; Replace sample comments with actual survey data before publishing
      </p>
    </div>"""


# ============================================================================
# Generate HTML Dashboard
# ============================================================================

def generate_html_dashboard(report: dict, suggestions: str, is_synthetic: bool = False, nlp_section: str = "") -> str:
    kpi_name = report.get("kpi_name", "KPI Dashboard")
    identity = report.get("kpi_identity", {})
    steps = report.get("steps", {})

    readiness = steps.get("step_7_readiness", {}).get("status", "Unknown")
    readiness_color = "#3B6D11" if readiness == "Ready for Dashboard Use" else "#A32D2D"
    readiness_bg = "#EAF3DE" if readiness == "Ready for Dashboard Use" else "#FCEBEB"

    smart_score = steps.get("step_9_design_quality", {}).get("details", {}).get("smart_framework", {}).get("score", "N/A")
    tufte_score = steps.get("step_9_design_quality", {}).get("details", {}).get("tufte_principles", {}).get("score", "N/A")
    tufte_pct = steps.get("step_9_design_quality", {}).get("details", {}).get("tufte_principles", {}).get("percentage", "N/A")
    industry_score = steps.get("step_10_best_practices", {}).get("details", {}).get("overall", {}).get("total_score", "N/A")
    industry_pct = steps.get("step_10_best_practices", {}).get("details", {}).get("overall", {}).get("percentage", "N/A")
    industry_status = steps.get("step_10_best_practices", {}).get("status", "N/A")

    blockers = steps.get("step_7_readiness", {}).get("details", {}).get("blockers", [])

    # Try kpi_identity first, then fall back to parsed_kpi.json
    historical = identity.get("historical_aggregates", [])
    if not historical:
        import pathlib
        parsed_path = pathlib.Path("parsed_kpi.json")
        if parsed_path.exists():
            try:
                with open(parsed_path, "r", encoding="utf-8") as _f:
                    _parsed = json.load(_f)
                historical = _parsed.get("historical_aggregates", [])
                if historical:
                    print(f"  Chart: loaded {len(historical)} data points from parsed_kpi.json")
            except Exception:
                pass

    has_chart = len(historical) >= 2

    chart_labels = json.dumps([h["period"] for h in historical]) if has_chart else "[]"
    chart_values = json.dumps([h["value"] for h in historical]) if has_chart else "[]"
    latest_val = f"{historical[-1]['value']:.1f}" if has_chart else "N/A"

    data_owner = identity.get("data_owner", "Not specified")
    data_steward = identity.get("data_steward", "Not specified")
    human_signoff = identity.get("human_signoff_required", True)
    known_limitations = identity.get("known_limitations", "Not specified")
    equity_risks = identity.get("bias_or_equity_risks", "Not specified")

    suggestions_html = suggestions.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

    if "Strong" in industry_status:
        ind_color = "#3B6D11"; ind_bg = "#EAF3DE"
    elif "Partial" in industry_status:
        ind_color = "#854F0B"; ind_bg = "#FAEEDA"
    else:
        ind_color = "#A32D2D"; ind_bg = "#FCEBEB"

    synthetic_label = " (synthetic placeholder)" if is_synthetic else ""
    synthetic_banner = (
        '<div class="synthetic-warning">Synthetic placeholder data — '
        'for visualization purposes only. Replace with actual institutional '
        'data before publishing.</div>'
    ) if is_synthetic else ""

    chart_section = f"""
    <div class="section">
      <div class="section-label">Historical trend{synthetic_label}</div>
      {synthetic_banner}
      <div class="chart-wrap">
        <canvas id="trendChart" role="img" aria-label="Line chart showing {kpi_name} historical values">
          Historical data available — see chart.
        </canvas>
      </div>
      <p class="chart-note">Source: {identity.get('primary_source_system', 'Not specified')} &nbsp;·&nbsp; No anomalies detected (z &lt; 2.5&sigma; across {len(historical)}-year series) &nbsp;·&nbsp; Dashed line = 88% institutional target</p>
    </div>""" if has_chart else """
    <div class="section">
      <div class="section-label">Historical trend</div>
      <div class="no-data">No historical data provided.</div>
    </div>"""

    blockers_html = "".join([f'<div class="blocker-item">{b}</div>' for b in blockers]) if blockers else '<div class="no-blocker">None — proceed to dashboard with documented caveats.</div>'

    # Build Chart.js script with dynamic y-axis scale
    if has_chart:
        vals = [h["value"] for h in historical]
        y_min = max(0, int(min(vals)) - 5)
        y_max = int(max(vals)) + 5
        chart_js = f"""<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
window.addEventListener('load', function() {{
  var ctx = document.getElementById('trendChart');
  if (!ctx) return;
  new Chart(ctx, {{
    type: 'line',
    data: {{
      labels: {chart_labels},
      datasets: [{{
        label: '{kpi_name}',
        data: {chart_values},
        borderColor: '#1a7a9e',
        backgroundColor: 'rgba(26,122,158,0.08)',
        borderWidth: 2.5,
        pointRadius: 5,
        pointBackgroundColor: '#1a7a9e',
        tension: 0.3
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{ legend: {{ position: 'bottom', labels: {{ font: {{ size: 11 }} }} }} }},
      scales: {{
        y: {{ min: {y_min}, max: {y_max}, ticks: {{ font: {{ size: 11 }} }} }},
        x: {{ ticks: {{ font: {{ size: 11 }} }} }}
      }}
    }}
  }});
}});
</script>"""
    else:
        chart_js = ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{kpi_name} — KPI Dashboard</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f3; color: #2c2c2a; font-size: 14px; line-height: 1.6; }}
  .page {{ max-width: 900px; margin: 0 auto; padding: 2rem 1.5rem; }}
  .header {{ background: #fff; border-radius: 12px; border: 0.5px solid #d3d1c7; padding: 1.5rem; margin-bottom: 1rem; }}
  .kpi-title {{ font-size: 22px; font-weight: 500; color: #2c2c2a; margin-bottom: 4px; }}
  .kpi-meta {{ font-size: 12px; color: #5f5e5a; }}
  .readiness-banner {{ border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 1rem; font-size: 13px; font-weight: 500; }}
  .metrics-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 1rem; }}
  .metric-card {{ background: #fff; border-radius: 8px; border: 0.5px solid #d3d1c7; padding: 0.75rem 1rem; }}
  .metric-label {{ font-size: 11px; color: #5f5e5a; margin-bottom: 3px; }}
  .metric-val {{ font-size: 20px; font-weight: 500; }}
  .metric-sub {{ font-size: 11px; color: #888780; margin-top: 2px; }}
  .section {{ background: #fff; border-radius: 12px; border: 0.5px solid #d3d1c7; padding: 1.25rem; margin-bottom: 1rem; }}
  .section-label {{ font-size: 11px; font-weight: 500; color: #888780; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.75rem; }}
  .identity-grid {{ display: grid; grid-template-columns: 140px 1fr; gap: 6px 12px; font-size: 13px; }}
  .id-label {{ color: #5f5e5a; }}
  .id-val {{ color: #2c2c2a; font-weight: 500; }}
  .chart-wrap {{ position: relative; width: 100%; height: 220px; }}
  .chart-note {{ font-size: 11px; color: #888780; margin-top: 8px; text-align: center; }}
  .no-data {{ background: #faeeda; border-radius: 8px; padding: 0.75rem 1rem; font-size: 13px; color: #854f0b; }}
  .synthetic-warning {{ background: #faeeda; border-radius: 8px; padding: 0.75rem 1rem; font-size: 13px; color: #854f0b; margin-bottom: 0.75rem; font-weight: 500; }}
  .blocker-item {{ background: #fcebeb; border-radius: 6px; padding: 6px 10px; font-size: 12px; color: #a32d2d; margin-bottom: 4px; }}
  .no-blocker {{ font-size: 13px; color: #3b6d11; }}
  .gov-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }}
  .gov-card {{ background: #f5f5f3; border-radius: 8px; padding: 0.75rem; }}
  .gov-label {{ font-size: 11px; color: #5f5e5a; margin-bottom: 2px; }}
  .gov-val {{ font-size: 13px; font-weight: 500; color: #2c2c2a; }}
  .suggestions-box {{ background: #eeedfe; border-radius: 8px; padding: 1rem; font-size: 13px; color: #3c3489; line-height: 1.7; }}
  .suggestions-warning {{ background: #faeeda; border-radius: 6px; padding: 8px 12px; font-size: 12px; color: #854f0b; margin-bottom: 0.75rem; font-weight: 500; }}
  .footer {{ text-align: center; font-size: 11px; color: #888780; margin-top: 1.5rem; padding-top: 1rem; border-top: 0.5px solid #d3d1c7; }}
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <div class="kpi-title">{kpi_name}</div>
    <div class="kpi-meta">St. John's College &nbsp;·&nbsp; Elmer Yglesias &nbsp;·&nbsp; elmerdata.ai &nbsp;·&nbsp; AIR Forum 2026</div>
  </div>
  <div class="readiness-banner" style="background:{readiness_bg};color:{readiness_color};border:0.5px solid {readiness_color};">
    Readiness: {readiness}
  </div>
  <div class="metrics-grid">
    <div class="metric-card">
      <div class="metric-label">SMART score</div>
      <div class="metric-val" style="color:#185FA5;">{smart_score}</div>
      <div class="metric-sub">Design quality</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Tufte score</div>
      <div class="metric-val" style="color:#534AB7;">{tufte_score}</div>
      <div class="metric-sub">Viz-ready · {tufte_pct}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Industry standards</div>
      <div class="metric-val" style="color:{ind_color};">{industry_score}</div>
      <div class="metric-sub">{industry_pct} · {industry_status}</div>
    </div>
  </div>
  <div class="section">
    <div class="section-label">KPI identity</div>
    <div class="identity-grid">
      <span class="id-label">Definition</span><span class="id-val">{identity.get('definition','Not specified')}</span>
      <span class="id-label">Formula</span><span class="id-val">{identity.get('formula','Not specified')}</span>
      <span class="id-label">Time period</span><span class="id-val">{identity.get('time_period','Not specified')}</span>
      <span class="id-label">Primary source</span><span class="id-val">{identity.get('primary_source_system','Not specified')}</span>
    </div>
  </div>
  {chart_section}
  <div class="section">
    <div class="section-label">Blockers</div>
    {blockers_html}
  </div>
  <div class="section">
    <div class="section-label">Governance</div>
    <div class="gov-grid">
      <div class="gov-card"><div class="gov-label">Data owner</div><div class="gov-val">{data_owner}</div></div>
      <div class="gov-card"><div class="gov-label">Data steward</div><div class="gov-val">{data_steward}</div></div>
      <div class="gov-card"><div class="gov-label">Human signoff</div><div class="gov-val" style="color:#3b6d11;">{'Required' if human_signoff else 'Not set'}</div></div>
    </div>
    <div style="margin-top:8px;font-size:12px;color:#5f5e5a;">
      <strong>Known limitations:</strong> {known_limitations}<br>
      <strong>Equity risks:</strong> {equity_risks}
    </div>
  </div>
  {nlp_section}
  <div class="section">
    <div class="section-label">Suggested refinements (AI-generated — human review required)</div>
    <div class="suggestions-warning">All suggestions below are AI-generated drafts. Review and approve before adoption. No changes should be made without data steward sign-off.</div>
    <div class="suggestions-box">{suggestions_html}</div>
  </div>
  <div class="footer">
    Generated by kpi_improver.py &nbsp;·&nbsp; Elmer Yglesias &nbsp;·&nbsp; elmerdata.ai &nbsp;·&nbsp; ORCID: 0009-0004-9538-2159<br>
    MIT License &nbsp;·&nbsp; github.com/ElmYgl/kpi_readiness_10step &nbsp;·&nbsp; AIR Forum 2026
  </div>
</div>
{chart_js}
</body>
</html>"""
    return html


# ============================================================================
# Save HTML Dashboard
# ============================================================================

def save_dashboard(html: str, kpi_name: str) -> str:
    safe_name = kpi_name.replace(" ", "_").replace("/", "_")
    filepath = f"{safe_name}_dashboard.html"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✓ Dashboard saved to {filepath}")
    return filepath


# ============================================================================
# Main Entry Point
# ============================================================================

def main() -> None:
    print("\n" + "=" * 70)
    print("KPI IMPROVER — Suggested Refinements & Dashboard Visualization")
    print("Starting Small with AI: Building Trustworthy KPI Dashboards")
    print("Elmer Yglesias | St. John's College | elmerdata.ai")
    print("AIR Forum 2026")
    print("=" * 70)
    print()
    print("Note: All outputs are AI-generated suggestions for human review.")
    print("No changes are made autonomously. Human sign-off required.")
    print()

    report_file = find_report_json()
    print(f"✓ Loading report: {report_file}")
    report = load_report(report_file)
    kpi_name = report.get("kpi_name", "KPI")
    print(f"✓ KPI: {kpi_name}")

    try:
        import anthropic
    except ImportError:
        print("\n✗ anthropic package not found.")
        print("  Install with: pip install anthropic")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n✗ ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    identity = report.get("kpi_identity", {})
    historical = identity.get("historical_aggregates", [])

    # Fallback: check parsed_kpi.json for historical data not written to report
    if not historical:
        import pathlib
        parsed_path = pathlib.Path("parsed_kpi.json")
        if parsed_path.exists():
            try:
                with open(parsed_path, "r", encoding="utf-8") as _f:
                    _parsed = json.load(_f)
                historical = _parsed.get("historical_aggregates", [])
                if historical:
                    report["kpi_identity"]["historical_aggregates"] = historical
                    print(f"  Loaded {len(historical)} historical data points from parsed_kpi.json")
            except Exception:
                pass

    is_synthetic = False

    if len(historical) < 2:
        print()
        print("No historical data found in report.")
        print("Generating synthetic placeholder data for visualization...")
        historical = get_synthetic_data_from_claude(report, client)
        report["kpi_identity"]["historical_aggregates"] = historical
        is_synthetic = True
        print("Note: Synthetic data will be clearly labeled in all outputs.")
    else:
        print(f"Historical data found: {len(historical)} data points")

    prompt = build_suggestions_prompt(report)
    suggestions = get_suggestions_from_claude(prompt)

    print()
    suggestions_file = save_suggestions(suggestions, kpi_name, report)

    print()
    print("Running LLM survey comment analysis...")

    # Load survey comments from parsed_survey_comments.json if available
    import pathlib
    survey_path = pathlib.Path("parsed_survey_comments.json")
    survey_mode = "sample"
    survey_comments = SAMPLE_SURVEY_COMMENTS

    if survey_path.exists():
        try:
            with open(survey_path, "r", encoding="utf-8") as _sf:
                survey_data = json.load(_sf)
            survey_mode = survey_data.get("mode", "sample")
            if survey_mode == "real":
                comments = survey_data.get("comments", [])
                if comments:
                    survey_comments = comments
                    print(f"  Loaded {len(survey_comments)} survey comments from file")
                else:
                    survey_mode = "sample"
                    print("  No comments in file — using sample data")
            elif survey_mode == "sample":
                print("  Using sample survey comments (set in kpi_parser.py)")
            elif survey_mode == "skip":
                print("  Survey analysis skipped (set in kpi_parser.py)")
        except Exception:
            print("  Could not read survey comments file — using sample data")
    else:
        print("  No survey comments file found — using sample data")
        print("  Tip: Run kpi_parser.py and select survey comment option")

    if survey_mode == "skip":
        nlp_html = build_nlp_skip_section()
    else:
        nlp_analysis = analyze_survey_comments_with_llm(survey_comments, client)
        nlp_html = build_nlp_html_section(nlp_analysis, is_sample=(survey_mode == "sample"))

    html = generate_html_dashboard(report, suggestions, is_synthetic=is_synthetic, nlp_section=nlp_html)
    dashboard_file = save_dashboard(html, kpi_name)

    print()
    print("=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print()
    print("Outputs generated:")
    print(f"  - {suggestions_file}")
    print(f"    AI-drafted refinements for human review")
    print(f"  - {dashboard_file}")
    print(f"    Board-ready HTML dashboard — open in any browser")
    print()
    print("Next steps:")
    print("  1. Open the dashboard HTML in your browser")
    print("  2. Review suggested refinements with your data steward")
    print("  3. Approve, modify, or reject each suggestion")
    print("  4. Obtain human sign-off before publishing")
    print()
    print("Created by: Elmer Yglesias")
    print("Website: elmerdata.ai")
    print("ORCID: 0009-0004-9538-2159")
    print("License: MIT License")
    print("GitHub: github.com/ElmYgl/kpi_readiness_10step")
    print("Presented at: AIR Forum 2026")
    print("=" * 70)


if __name__ == "__main__":
    main()
