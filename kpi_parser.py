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
    Environment variable ANTHROPIC_API_KEY must be set.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


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

    print("""
Paste or type your KPI description below.
Include as much detail as you have:
  - What is being measured
  - How it is calculated
  - Where the data comes from
  - Who owns/uses it
  - Any historical values (optional)
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

    # Step 1: Parse with Claude
    parsed = parse_kpi_with_claude(description)

    # Step 2: Human review (governance guardrail)
    display_parsed_fields(parsed)

    confirmed = confirm_with_user()

    if not confirmed:
        print("\n  Exiting. Please refine your KPI description and try again.")
        print("  Tip: Add more detail about formula, source system, or audience.")
        sys.exit(0)

    # Step 3: Save parsed fields
    save_parsed_kpi(parsed, PARSED_OUTPUT_FILE)

    # Step 4: Run 10-step validation
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
