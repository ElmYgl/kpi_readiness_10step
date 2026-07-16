"""
KPI Parser — Plain Language Intake Tool
MIT License
Copyright (c) 2026 Elmer Yglesias

Purpose:
  Accept a plain-language KPI description, parse it into structured
  KPIInput fields, show them for human review, then hand off to
  kpi_readiness_10step.py for full 10-step validation.

  v1.1.0 adds Level 2A no-API prompt-export mode: when no API key is
  detected, the parser prints the exact prompt it would have sent to
  the LLM, waits for the user to paste the JSON response back, and
  continues the pipeline identically. Works with any AI environment —
  Claude.ai, ChatGPT, Copilot, Gemini, or a local model.

Pipeline:
  kpi_parser.py → parsed_kpi.json → kpi_readiness_10step.py → outputs

Entry levels:
  Level 1  — Core only:      kpi_readiness_10step.py (Python only)
  Level 2A — No-API mode:    kpi_parser.py, no key required  ★ NEW in v1.1.0
  Level 2  — With parser:    kpi_parser.py + ANTHROPIC_API_KEY
  Level 3  — Full pipeline:  all three tools + ANTHROPIC_API_KEY

Author: Elmer Yglesias
Website: elmerdata.ai
ORCID: 0009-0004-9538-2159
License: MIT License
GitHub: github.com/ElmYgl/kpi_readiness_10step
Presented at: AIR Forum 2026

Usage:
  python kpi_parser.py

Requirements:
  Level 2A (no-API mode): Python 3.8+ only. No packages, no key.
  Level 2  (API mode):    pip install anthropic
                          ANTHROPIC_API_KEY environment variable set.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# ============================================================================
# Version
# ============================================================================

__version__ = "1.1.0"
__release__ = "2026-07"

# ============================================================================
# Configuration
# ============================================================================

CLAUDE_MODEL = "claude-opus-4-5"
PARSED_OUTPUT_FILE = "parsed_kpi.json"
READINESS_SCRIPT = "kpi_readiness_10step.py"
PROMPT_EXPORT_FILE = "parser_prompt.txt"

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
# Mode Detection
# ============================================================================

def get_api_key() -> Optional[str]:
    """Return the Anthropic API key if set, else None."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    return key if key and key.strip() else None


def detect_mode() -> str:
    """
    Detect which parsing mode to use.

    Returns:
        "api"    — ANTHROPIC_API_KEY present, use Claude API (Level 2)
        "no_api" — no key detected, use prompt-export mode (Level 2A)
    """
    return "api" if get_api_key() else "no_api"


# ============================================================================
# Shared Prompt Construction
# ============================================================================

def build_full_prompt(description: str) -> str:
    """
    Build the complete self-contained prompt for no-API mode.
    Combines the system prompt and the user message so it can be pasted
    into any LLM as a single block.
    """
    return (
        PARSE_SYSTEM_PROMPT.strip()
        + "\n\n"
        + "Parse this KPI description into structured fields:\n\n"
        + description
    )


def strip_markdown_fences(raw: str) -> str:
    """Remove markdown code fences if the LLM wrapped its response in them."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Drop opening fence line
        lines = lines[1:]
        # Drop closing fence line if present
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return raw


# ============================================================================
# Level 2 — Claude API Mode
# ============================================================================

def parse_kpi_with_claude(description: str) -> dict:
    """
    Send KPI description to Claude API and return parsed fields as dict.
    Level 2 path — requires anthropic package and ANTHROPIC_API_KEY.
    """
    try:
        import anthropic
    except ImportError:
        print("\n✗ anthropic package not found.")
        print("  Install it with: pip install anthropic")
        print("  Or unset ANTHROPIC_API_KEY to use no-API mode (Level 2A).")
        sys.exit(1)

    api_key = get_api_key()
    client = anthropic.Anthropic(api_key=api_key)

    print("\n  Sending to Claude for parsing...")

    try:
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
    except anthropic.AuthenticationError:
        print("\n✗ Your ANTHROPIC_API_KEY was not accepted (authentication failed).")
        print("  Check that the key is valid and current at console.anthropic.com.")
        print("  You can also run without a key to use no-API mode (Level 2A),")
        print("  which works with Claude.ai, ChatGPT, Copilot, or any LLM.")
        sys.exit(1)
    except anthropic.RateLimitError:
        print("\n✗ Rate limit reached on your Anthropic account. Wait a moment and try again,")
        print("  or run without a key to use no-API mode (Level 2A).")
        sys.exit(1)
    except (anthropic.APIConnectionError, anthropic.APITimeoutError):
        print("\n✗ Could not reach the Anthropic API (network or connection issue).")
        print("  Check your internet connection and try again,")
        print("  or run without a key to use no-API mode (Level 2A).")
        sys.exit(1)
    except anthropic.APIStatusError as e:
        print(f"\n✗ The Anthropic API returned an error (status {e.status_code}).")
        print("  Try again in a moment, or run without a key to use no-API mode (Level 2A).")
        sys.exit(1)

    raw = strip_markdown_fences(message.content[0].text)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"\n✗ Could not parse Claude's response as JSON: {e}")
        print(f"Raw response:\n{raw}")
        sys.exit(1)


# ============================================================================
# Level 2A — No-API Prompt-Export Mode  ★ NEW in v1.1.0
# ============================================================================

def save_prompt_to_file(prompt: str, filepath: str = PROMPT_EXPORT_FILE) -> None:
    """Save the export prompt to a text file for convenience."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(prompt)
        print(f"  (Prompt also saved to {filepath})")
    except OSError:
        # Non-fatal — the prompt is already on screen
        pass


def read_pasted_response() -> str:
    """
    Read a multi-line pasted response from the console.
    The user signals completion by pressing Enter twice
    (two consecutive empty lines), or by EOF.
    """
    print("Paste the full JSON response below.")
    print("Press Enter twice when done.")
    print()
    lines: List[str] = []
    empty_count = 0
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "":
            empty_count += 1
            if empty_count >= 2 and lines:
                break
            # Preserve single blank lines inside the paste
            if lines:
                lines.append(line)
        else:
            empty_count = 0
            lines.append(line)
    return "\n".join(lines).strip()


def load_response_from_file() -> str:
    """Offer loading the LLM response from a saved .json or .txt file."""
    filepath = input("  File path: ").strip().strip('"').strip("'")
    if not filepath:
        return ""
    path = Path(filepath)
    if not path.exists():
        print(f"  File not found: {filepath}")
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as e:
        print(f"  Could not read file: {e}")
        return ""


def parse_kpi_no_api(description: str) -> dict:
    """
    Level 2A: No-API prompt-export mode.

    Prints the exact prompt the API path would have sent, waits for the
    user to paste the JSON response back, validates it, and returns the
    parsed fields. The rest of the pipeline runs identically to API mode.
    """
    prompt = build_full_prompt(description)

    print()
    print("No API key detected. Switching to no-API mode (Level 2A).")
    print()
    print("─" * 70)
    print("PROMPT — paste this into your AI environment")
    print("─" * 70)
    print(prompt)
    print("─" * 70)
    print()
    save_prompt_to_file(prompt)
    print()
    print("Paste the prompt above into Claude.ai, ChatGPT, Copilot, or any LLM.")
    print("Copy the full JSON response it returns.")
    print()

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        print("How would you like to provide the response?")
        print()
        print("  [1] Paste it here")
        print("  [2] Load it from a saved .json or .txt file")
        print()
        choice = ""
        while choice not in {"1", "2"}:
            choice = input("  Your choice (1/2): ").strip()

        print()
        if choice == "2":
            raw = load_response_from_file()
        else:
            raw = read_pasted_response()

        if not raw:
            print("  No response received.")
        else:
            raw = strip_markdown_fences(raw)
            try:
                parsed = json.loads(raw)
                if not isinstance(parsed, dict):
                    print("  Response parsed but is not a JSON object. Please paste the full JSON object.")
                else:
                    print("  ✓ Response parsed successfully.")
                    return parsed
            except json.JSONDecodeError as e:
                print(f"  ✗ Could not parse the response as JSON: {e}")
                print("  Tip: paste the complete response, starting with { and ending with }.")

        if attempt < max_attempts:
            print(f"\n  Let's try again ({attempt}/{max_attempts} attempts used).\n")

    print("\n✗ Could not obtain a valid JSON response after "
          f"{max_attempts} attempts. Exiting.")
    print("  Tip: the prompt is saved in parser_prompt.txt — you can run this")
    print("  tool again and load the LLM response from a file (option 2).")
    sys.exit(1)


# ============================================================================
# Unified Parse Entry Point
# ============================================================================

def parse_kpi(description: str) -> dict:
    """
    Parse a KPI description using whichever mode is available.
    API key present → Level 2 (Claude API).
    No API key     → Level 2A (prompt-export mode).
    """
    if detect_mode() == "api":
        return parse_kpi_with_claude(description)
    return parse_kpi_no_api(description)


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
    print("\n⚠ HUMAN REVIEW REQUIRED (governance guardrail)")
    print("  Do the parsed fields look correct?")
    print()
    print("  [Y] Yes — proceed with 10-step validation")
    print("  [N] No — exit and adjust your description")
    print()
    while True:
        response = input("  Your choice (Y/N): ").strip().upper()
        if response == "Y":
            return True
        elif response == "N":
            return False
        else:
            print("  Please enter Y or N.")


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
    Column headers are flexible — fuzzy matching handles real-world files.
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
    mode = detect_mode()
    mode_label = ("Level 2 — Claude API mode"
                  if mode == "api"
                  else "Level 2A — No-API prompt-export mode")

    print("\n" + "=" * 70)
    print("KPI PARSER — Plain Language Intake Tool")
    print(f"v{__version__} | {mode_label}")
    print("Starting Small with AI: Building Trustworthy KPI Dashboards")
    print("Elmer Yglesias | St. John's College | elmerdata.ai")
    print("AIR Forum 2026")
    print("=" * 70)

    # ── Step 1: Get KPI description ───────────────────────────────────────
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

    # ── Step 2: Ask how historical data will be provided ─────────────────
    data_option = ask_data_option()

    # ── Step 3: Handle data option ────────────────────────────────────────
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
        print("  The LLM will extract them automatically during parsing.")
    elif data_option == "3":
        print("\n  No historical data — kpi_improver.py will generate synthetic placeholder.")

    # ── Step 4: Parse (API mode or no-API mode) ───────────────────────────
    parsed = parse_kpi(description)

    # ── Step 5: Inject or clear historical data based on option ──────────
    if data_option == "2" and file_historical:
        parsed["historical_aggregates"] = file_historical
        print(f"\n  Injected {len(file_historical)} historical data points from file.")
    elif data_option == "3":
        parsed["historical_aggregates"] = []

    # ── Step 6: Human review (governance guardrail) ───────────────────────
    display_parsed_fields(parsed)
    confirmed = confirm_with_user()

    if not confirmed:
        print("\n  Exiting. Please refine your KPI description and try again.")
        print("  Tip: Add more detail about formula, source system, or audience.")
        sys.exit(0)

    # ── Step 7: Save parsed fields ────────────────────────────────────────
    save_parsed_kpi(parsed, PARSED_OUTPUT_FILE)

    # ── Step 8: Run 10-step validation ────────────────────────────────────
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
