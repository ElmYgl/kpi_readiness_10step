"""
KPI Parser — Plain Language Intake Tool

MIT License
Copyright (c) 2026 Elmer Yglesias

Purpose:
    Accept a plain-language KPI description, use the Claude API to parse it
    into structured KPIInput fields, show them for human review, then hand
    off to kpi_readiness_10step.py for full 10-step validation.

Pipeline:
    kpi_parser.py  →  parsed_kpi.json  →  kpi_readiness_10step.py  →  outputs

Author:  Elmer Yglesias
Website: elmerdata.ai
ORCID:   0009-0004-9538-2159
Presented at: AIR Forum 2026

Usage:
    python kpi_parser.py

Requirements:
    pip install anthropic
    pip install openpyxl  (optional, for Excel file upload)
    Environment variable ANTHROPIC_API_KEY must be set.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any


# ============================================================================
# Configuration
# ============================================================================

CLAUDE_MODEL = "claude-opus-4-5"
PARSED_OUTPUT_FILE = "parsed_kpi.json"
READINESS_SCRIPT = "kpi_readiness_10step.py"


# ============================================================================
# System Prompt for Parsing
# ============================================================================

PARSE_SYSTEM_PROMPT = """
You are an expert institutional research data analyst helping to extract
structured KPI metadata from plain-language descriptions.

Your task is to parse a KPI description and return a JSON object with
exactly these fields. Return ONLY valid JSON, no preamble, no markdown fences.

Fields to extract:
{
  "name": "Short KPI name (string)",
  "definition": "Full plain-language definition (string, aim for 50+ characters)",
  "formula": "Calculation formula using / or = operators (string)",
  "time_period": "Reporting cycle, e.g. Fall-to-fall annually (string)",
  "primary_source_system": "Main data source, e.g. Banner, IPEDS, SIS (string)",
  "secondary_source_systems": ["list", "of", "other", "systems"],
  "identifier_fields": ["fields", "used", "to", "join", "records"],
  "source_systems_in_join": ["systems", "involved", "in", "join"],
  "intended_audience": "Who uses this KPI, e.g. Board of Trustees (string)",
  "data_owner": "Office or person responsible, e.g. Registrar (string)",
  "data_steward": "Who maintains the data, e.g. Institutional Research (string)",
  "known_limitations": "Any caveats or limitations (string)",
  "bias_or_equity_risks": "Any equity or demographic risks (string)",
  "human_signoff_required": true,
  "historical_aggregates": [
    {"period": "Fall 2020", "value": 0.0},
    {"period": "Fall 2021", "value": 0.0}
  ]
}

Rules:
- historical_aggregates: if specific values are given, use them. If years are
  mentioned but no values, create placeholder entries with value 0.0 and note
  them as placeholders. If no history mentioned, return empty list [].
- human_signoff_required: always set to true.
- secondary_source_systems: empty list [] if none mentioned.
- identifier_fields: use ["student_id"] as default if a join is implied.
- source_systems_in_join: same as primary if no join needed, list both if join needed.
- bias_or_equity_risks: if not mentioned, use "Not specified - recommend documenting equity risks".
- known_limitations: if not mentioned, use "Not specified - recommend documenting limitations".
- Return ONLY the JSON object. No explanation. No markdown.
"""


# ============================================================================
# Claude API Call
# ============================================================================

def parse_kpi_with_claude(description: str) -> dict:
    """
    Send KPI description to Claude API and return parsed fields as dict.
    """
    try:
        import anthropic
    except ImportError:
        print("\n✗ anthropic package not found.")
        print("  Install it with: pip install anthropic")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n✗ ANTHROPIC_API_KEY environment variable not set.")
        print("  Set it in your User Variables (see setup instructions).")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print("\n⏳ Sending to Claude for parsing...")

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        system=PARSE_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Parse this KPI description into structured fields:\n\n{description}"
            }
        ]
    )

    raw = message.content[0].text.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1])

    try:
        parsed = json.loads(raw)
        return parsed
    except json.JSONDecodeError as e:
        print(f"\n✗ Could not parse Claude's response as JSON: {e}")
        print(f"Raw response:\n{raw}")
        sys.exit(1)


# ============================================================================
# Human Review Step
# ============================================================================

def display_parsed_fields(parsed: dict) -> None:
    """Display parsed fields clearly for human review."""
    print("\n" + "=" * 70)
    print("PARSED KPI FIELDS — PLEASE REVIEW BEFORE RUNNING VALIDATION")
    print("=" * 70)

    simple_fields = [
        "name", "definition", "formula", "time_period",
        "primary_source_system", "intended_audience",
        "data_owner", "data_steward", "known_limitations",
        "bias_or_equity_risks", "human_signoff_required"
    ]

    for field in simple_fields:
        value = parsed.get(field, "NOT FOUND")
        print(f"\n  {field}:")
        print(f"    {value}")

    list_fields = [
        "secondary_source_systems",
        "identifier_fields",
        "source_systems_in_join"
    ]

    for field in list_fields:
        value = parsed.get(field, [])
        print(f"\n  {field}:")
        if value:
            for item in value:
                print(f"    - {item}")
        else:
            print("    (none)")

    aggregates = parsed.get("historical_aggregates", [])
    print(f"\n  historical_aggregates: ({len(aggregates)} data points)")
    for agg in aggregates:
        print(f"    {agg.get('period')}: {agg.get('value')}")

    print("\n" + "=" * 70)


def confirm_with_user() -> bool:
    """Ask user to confirm parsed fields before proceeding."""
    print("\n⚠  HUMAN REVIEW REQUIRED (governance guardrail)")
    print("   Do the parsed fields look correct?")
    print()
    print("   [Y] Yes — proceed with 10-step validation")
    print("   [N] No  — exit and adjust your description")
    print()

    while True:
        response = input("   Your choice (Y/N): ").strip().upper()
        if response == "Y":
            return True
        elif response == "N":
            return False
        else:
            print("   Please enter Y or N.")


# ============================================================================
# Save Parsed KPI to JSON
# ============================================================================

def save_parsed_kpi(parsed: dict, filepath: str) -> None:
    """Save parsed KPI fields to JSON for handoff to readiness script."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2)
    print(f"\n✓ Parsed fields saved to {filepath}")


# ============================================================================
# Historical Data Intake — Three Options
# ============================================================================

def ask_data_option() -> str:
    """
    Ask user how they want to provide historical data.
    Returns '1', '2', or '3'.
    """
    print()
    print("=" * 70)
    print("HISTORICAL DATA")
    print("=" * 70)
    print()
    print("How would you like to provide historical data?")
    print()
    print("  [1] Include it in your KPI description (any format)")
    print("      e.g. Fall 2020: 88.5, Fall 2021: 89.0 ...")
    print("      or a table, narrative, or copy-paste from notes")
    print()
    print("  [2] Upload an Excel or CSV file")
    print("      Two columns expected: period and value")
    print("      e.g. retention_data.xlsx or historical.csv")
    print()
    print("  [3] No historical data available yet")
    print("      kpi_improver.py will generate synthetic placeholder data")
    print()

    while True:
        response = input("  Your choice (1/2/3): ").strip()
        if response in {"1", "2", "3"}:
            return response
        print("  Please enter 1, 2, or 3.")


def load_historical_from_excel(filepath: str) -> List[Dict[str, Any]]:
    """
    Load historical data from Excel file (.xlsx).
    Expects two columns: period (e.g. Fall 2020) and value (numeric).
    Column headers are flexible — fuzzy matching used.
    Requires: pip install openpyxl
    """
    try:
        import openpyxl
    except ImportError:
        print()
        print("  openpyxl not installed.")
        print("  Install with: pip install openpyxl")
        print("  Falling back to no historical data.")
        return []

    try:
        wb = openpyxl.load_workbook(filepath, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))

        if not rows:
            print("  Excel file appears empty.")
            return []

        # Find period and value columns — flexible header matching
        headers = [str(h).lower().strip() if h else "" for h in rows[0]]
        period_col = None
        value_col = None

        for i, h in enumerate(headers):
            if any(term in h for term in ["period", "year", "term", "date", "fall", "spring"]):
                period_col = i
            if any(term in h for term in ["value", "rate", "pct", "percent", "%", "count", "n"]):
                value_col = i

        # Fallback: assume first col = period, second = value
        if period_col is None:
            period_col = 0
        if value_col is None:
            value_col = 1

        results = []
        for row in rows[1:]:  # Skip header
            try:
                period = str(row[period_col]).strip()
                value = float(row[value_col])
                if period and period.lower() != "none":
                    results.append({"period": period, "value": value})
            except (TypeError, ValueError, IndexError):
                continue

        return results

    except Exception as e:
        print(f"  Could not read Excel file: {e}")
        return []


def load_historical_from_csv_file(filepath: str) -> List[Dict[str, Any]]:
    """
    Load historical data from CSV file.
    Expects two columns: period and value.
    Header row optional — auto-detected.
    """
    results = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            print("  CSV file appears empty.")
            return []

        # Detect if first row is a header
        start = 0
        try:
            float(rows[0][1])
        except (ValueError, IndexError):
            start = 1  # First row is a header

        for row in rows[start:]:
            try:
                period = str(row[0]).strip()
                value = float(row[1])
                if period:
                    results.append({"period": period, "value": value})
            except (ValueError, IndexError):
                continue

        return results

    except Exception as e:
        print(f"  Could not read CSV file: {e}")
        return []


def get_historical_data_from_file() -> List[Dict[str, Any]]:
    """
    Prompt user for file path and load historical data.
    Supports .xlsx and .csv files.
    """
    print()
    print("  Enter the full path to your Excel or CSV file.")
    print("  Example: C:\\Users\\eyglesias\\retention_data.xlsx")
    print("  Example: historical_rates.csv")
    print()

    filepath = input("  File path: ").strip().strip('"').strip("'")

    if not filepath:
        print("  No file path entered. Proceeding without historical data.")
        return []

    path = Path(filepath)

    if not path.exists():
        print(f"  File not found: {filepath}")
        print("  Proceeding without historical data.")
        return []

    suffix = path.suffix.lower()

    if suffix in {".xlsx", ".xls"}:
        data = load_historical_from_excel(filepath)
    elif suffix == ".csv":
        data = load_historical_from_csv_file(filepath)
    else:
        print(f"  Unsupported file type: {suffix}")
        print("  Supported types: .xlsx, .xls, .csv")
        print("  Proceeding without historical data.")
        return []

    if data:
        print(f"  Loaded {len(data)} data points from {path.name}:")
        for d in data:
            print(f"    {d['period']}: {d['value']}")
    else:
        print("  No valid data found in file.")

    return data


# ============================================================================
# Survey Comments Intake
# ============================================================================

def ask_survey_comments() -> tuple:
    """
    Ask user about survey comments in one clean three-option menu.
    Returns (mode, comments) where mode is 'real', 'sample', or 'skip'.
    """
    print()
    print("=" * 70)
    print("SURVEY COMMENTS")
    print("=" * 70)
    print()
    print("How would you like to handle student survey comment analysis?")
    print("This section appears in the kpi_improver.py HTML dashboard.")
    print()
    print("  [1] I have comments to provide — paste or upload")
    print("      LLM will analyze your actual survey data")
    print()
    print("  [2] Use sample data for demonstration")
    print("      Dashboard shows analysis of 10 built-in demo comments")
    print("      Clearly labeled as sample data — not for publication")
    print()
    print("  [3] Skip survey analysis entirely")
    print("      Dashboard will show: No survey data provided")
    print()

    while True:
        response = input("  Your choice (1/2/3): ").strip()
        if response == "1":
            break
        elif response == "2":
            print("\n  Using sample data — clearly labeled in dashboard.")
            return ("sample", [])
        elif response == "3":
            print("\n  Survey analysis will be skipped in dashboard.")
            return ("skip", [])
        else:
            print("  Please enter 1, 2, or 3.")

    # Option 1 — get comments
    print()
    print("  How would you like to provide your comments?")
    print()
    print("  [1] Paste comments (one per line, type END when done)")
    print("  [2] Upload a CSV file (one comment per row)")
    print()

    while True:
        sub = input("  Your choice (1/2): ").strip()
        if sub == "1":
            comments = get_survey_comments_from_input()
            if comments:
                return ("real", comments)
            else:
                print("  No comments entered — using sample data.")
                return ("sample", [])
        elif sub == "2":
            comments = get_survey_comments_from_file()
            if comments:
                return ("real", comments)
            else:
                print("  No comments loaded — using sample data.")
                return ("sample", [])
        else:
            print("  Please enter 1 or 2.")


def get_survey_comments_from_input() -> List[str]:
    """
    Accept survey comments pasted directly by the user.
    One comment per line, type END to finish.
    """
    print()
    print("  Paste or type your survey comments below.")
    print("  One comment per line.")
    print("  When done, type END on a new line and press Enter.")
    print()

    comments = []
    while True:
        try:
            line = input()
            if line.strip().upper() == "END":
                break
            if line.strip():
                comments.append(line.strip())
        except EOFError:
            break

    if comments:
        print(f"\n  {len(comments)} comments received.")
    else:
        print("  No comments entered.")

    return comments


def get_survey_comments_from_file() -> List[str]:
    """
    Load survey comments from a CSV file.
    Expects one comment per row, no header required.
    """
    print()
    print("  Enter the full path to your CSV file.")
    print("  Example: C:\\Users\\eyglesias\\survey_comments.csv")
    print("  One comment per row, no header needed.")
    print()

    filepath = input("  File path: ").strip().strip('"').strip("'")

    if not filepath:
        print("  No file path entered.")
        return []

    path = Path(filepath)

    if not path.exists():
        print(f"  File not found: {filepath}")
        return []

    if path.suffix.lower() != ".csv":
        print(f"  Unsupported file type: {path.suffix}")
        print("  Only .csv files are supported for survey comments.")
        return []

    comments = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():
                    comments.append(row[0].strip())

        if comments:
            print(f"  Loaded {len(comments)} comments from {path.name}")
        else:
            print("  No comments found in file.")

    except Exception as e:
        print(f"  Could not read file: {e}")

    return comments


def save_survey_comments(comments: List[str]) -> None:
    """Save survey comments to parsed_survey_comments.json for kpi_improver.py."""
    filepath = "parsed_survey_comments.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(comments, f, indent=2)
    print(f"\n✓ Survey comments saved to {filepath} ({len(comments)} comments)")


# ============================================================================
# Run kpi_readiness_10step.py
# ============================================================================

def run_readiness_check(parsed_json_path: str) -> None:
    """
    Hand off parsed JSON to kpi_readiness_10step.py via a small bridge script.
    Creates a temporary runner that loads the JSON and calls run_kpi_readiness().
    """

    bridge_script = f"""
import json
import sys
sys.path.insert(0, '.')
from kpi_readiness_10step import KPIInput, run_kpi_readiness, export_report_json, export_report_csv, plot_time_series, _print_report

with open('{parsed_json_path}', 'r') as f:
    data = json.load(f)

kpi = KPIInput(
    name=data['name'],
    definition=data['definition'],
    formula=data['formula'],
    time_period=data['time_period'],
    primary_source_system=data['primary_source_system'],
    secondary_source_systems=data.get('secondary_source_systems', []),
    identifier_fields=data.get('identifier_fields', []),
    source_systems_in_join=data.get('source_systems_in_join', []),
    intended_audience=data['intended_audience'],
    historical_aggregates=data.get('historical_aggregates', []),
    data_owner=data['data_owner'],
    data_steward=data['data_steward'],
    known_limitations=data['known_limitations'],
    bias_or_equity_risks=data['bias_or_equity_risks'],
    human_signoff_required=data.get('human_signoff_required', True)
)

report = run_kpi_readiness(kpi)
_print_report(report)

safe_name = kpi.name.replace(' ', '_').replace('/', '_')
export_report_json(report, f"{{safe_name}}_report.json")
export_report_csv(report, f"{{safe_name}}_summary.csv")

anomalies = report.step_4_quality.details.get('anomalies', [])
plot_time_series(kpi, anomalies, f"{{safe_name}}_chart.png")
"""

    bridge_path = "_kpi_bridge_runner.py"
    with open(bridge_path, "w", encoding="utf-8") as f:
        f.write(bridge_script)

    print("\n" + "=" * 70)
    print("RUNNING 10-STEP KPI READINESS VALIDATION")
    print("=" * 70)

    result = subprocess.run(
        [sys.executable, bridge_path],
        capture_output=False
    )

    # Clean up bridge script
    Path(bridge_path).unlink(missing_ok=True)

    if result.returncode != 0:
        print("\n✗ Validation script encountered an error.")
    else:
        print("\n✓ Validation complete.")


# ============================================================================
# Main Entry Point
# ============================================================================

def main() -> None:
    print("\n" + "=" * 70)
    print("KPI PARSER — Plain Language Intake Tool")
    print("Starting Small with AI: Building Trustworthy KPI Dashboards")
    print("Elmer Yglesias | St. John's College | elmerdata.ai")
    print("AIR Forum 2026")
    print("=" * 70)

    # ── Step 1: Get KPI description ───────────────────────────────────────────
    print("""
Paste or type your KPI description below.
Include as much detail as you have:
  - What is being measured
  - How it is calculated (formula)
  - Where the data comes from (source system)
  - Who owns and uses it (data owner, audience)
  - Any known limitations or equity considerations

When done, type END on a new line and press Enter.
""")

    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        except EOFError:
            break

    description = "\n".join(lines).strip()

    if not description:
        print("\n✗ No description entered. Exiting.")
        sys.exit(1)

    # ── Step 2: Ask how historical data will be provided ─────────────────────
    data_option = ask_data_option()

    # ── Step 3: Handle data option ────────────────────────────────────────────
    file_historical = []

    if data_option == "2":
        file_historical = get_historical_data_from_file()
        if file_historical:
            print(f"\n  Data loaded successfully — {len(file_historical)} points ready.")
        else:
            print("  No data loaded — will proceed without historical data.")
            data_option = "3"

    elif data_option == "1":
        print("\n  Include your historical values in the description above.")
        print("  Claude will extract them automatically during parsing.")

    elif data_option == "3":
        print("\n  No historical data — kpi_improver.py will generate synthetic placeholder.")

    # ── Step 3b: Ask about survey comments ──────────────────────────────────
    survey_mode, survey_comments = ask_survey_comments()

    if survey_mode == "real" and survey_comments:
        save_survey_comments({"mode": "real", "comments": survey_comments})
    elif survey_mode == "sample":
        save_survey_comments({"mode": "sample", "comments": []})
    elif survey_mode == "skip":
        save_survey_comments({"mode": "skip", "comments": []})

    # ── Step 4: Parse with Claude ─────────────────────────────────────────────
    parsed = parse_kpi_with_claude(description)

    # ── Step 5: Inject or clear historical data based on option ──────────────
    if data_option == "2" and file_historical:
        parsed["historical_aggregates"] = file_historical
        print(f"\n  Injected {len(file_historical)} historical data points from file.")
    elif data_option == "3":
        parsed["historical_aggregates"] = []

    # ── Step 5b: Save survey comments ────────────────────────────────────────
    if survey_comments:
        save_survey_comments(survey_comments)

    # ── Step 6: Human review (governance guardrail) ───────────────────────────
    display_parsed_fields(parsed)

    confirmed = confirm_with_user()

    if not confirmed:
        print("\n  Exiting. Please refine your KPI description and try again.")
        print("  Tip: Add more detail about formula, source system, or audience.")
        sys.exit(0)

    # ── Step 7: Save parsed fields ────────────────────────────────────────────
    save_parsed_kpi(parsed, PARSED_OUTPUT_FILE)

    # ── Step 8: Run 10-step validation ────────────────────────────────────────
    run_readiness_check(PARSED_OUTPUT_FILE)

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print("\nOutputs generated in your project folder:")
    print(f"  - {PARSED_OUTPUT_FILE} (parsed KPI fields)")
    kpi_name = parsed.get('name', 'KPI').replace(' ', '_').replace('/', '_')
    print(f"  - {kpi_name}_report.json (full 10-step report)")
    print(f"  - {kpi_name}_summary.csv (executive summary)")
    print(f"  - {kpi_name}_chart.png (time series chart)")
    print("\nCreated by: Elmer Yglesias")
    print("Website: elmerdata.ai")
    print("ORCID: 0009-0004-9538-2159")
    print("License: MIT License")
    print("Presented at: AIR Forum 2026")
    print("=" * 70)


if __name__ == "__main__":
    main()
