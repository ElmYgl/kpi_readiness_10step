"""
KPI Readiness Routine (10-Step Version)

MIT License

Copyright (c) 2026 Elmer Yglesias

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

Purpose: Run a 10-step KPI validation workflow aligned to the AIR poster abstract:
"Starting Small with AI: Building Trustworthy KPI Dashboards"

Author: Elmer Yglesias
Institution: St. John's College
Website: elmerdata.ai
ORCID: 0009-0004-9538-2159
GitHub: github.com/ElmYgl/kpi_readiness_10step
Presented at: AIR Forum 2026

New 10-step structure:
Steps 1-8: Core validation (data quality, governance, readiness)
Step 9: KPI Design Quality (SMART framework)
Step 10: Industry Best Practice Alignment (EDUCAUSE/AGB/NACUBO)

Features:
- CSV input for KPI metadata
- IPEDS historical data loader
- JSON/CSV export
- Batch processing
- Visual time-series charts
- SMART framework assessment
- Industry standards validation

How to use:
1) Save as kpi_readiness_10step.py
2) Run: python kpi_readiness_10step.py
3) Follow prompts or customize main()

Design principles:
- No individual-level data required
- Flags issues, never auto-corrects
- Governance and transparency central
- Industry standards grounded in EDUCAUSE/AGB/NACUBO
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
from statistics import mean, pstdev
from pathlib import Path


# ============================================================================
# Configuration Constants
# ============================================================================

Z_SCORE_THRESHOLD = 2.5  # Standard deviations for outlier detection
STEP_CHANGE_THRESHOLD = 0.25  # 25% change threshold for step detection

# Step 9-10 can be disabled if desired
DEFAULT_INCLUDE_DESIGN_ASSESSMENT = True
DEFAULT_INCLUDE_BEST_PRACTICES = True


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class KPIInput:
    name: str
    definition: str
    formula: str
    time_period: str
    primary_source_system: str
    secondary_source_systems: List[str]
    intended_audience: str

    # Optional fields for steps 3 and 4
    identifier_fields: List[str]  # fields used to unify records across systems
    source_systems_in_join: List[str]  # systems that must join to calculate KPI

    # Historical aggregate series, for example [{"period":"Fall 2023","value":1234}, ...]
    historical_aggregates: List[Dict[str, Any]]

    # Governance fields
    data_owner: str
    data_steward: str
    known_limitations: str
    bias_or_equity_risks: str
    human_signoff_required: bool


@dataclass
class StepResult:
    status: str
    notes: str
    details: Dict[str, Any]


@dataclass
class KPIReadinessReport:
    kpi_name: str
    step_1_register: StepResult
    step_2_definition: StepResult
    step_3_entity: StepResult
    step_4_quality: StepResult
    step_5_ai: StepResult
    step_6_governance: StepResult
    step_7_readiness: StepResult
    step_8_summary: StepResult
    step_9_design_quality: StepResult  # NEW: SMART framework
    step_10_best_practices: StepResult  # NEW: Industry standards


# ============================================================================
# Input/Output Functions
# ============================================================================

def load_kpi_from_csv(filepath: str) -> KPIInput:
    """
    Load KPI metadata from CSV with standardized columns.
    
    Expected columns:
    - name, definition, formula, time_period, primary_source_system
    - secondary_source_systems (comma-separated)
    - identifier_fields (comma-separated)
    - source_systems_in_join (comma-separated)
    - intended_audience
    - data_owner, data_steward, known_limitations
    - bias_or_equity_risks, human_signoff_required
    
    Note: historical_aggregates should be loaded separately via load_ipeds_time_series
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        row = next(reader)  # Assume one KPI per file for now
        
        return KPIInput(
            name=row['name'],
            definition=row['definition'],
            formula=row['formula'],
            time_period=row['time_period'],
            primary_source_system=row['primary_source_system'],
            secondary_source_systems=[x.strip() for x in row.get('secondary_source_systems', '').split(',') if x.strip()],
            identifier_fields=[x.strip() for x in row.get('identifier_fields', '').split(',') if x.strip()],
            source_systems_in_join=[x.strip() for x in row.get('source_systems_in_join', '').split(',') if x.strip()],
            intended_audience=row['intended_audience'],
            historical_aggregates=[],  # Load separately with load_ipeds_time_series or load_historical_from_csv
            data_owner=row['data_owner'],
            data_steward=row['data_steward'],
            known_limitations=row['known_limitations'],
            bias_or_equity_risks=row['bias_or_equity_risks'],
            human_signoff_required=row['human_signoff_required'].lower() == 'true'
        )


def load_ipeds_time_series(
    filepath: str,
    unitid: int,
    year_column: str = 'YEAR',
    value_column: str = 'RET_PCF',
    period_format: str = 'Fall {year}'
) -> List[Dict[str, Any]]:
    """
    Load historical aggregates from IPEDS CSV.
    
    Args:
        filepath: Path to IPEDS CSV file
        unitid: Institution UNITID (e.g., 209542 for Reed, 121432 for Norco)
        year_column: Column name containing year
        value_column: Column name containing KPI value
        period_format: Format string for period labels
        
    Returns:
        List of {"period": "Fall 2023", "value": 89.5} dicts
    """
    results = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row_unitid = int(row.get('UNITID', 0))
                if row_unitid == unitid:
                    year = int(row[year_column])
                    value = float(row[value_column])
                    period = period_format.format(year=year)
                    results.append({"period": period, "value": value})
            except (ValueError, KeyError) as e:
                continue  # Skip malformed rows
    
    return sorted(results, key=lambda x: x['period'])


def load_historical_from_csv(filepath: str) -> List[Dict[str, Any]]:
    """
    Load historical aggregates from simple CSV with period,value columns.
    
    Expected format:
    period,value
    Fall 2020,88.5
    Fall 2021,89.0
    """
    results = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                results.append({
                    "period": row['period'],
                    "value": float(row['value'])
                })
            except (ValueError, KeyError):
                continue
    
    return results


def export_report_json(report: KPIReadinessReport, filepath: str) -> None:
    """Export full report as JSON for archival or dashboards."""
    
    def step_to_dict(step: StepResult) -> dict:
        return {
            "status": step.status,
            "notes": step.notes,
            "details": step.details
        }
    
    summary = report.step_8_summary.details.get("summary", {})
    sources = summary.get("sources", {})
    governance = summary.get("governance", {})

    output = {
        "kpi_name": report.kpi_name,
        "kpi_identity": {
            "definition": summary.get("definition", ""),
            "formula": summary.get("formula", ""),
            "time_period": summary.get("time_period", ""),
            "primary_source_system": sources.get("primary", ""),
            "secondary_source_systems": sources.get("secondary", []),
            "identifier_fields": sources.get("identifier_fields", []),
            "data_owner": governance.get("data_owner", ""),
            "data_steward": governance.get("data_steward", ""),
            "known_limitations": governance.get("known_limitations", ""),
            "bias_or_equity_risks": governance.get("bias_or_equity_risks", ""),
            "human_signoff_required": governance.get("human_signoff_required", True),
        },
        "timestamp": None,
        "author": "Elmer Yglesias",
        "institution": "St. John's College",
        "website": "elmerdata.ai",
        "orcid": "0009-0004-9538-2159",
        "license": "MIT License",
        "github": "github.com/ElmYgl/kpi_readiness_10step",
        "presented_at": "AIR Forum 2026",
        "steps": {
            "step_1_register": step_to_dict(report.step_1_register),
            "step_2_definition": step_to_dict(report.step_2_definition),
            "step_3_entity": step_to_dict(report.step_3_entity),
            "step_4_quality": step_to_dict(report.step_4_quality),
            "step_5_ai": step_to_dict(report.step_5_ai),
            "step_6_governance": step_to_dict(report.step_6_governance),
            "step_7_readiness": step_to_dict(report.step_7_readiness),
            "step_8_summary": step_to_dict(report.step_8_summary),
            "step_9_design_quality": step_to_dict(report.step_9_design_quality),
            "step_10_best_practices": step_to_dict(report.step_10_best_practices),
        }
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✓ Report exported to {filepath}")


def export_report_csv(report: KPIReadinessReport, filepath: str) -> None:
    """Export summary as CSV for spreadsheet analysis."""
    
    summary = report.step_8_summary.details.get('summary', {})
    sources = summary.get('sources', {})
    governance = summary.get('governance', {})
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # ── KPI Identity (what was validated) ──────────────────────────────
        writer.writerow(['KPI VALIDATED'])
        writer.writerow(['KPI Name', report.kpi_name])
        writer.writerow(['Definition', summary.get('definition', '')])
        writer.writerow(['Formula', summary.get('formula', '')])
        writer.writerow(['Time Period', summary.get('time_period', '')])
        writer.writerow(['Primary Source System', sources.get('primary', '')])
        secondary = sources.get('secondary', [])
        writer.writerow(['Secondary Source Systems', ', '.join(secondary) if secondary else 'None'])
        writer.writerow(['Intended Audience', governance.get('intended_audience', summary.get('intended_audience', ''))])
        writer.writerow([])

        # ── Readiness Results ───────────────────────────────────────────────
        writer.writerow(['READINESS RESULTS'])
        writer.writerow(['Readiness Status', summary.get('readiness_status', 'Unknown')])
        writer.writerow(['Definition Status', summary['risks'].get('definition_status', 'Unknown')])
        writer.writerow(['Entity Risk Level', summary['risks'].get('entity_risk_level', 'Unknown')])
        writer.writerow(['Anomalies Detected', summary['risks'].get('anomalies_detected', 'Unknown')])
        writer.writerow(['Governance Status', summary['risks'].get('governance_status', 'Unknown')])
        writer.writerow(['Design Quality', report.step_9_design_quality.status])
        writer.writerow(['Industry Standards', report.step_10_best_practices.status])
        writer.writerow([])

        # ── Blockers ────────────────────────────────────────────────────────
        writer.writerow(['BLOCKERS'])
        blockers = summary.get('blockers', [])
        if blockers:
            for blocker in blockers:
                writer.writerow(['', blocker])
        else:
            writer.writerow(['', 'None — proceed to dashboard with documented caveats'])
        writer.writerow([])

        # ── Governance ──────────────────────────────────────────────────────
        writer.writerow(['GOVERNANCE'])
        writer.writerow(['Data Owner', governance.get('data_owner', '')])
        writer.writerow(['Data Steward', governance.get('data_steward', '')])
        writer.writerow(['Known Limitations', governance.get('known_limitations', '')])
        writer.writerow(['Bias or Equity Risks', governance.get('bias_or_equity_risks', '')])
        writer.writerow(['Human Signoff Required', governance.get('human_signoff_required', False)])
        writer.writerow([])

        # ── Attribution ─────────────────────────────────────────────────────
        writer.writerow(['ATTRIBUTION'])
        writer.writerow(['Author', 'Elmer Yglesias'])
        writer.writerow(['Institution', "St. John's College"])
        writer.writerow(['Website', 'elmerdata.ai'])
        writer.writerow(['ORCID', '0009-0004-9538-2159'])
        writer.writerow(['License', 'MIT License'])
        writer.writerow(['GitHub', 'github.com/ElmYgl/kpi_readiness_10step'])
        writer.writerow(['Presented at', 'AIR Forum 2026'])
    
    print(f"✓ Summary exported to {filepath}")


def plot_time_series(kpi: KPIInput, anomalies: List[Dict], output_path: str = None) -> None:
    """
    Generate time-series chart of KPI over time with anomalies marked.
    Requires matplotlib.
    
    Args:
        kpi: KPIInput with historical_aggregates
        anomalies: List of anomaly dicts from step 4
        output_path: Where to save chart (default: {kpi_name}_chart.png)
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("⚠ matplotlib not installed, skipping chart generation")
        print("  Install with: pip install matplotlib")
        return
    
    if not kpi.historical_aggregates:
        print("⚠ No historical data to chart")
        return
    
    periods = [x['period'] for x in kpi.historical_aggregates]
    values = [x['value'] for x in kpi.historical_aggregates]
    
    plt.figure(figsize=(12, 6))
    plt.plot(periods, values, marker='o', linewidth=2, markersize=8, label='KPI Value')
    
    # Mark outliers
    outliers = [a for a in anomalies if a['type'] == 'Outlier']
    for anom in outliers:
        period = anom['period']
        if period in periods:
            idx = periods.index(period)
            plt.scatter(idx, values[idx], color='red', s=300, zorder=5, 
                       marker='X', label=f"Outlier (z={anom['z_score']})")
    
    # Mark step changes
    step_changes = [a for a in anomalies if a['type'] == 'StepChange']
    for anom in step_changes:
        to_period = anom['to_period']
        if to_period in periods:
            idx = periods.index(to_period)
            plt.axvline(x=idx, color='orange', linestyle='--', alpha=0.7, linewidth=2,
                       label=f"Step Change ({anom['pct_change']}%)")
    
    plt.title(f"{kpi.name} - Time Series with Anomaly Flags", fontsize=16, fontweight='bold')
    plt.xlabel("Period", fontsize=12)
    plt.ylabel("Value", fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, alpha=0.3, linestyle='--')
    plt.legend(loc='best')
    plt.tight_layout()
    
    if output_path is None:
        safe_name = kpi.name.replace(' ', '_').replace('/', '_')
        output_path = f"{safe_name}_chart.png"
    
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Chart saved: {output_path}")


# ============================================================================
# Batch Processing Functions
# ============================================================================

def run_batch_readiness(kpis: List[KPIInput], **kwargs) -> List[KPIReadinessReport]:
    """Run readiness checks on multiple KPIs."""
    return [run_kpi_readiness(kpi, **kwargs) for kpi in kpis]


def print_batch_summary(reports: List[KPIReadinessReport]) -> None:
    """Print executive summary of batch results."""
    print("\n" + "=" * 70)
    print("BATCH READINESS SUMMARY")
    print("=" * 70)
    
    ready = [r for r in reports if r.step_7_readiness.status == "Ready for Dashboard Use"]
    blocked = [r for r in reports if r.step_7_readiness.status == "Not Ready"]
    
    print(f"\nTotal KPIs assessed: {len(reports)}")
    print(f"✓ Ready for dashboard: {len(ready)}")
    print(f"⚠ Blocked (need review): {len(blocked)}")
    
    if ready:
        print("\n✓ Ready KPIs:")
        for r in ready:
            print(f"  - {r.kpi_name}")
    
    if blocked:
        print("\n⚠ Blocked KPIs:")
        for r in blocked:
            blockers = r.step_7_readiness.details.get('blockers', [])
            print(f"  - {r.kpi_name}")
            for blocker in blockers:
                print(f"    • {blocker}")


def export_batch_to_csv(reports: List[KPIReadinessReport], filepath: str) -> None:
    """Export batch summary as CSV."""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'KPI Name',
            'Readiness Status',
            'Definition Status',
            'Entity Risk',
            'Anomalies Detected',
            'Governance Status',
            'Design Quality',
            'Industry Standards',
            'Blockers'
        ])
        
        # Rows
        for report in reports:
            summary = report.step_8_summary.details.get('summary', {})
            writer.writerow([
                report.kpi_name,
                summary.get('readiness_status', 'Unknown'),
                summary['risks'].get('definition_status', 'Unknown'),
                summary['risks'].get('entity_risk_level', 'Unknown'),
                summary['risks'].get('anomalies_detected', 'Unknown'),
                summary['risks'].get('governance_status', 'Unknown'),
                report.step_9_design_quality.status,
                report.step_10_best_practices.status,
                '; '.join(summary.get('blockers', []))
            ])
    
    print(f"\n✓ Batch summary exported to {filepath}")


# ============================================================================
# Core Validation Functions (Steps 1-8)
# ============================================================================

def _is_blank(s: Optional[str]) -> bool:
    return s is None or str(s).strip() == ""


def step_1_register(kpi: KPIInput) -> StepResult:
    missing = []
    for field_name, value in asdict(kpi).items():
        if field_name in {"historical_aggregates"}:
            continue
        if isinstance(value, list) and len(value) == 0:
            missing.append(field_name)
        elif isinstance(value, str) and _is_blank(value):
            missing.append(field_name)

    status = "Pass" if len(missing) == 0 else "Needs Attention"
    notes = "All required metadata present." if status == "Pass" else "Missing required fields."
    return StepResult(status=status, notes=notes, details={"missing_fields": missing})


def step_2_validate_definition(kpi: KPIInput) -> StepResult:
    issues = []

    # Minimal heuristic checks, designed for lean offices
    if len(kpi.definition.strip()) < 20:
        issues.append("Definition looks too short to be precise.")
    if "=" not in kpi.formula and "÷" not in kpi.formula and "/" not in kpi.formula:
        issues.append("Formula does not visibly show a calculation operator.")
    if _is_blank(kpi.time_period):
        issues.append("Time period is missing.")

    status = "Clear" if len(issues) == 0 else "Ambiguous"
    notes = (
        "Definition appears stable and usable."
        if status == "Clear"
        else "Definition needs clarification before downstream checks."
    )
    return StepResult(
        status=status,
        notes=notes,
        details={
            "issues": issues,
            "follow_up_prompts": [
                "State numerator in plain language.",
                "State denominator in plain language.",
                "State the exact census date or reporting window.",
                "Name the single source of record for each component.",
            ]
            if status != "Clear"
            else [],
        },
    )


def step_3_check_entity_coherence(kpi: KPIInput) -> StepResult:
    joins_required = len(kpi.source_systems_in_join) > 1
    issues = []

    if joins_required and len(kpi.identifier_fields) == 0:
        issues.append("Cross system join required but identifier fields are not listed.")
    if joins_required and len(set(kpi.source_systems_in_join)) != len(kpi.source_systems_in_join):
        issues.append("Duplicate system names in join list, confirm intended join path.")

    risk = "Low"
    if joins_required:
        risk = "Moderate" if len(issues) == 0 else "High"

    recommendation = "Entity resolution required: Yes" if joins_required else "Entity resolution required: No"

    status = "Pass" if risk in {"Low", "Moderate"} else "Fail"
    notes = (
        "Entity coherence looks manageable."
        if status == "Pass"
        else "Entity coherence risk is high, resolve before dashboard use."
    )

    return StepResult(
        status=status,
        notes=notes,
        details={
            "joins_required": joins_required,
            "entity_risk_level": risk,
            "identifier_fields": kpi.identifier_fields,
            "recommendation": recommendation,
            "issues": issues,
        },
    )


def _analyze_series(values: List[float]) -> Dict[str, Any]:
    if len(values) == 0:
        return {"count": 0}
    if len(values) == 1:
        return {"count": 1, "mean": values[0], "stdev": 0.0}

    m = mean(values)
    s = pstdev(values)
    return {"count": len(values), "mean": m, "stdev": s}


def step_4_screen_data_quality(kpi: KPIInput) -> StepResult:
    anomalies: List[Dict[str, Any]] = []
    series = kpi.historical_aggregates or []

    # Extract numeric values
    values: List[Tuple[str, float]] = []
    for row in series:
        try:
            period = str(row.get("period", "Unknown"))
            value = float(row.get("value"))
            values.append((period, value))
        except Exception:
            anomalies.append(
                {
                    "type": "NonNumeric",
                    "period": row.get("period", "Unknown"),
                    "value": row.get("value"),
                    "note": "Value is missing or non numeric.",
                }
            )

    only_vals = [v for _, v in values]
    stats = _analyze_series(only_vals)

    # Outlier detection
    if stats.get("count", 0) >= 3 and stats.get("stdev", 0.0) > 0.0:
        m = stats["mean"]
        s = stats["stdev"]
        for period, v in values:
            z = abs((v - m) / s) if s > 0 else 0.0
            if z >= Z_SCORE_THRESHOLD:
                anomalies.append(
                    {"type": "Outlier", "period": period, "value": v, "z_score": round(z, 2), "note": "Flag for review."}
                )

    # Step change check
    for i in range(1, len(values)):
        p0, v0 = values[i - 1]
        p1, v1 = values[i]
        if v0 == 0:
            continue
        pct = (v1 - v0) / v0
        if abs(pct) >= STEP_CHANGE_THRESHOLD:
            anomalies.append(
                {
                    "type": "StepChange",
                    "from_period": p0,
                    "to_period": p1,
                    "from_value": v0,
                    "to_value": v1,
                    "pct_change": round(pct * 100, 1),
                    "note": "Confirm if institutional event explains change.",
                }
            )

    detected = "Yes" if len(anomalies) > 0 else "No"
    status = "Pass" if detected == "No" else "Needs Human Review"
    notes = "No anomalies detected in aggregates." if detected == "No" else "Anomalies detected, require human review."

    return StepResult(
        status=status,
        notes=notes,
        details={
            "anomalies_detected": detected,
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "stats": stats,
            "rule_notes": {
                "outlier_rule": f"z score at or above {Z_SCORE_THRESHOLD}",
                "step_change_rule": f"absolute percent change at or above {int(STEP_CHANGE_THRESHOLD * 100)} percent",
                "human_review": "Required for every flagged anomaly",
            },
        },
    )


def step_5_assess_ai_use(kpi: KPIInput) -> StepResult:
    permitted = []
    excluded = []
    rationale = []

    joins_required = len(kpi.source_systems_in_join) > 1
    has_survey_comments = "survey" in (kpi.definition.lower() + " " + kpi.known_limitations.lower())

    if joins_required:
        permitted.append("Entity resolution to unify records across systems")
        rationale.append("Multiple systems require reliable record linkage.")

    permitted.append("Anomaly detection to flag potential data errors in aggregates")
    rationale.append("Aggregate screening supports faster dashboards, without auto correction.")

    if has_survey_comments:
        permitted.append("Natural language processing to organize open ended survey comments")
        rationale.append("NLP can structure comments into themes for review.")

    excluded.extend(
        [
            "Automated decisions affecting individuals",
            "Black box scoring without documentation",
            "Auto correction of records without human review",
        ]
    )

    status = "Pass"
    notes = "AI techniques remain limited, explainable, and governed."

    return StepResult(
        status=status,
        notes=notes,
        details={
            "permitted_ai_techniques": permitted,
            "excluded_ai_techniques": excluded,
            "rationale": rationale,
        },
    )


def step_6_check_governance(kpi: KPIInput) -> StepResult:
    missing = []
    if _is_blank(kpi.data_owner):
        missing.append("data_owner")
    if _is_blank(kpi.data_steward):
        missing.append("data_steward")
    if _is_blank(kpi.known_limitations):
        missing.append("known_limitations")
    if _is_blank(kpi.bias_or_equity_risks):
        missing.append("bias_or_equity_risks")
    if kpi.human_signoff_required is not True:
        missing.append("human_signoff_required must be True")

    status = "Complete" if len(missing) == 0 else "Incomplete"
    notes = "Governance elements present." if status == "Complete" else "Governance gaps, fill before publishing."

    return StepResult(
        status=status,
        notes=notes,
        details={
            "missing_elements": missing,
            "guardrails": [
                "Human oversight required",
                "Bias checks documented",
                "Transparent documentation and change log",
            ],
        },
    )


def step_7_assess_readiness(
    kpi: KPIInput,
    s2: StepResult,
    s3: StepResult,
    s4: StepResult,
    s6: StepResult,
) -> StepResult:
    """
    Assess readiness based on steps 1-6 only.
    Steps 9-10 provide quality insights but don't block publishing.
    """
    blockers = []

    if s2.status != "Clear":
        blockers.append("Definition ambiguous")
    if s3.status == "Fail":
        blockers.append("Entity coherence high risk")
    if s4.status == "Needs Human Review":
        blockers.append("Data anomalies require review")
    if s6.status != "Complete":
        blockers.append("Governance incomplete")

    if len(blockers) == 0:
        status = "Ready for Dashboard Use"
        notes = "KPI meets definition, quality, and governance requirements."
    else:
        status = "Not Ready"
        notes = "KPI blocked by one or more gaps."

    return StepResult(
        status=status,
        notes=notes,
        details={
            "blockers": blockers,
            "next_actions": [
                "Clarify definition and formula",
                "Confirm sources of record and join keys",
                "Review anomalies with domain owners",
                "Complete governance fields and require sign off",
            ]
            if status == "Not Ready"
            else ["Proceed to dashboard with documented caveats"],
            "note": "Steps 9-10 provide quality insights but don't affect readiness status"
        },
    )


def step_8_generate_summary(kpi: KPIInput, readiness: StepResult, ai: StepResult, 
                            quality: StepResult, entity: StepResult, gov: StepResult, 
                            definition: StepResult) -> StepResult:
    summary = {
        "kpi_name": kpi.name,
        "definition": kpi.definition,
        "formula": kpi.formula,
        "time_period": kpi.time_period,
        "sources": {
            "primary": kpi.primary_source_system,
            "secondary": kpi.secondary_source_systems,
            "systems_in_join": kpi.source_systems_in_join,
            "identifier_fields": kpi.identifier_fields,
        },
        "risks": {
            "definition_status": definition.status,
            "entity_risk_level": entity.details.get("entity_risk_level"),
            "anomalies_detected": quality.details.get("anomalies_detected"),
            "governance_status": gov.status,
        },
        "ai_guidance": {
            "permitted": ai.details.get("permitted_ai_techniques"),
            "excluded": ai.details.get("excluded_ai_techniques"),
        },
        "governance": {
            "data_owner": kpi.data_owner,
            "data_steward": kpi.data_steward,
            "known_limitations": kpi.known_limitations,
            "bias_or_equity_risks": kpi.bias_or_equity_risks,
            "human_signoff_required": kpi.human_signoff_required,
        },
        "readiness_status": readiness.status,
        "readiness_notes": readiness.notes,
        "blockers": readiness.details.get("blockers", []),
    }

    status = "Generated"
    notes = "One page readiness summary prepared."
    return StepResult(status=status, notes=notes, details={"summary": summary})


# ============================================================================
# Step 9: KPI Design Quality Assessment (SMART Framework)
# ============================================================================

def step_9_assess_design_quality(kpi: KPIInput) -> StepResult:
    """
    Assess KPI design quality using SMART framework + Tufte visualization principles.
    Focus on internal metric construction and visualization readiness.
    """
    smart_checks = {}
    strengths = []
    issues = []
    
    # S - Specific
    if len(kpi.definition) > 50:
        smart_checks["Specific"] = True
        strengths.append("Clear population and outcome defined")
    else:
        smart_checks["Specific"] = False
        issues.append("Definition could be more precise (currently < 50 characters)")
    
    # M - Measurable
    if any(op in kpi.formula for op in ["/", "÷", "="]):
        smart_checks["Measurable"] = True
        strengths.append("Formula with clear calculation operator")
    else:
        smart_checks["Measurable"] = False
        issues.append("Formula lacks clear calculation operator")
    
    # A - Achievable (check historical variance if available)
    if kpi.historical_aggregates and len(kpi.historical_aggregates) >= 3:
        values = [x['value'] for x in kpi.historical_aggregates]
        variance = max(values) - min(values)
        if variance < max(values) * 0.3:  # Less than 30% range
            smart_checks["Achievable"] = True
            strengths.append(f"Historical data shows stable, realistic range (variance: {variance:.1f})")
        else:
            smart_checks["Achievable"] = False
            issues.append("High variance suggests volatility or data quality concerns")
    else:
        smart_checks["Achievable"] = None  # Can't assess without data
    
    # R - Relevant
    if kpi.intended_audience and len(kpi.intended_audience) > 0:
        smart_checks["Relevant"] = True
        strengths.append(f"Clear audience defined: {kpi.intended_audience}")
    else:
        smart_checks["Relevant"] = False
        issues.append("Intended audience not specified")
    
    # T - Time-bound
    if kpi.time_period and len(kpi.time_period) > 0:
        smart_checks["Time-bound"] = True
        strengths.append(f"Reporting cycle defined: {kpi.time_period}")
    else:
        smart_checks["Time-bound"] = False
        issues.append("Reporting cycle not specified")
    
    # Calculate SMART score (exclude None values)
    assessable = [v for v in smart_checks.values() if v is not None]
    smart_score = sum(1 for v in assessable if v)
    smart_total = len(assessable)
    
    # Actionability assessment
    actionability = "High" if kpi.data_owner and kpi.intended_audience else "Medium"
    
    # =======================================================================
    # NEW: Tufte Visualization Principles Assessment
    # =======================================================================
    
    tufte_checks = {}
    viz_strengths = []
    viz_issues = []
    
    # 1. Data-Ink Ratio (meaningful data, minimal chart decoration)
    has_ratio = "/" in kpi.formula or "÷" in kpi.formula
    has_trend = len(kpi.historical_aggregates) >= 3
    
    if has_ratio and has_trend:
        tufte_checks["data_ink_ratio"] = True
        viz_strengths.append("KPI is a ratio with time series (high data density)")
    elif has_ratio:
        tufte_checks["data_ink_ratio"] = True
        viz_strengths.append("KPI is a ratio (meaningful comparison)")
    elif has_trend:
        tufte_checks["data_ink_ratio"] = False
        viz_issues.append("Count-based KPI without ratio context (lower data-ink ratio)")
    else:
        tufte_checks["data_ink_ratio"] = False
        viz_issues.append("Lacks both ratio structure and time series")
    
    # 2. Chartjunk Avoidance (simple, clear units and direction)
    simple_units = any(term in kpi.definition.lower() for term in ["percent", "percentage", "rate", "%"])
    direction_clear = any(term in kpi.definition.lower() for term in ["increase", "decrease", "maintain", "improve", "reduce", "higher", "lower"])
    
    if simple_units and direction_clear:
        tufte_checks["chartjunk_avoidance"] = True
        viz_strengths.append("Clear units and direction (minimal interpretation needed)")
    elif simple_units:
        tufte_checks["chartjunk_avoidance"] = True
        viz_strengths.append("Standard percentage units (easy to understand)")
    else:
        tufte_checks["chartjunk_avoidance"] = False
        viz_issues.append("Units or direction unclear (may need extra context)")
    
    # 3. Data Density (has comparisons, sufficient variation)
    has_comparisons = any(term in kpi.definition.lower() for term in ["target", "goal", "peer", "benchmark", "compared to"])
    
    # Check for meaningful variation in time series
    has_variation = False
    if len(kpi.historical_aggregates) >= 3:
        values = [x['value'] for x in kpi.historical_aggregates]
        if len(values) > 1:
            cv = (pstdev(values) / mean(values)) if mean(values) > 0 else 0
            has_variation = cv > 0.01  # Coefficient of variation > 1%
    
    if has_comparisons and has_variation:
        tufte_checks["data_density"] = True
        viz_strengths.append("Has comparison context and meaningful variation")
    elif has_comparisons:
        tufte_checks["data_density"] = True
        viz_strengths.append("Has comparison context (target or benchmark)")
    elif has_variation:
        tufte_checks["data_density"] = False
        viz_issues.append("Has variation but lacks comparison context (add target/peer)")
    else:
        tufte_checks["data_density"] = False
        viz_issues.append("Lacks both comparison context and meaningful variation")
    
    # 4. Small Multiples Ready (can be disaggregated for subgroup comparison)
    disaggregatable = any(term in kpi.bias_or_equity_risks.lower() for term in ["demographic", "segment", "subgroup", "race", "ethnicity", "gender", "income"])
    
    if disaggregatable:
        tufte_checks["small_multiples"] = True
        viz_strengths.append("Can be disaggregated for equity monitoring (small multiples)")
    else:
        tufte_checks["small_multiples"] = False
        viz_issues.append("Not identified as disaggregatable by demographic group")
    
    # 5. Narrative Clarity (tells a story, actionable)
    is_actionable = bool(kpi.data_owner and kpi.intended_audience)
    direction_meaningful = direction_clear  # Already checked above
    
    if is_actionable and direction_meaningful:
        tufte_checks["narrative_clarity"] = True
        viz_strengths.append("Clear narrative: actionable with defined direction")
    elif is_actionable:
        tufte_checks["narrative_clarity"] = True
        viz_strengths.append("Actionable with clear ownership")
    else:
        tufte_checks["narrative_clarity"] = False
        viz_issues.append("Lacks clear ownership or direction for action")
    
    # Calculate Tufte score
    tufte_score = sum(1 for v in tufte_checks.values() if v)
    tufte_total = len(tufte_checks)
    tufte_percentage = int((tufte_score / tufte_total) * 100)
    
    # Combined recommendations
    recommendations = []
    
    # SMART recommendations
    if "demographic" not in kpi.bias_or_equity_risks.lower() and \
       "segment" not in kpi.bias_or_equity_risks.lower():
        recommendations.append("Consider disaggregating by demographic group for equity monitoring")
    
    if "target" not in kpi.definition.lower() and "goal" not in kpi.definition.lower():
        recommendations.append("Define explicit target or goal (e.g., 'maintain above 85%' or 'improve to 90% by 2028')")
    
    if len(kpi.historical_aggregates) >= 3:
        recommendations.append("Consider adding trend expectation to definition (e.g., 'trending upward' or 'maintain stability')")
    
    # Tufte-specific recommendations
    if not has_comparisons:
        recommendations.append("Add comparison context (peer institution, national average, or historical baseline)")
    
    if not direction_clear:
        recommendations.append("Clarify direction in definition (e.g., 'higher is better' or 'maintain stability')")
    
    if not has_ratio and not has_trend:
        recommendations.append("Consider converting to rate or ratio for better visualization")
    
    # Overall status determination
    combined_score = (smart_score / smart_total + tufte_score / tufte_total) / 2
    
    if smart_score >= 4 and tufte_score >= 4:
        status = "Strong Design & Visualization-Ready"
        notes = f"SMART: {smart_score}/{smart_total}, Tufte: {tufte_score}/{tufte_total} ({tufte_percentage}%). Dashboard-ready."
    elif smart_score >= 4:
        status = "Strong Design, Needs Visualization Enhancement"
        notes = f"SMART: {smart_score}/{smart_total}, Tufte: {tufte_score}/{tufte_total} ({tufte_percentage}%). Consider visualization improvements."
    elif tufte_score >= 4:
        status = "Visualization-Ready, Needs Design Refinement"
        notes = f"SMART: {smart_score}/{smart_total}, Tufte: {tufte_score}/{tufte_total} ({tufte_percentage}%). Address design gaps."
    else:
        status = "Needs Refinement"
        notes = f"SMART: {smart_score}/{smart_total}, Tufte: {tufte_score}/{tufte_total} ({tufte_percentage}%). Address both design and visualization."
    
    return StepResult(
        status=status,
        notes=notes,
        details={
            "smart_framework": {
                "score": f"{smart_score}/{smart_total}",
                "criteria": smart_checks,
                "strengths": strengths,
                "issues": issues
            },
            "tufte_principles": {
                "score": f"{tufte_score}/{tufte_total}",
                "percentage": f"{tufte_percentage}%",
                "criteria": tufte_checks,
                "strengths": viz_strengths,
                "issues": viz_issues,
                "reference": "Tufte, E. (2001). The Visual Display of Quantitative Information"
            },
            "actionability": actionability,
            "recommendations": recommendations,
            "note": "SMART = Specific, Measurable, Achievable, Relevant, Time-bound; Tufte = Data-ink ratio, Chartjunk avoidance, Data density, Small multiples, Narrative clarity"
        }
    )


# ============================================================================
# Step 10: Industry Best Practice Alignment
# ============================================================================

def step_10_assess_best_practices(kpi: KPIInput) -> StepResult:
    """
    Assess alignment to EDUCAUSE, AGB, and NACUBO standards.
    Focus on external industry best practices.
    """
    
    # EDUCAUSE Standards (Data Governance & Analytics)
    educause_checks = {}
    
    educause_checks["data_governance"] = {
        "standard": "Clear data ownership and stewardship",
        "met": bool(kpi.data_owner and kpi.data_steward),
        "reference": "EDUCAUSE Data Governance Framework (2023)"
    }
    
    educause_checks["equity_consideration"] = {
        "standard": "Bias and equity risks documented",
        "met": bool(kpi.bias_or_equity_risks and len(kpi.bias_or_equity_risks) > 0),
        "reference": "EDUCAUSE Analytics Maturity Model"
    }
    
    educause_checks["limitations_documented"] = {
        "standard": "Known limitations clearly stated",
        "met": bool(kpi.known_limitations and len(kpi.known_limitations) > 0),
        "reference": "EDUCAUSE Data Quality Standards"
    }
    
    # AGB Standards (Board Governance & Oversight)
    agb_checks = {}
    
    agb_checks["board_appropriate"] = {
        "standard": "Intended for board/cabinet strategic oversight",
        "met": any(term in kpi.intended_audience.lower() 
                   for term in ["board", "cabinet", "trustees", "executive"]),
        "reference": "AGB Dashboard Metrics for Boards (2022)"
    }
    
    agb_checks["multi_year_trend"] = {
        "standard": "Multi-year trend data available (3+ years)",
        "met": len(kpi.historical_aggregates) >= 3,
        "reference": "AGB Board Responsibilities for Strategic Planning"
    }
    
    agb_checks["contextualized"] = {
        "standard": "Includes target or peer comparison for context",
        "met": any(term in kpi.definition.lower() 
                   for term in ["target", "goal", "peer", "benchmark"]),
        "reference": "AGB Benchmarking for Boards"
    }
    
    # NACUBO Standards (Financial & Operational Rigor)
    nacubo_checks = {}
    
    nacubo_checks["standard_definitions"] = {
        "standard": "Uses standard definitions (IPEDS-aligned where applicable)",
        "met": "IPEDS" in kpi.primary_source_system or 
               any(term in kpi.definition.lower() 
                   for term in ["first-time", "full-time", "degree-seeking", "ipeds"]),
        "reference": "NACUBO KPI Framework (2024)"
    }
    
    nacubo_checks["multi_year_data"] = {
        "standard": "Multi-year historical data for trend analysis",
        "met": len(kpi.historical_aggregates) >= 3,
        "reference": "NACUBO Business Intelligence Best Practices"
    }
    
    nacubo_checks["auditable"] = {
        "standard": "Formula and source system documented for auditability",
        "met": bool(kpi.formula and kpi.primary_source_system),
        "reference": "NACUBO Financial Reporting Standards"
    }
    
    # Calculate scores
    educause_met = sum(1 for c in educause_checks.values() if c["met"])
    educause_total = len(educause_checks)
    
    agb_met = sum(1 for c in agb_checks.values() if c["met"])
    agb_total = len(agb_checks)
    
    nacubo_met = sum(1 for c in nacubo_checks.values() if c["met"])
    nacubo_total = len(nacubo_checks)
    
    total_met = educause_met + agb_met + nacubo_met
    total_checks = educause_total + agb_total + nacubo_total
    percentage = (total_met / total_checks) * 100
    
    # Generate recommendations for unmet standards
    recommendations = []
    
    for check in educause_checks.values():
        if not check["met"]:
            recommendations.append(f"EDUCAUSE: {check['standard']}")
    
    for check in agb_checks.values():
        if not check["met"]:
            recommendations.append(f"AGB: {check['standard']}")
    
    for check in nacubo_checks.values():
        if not check["met"]:
            recommendations.append(f"NACUBO: {check['standard']}")
    
    # Status determination
    if percentage >= 85:
        status = "Strong Alignment"
        notes = f"Exceeds industry standards ({total_met}/{total_checks} met, {percentage:.0f}%)"
    elif percentage >= 70:
        status = "Partial Alignment"
        notes = f"Meets most industry standards ({total_met}/{total_checks} met, {percentage:.0f}%)"
    else:
        status = "Needs Enhancement"
        notes = f"Significant gaps in industry alignment ({total_met}/{total_checks} met, {percentage:.0f}%)"
    
    return StepResult(
        status=status,
        notes=notes,
        details={
            "educause_standards": {
                "score": f"{educause_met}/{educause_total}",
                "checks": educause_checks,
                "organization": "EDUCAUSE - Data Governance & Analytics"
            },
            "agb_standards": {
                "score": f"{agb_met}/{agb_total}",
                "checks": agb_checks,
                "organization": "AGB - Board Governance & Oversight"
            },
            "nacubo_standards": {
                "score": f"{nacubo_met}/{nacubo_total}",
                "checks": nacubo_checks,
                "organization": "NACUBO - Financial & Operational Rigor"
            },
            "overall": {
                "total_score": f"{total_met}/{total_checks}",
                "percentage": f"{percentage:.0f}%",
                "status": status
            },
            "recommendations": recommendations,
            "note": "Industry standards from EDUCAUSE, AGB (Association of Governing Boards), and NACUBO (National Association of College and University Business Officers)"
        }
    )


# ============================================================================
# Main Workflow Orchestration
# ============================================================================

def run_kpi_readiness(
    kpi: KPIInput,
    include_design_assessment: bool = DEFAULT_INCLUDE_DESIGN_ASSESSMENT,
    include_best_practices: bool = DEFAULT_INCLUDE_BEST_PRACTICES
) -> KPIReadinessReport:
    """
    Run complete 10-step KPI readiness workflow.
    
    Args:
        kpi: KPI input data
        include_design_assessment: Run Step 9 (default: True)
        include_best_practices: Run Step 10 (default: True)
    
    Returns:
        Complete readiness report with all 10 steps
    """
    # Core validation steps (1-8)
    s1 = step_1_register(kpi)
    s2 = step_2_validate_definition(kpi)
    s3 = step_3_check_entity_coherence(kpi)
    s4 = step_4_screen_data_quality(kpi)
    s5 = step_5_assess_ai_use(kpi)
    s6 = step_6_check_governance(kpi)
    s7 = step_7_assess_readiness(kpi, s2, s3, s4, s6)
    s8 = step_8_generate_summary(kpi, s7, s5, s4, s3, s6, s2)
    
    # Quality enhancement steps (9-10) - optional
    if include_design_assessment:
        s9 = step_9_assess_design_quality(kpi)
    else:
        s9 = StepResult(
            status="Skipped", 
            notes="Design assessment disabled by configuration", 
            details={}
        )
    
    if include_best_practices:
        s10 = step_10_assess_best_practices(kpi)
    else:
        s10 = StepResult(
            status="Skipped", 
            notes="Best practices assessment disabled by configuration", 
            details={}
        )
    
    return KPIReadinessReport(
        kpi_name=kpi.name,
        step_1_register=s1,
        step_2_definition=s2,
        step_3_entity=s3,
        step_4_quality=s4,
        step_5_ai=s5,
        step_6_governance=s6,
        step_7_readiness=s7,
        step_8_summary=s8,
        step_9_design_quality=s9,
        step_10_best_practices=s10
    )


def _print_report(report: KPIReadinessReport) -> None:
    """Print comprehensive report to console."""
    def show(title: str, sr: StepResult) -> None:
        print(f"\n{title}")
        print(f"Status: {sr.status}")
        print(f"Notes: {sr.notes}")
        if sr.details and sr.status != "Skipped":
            print("Details:")
            for k, v in sr.details.items():
                if isinstance(v, dict):
                    print(f"  {k}:")
                    for k2, v2 in v.items():
                        print(f"    {k2}: {v2}")
                elif isinstance(v, list) and len(v) > 0:
                    print(f"  {k}:")
                    for item in v:
                        print(f"    - {item}")
                else:
                    print(f"  {k}: {v}")

    print(f"\n{'=' * 70}")
    print(f"10-STEP KPI READINESS REPORT: {report.kpi_name}")
    print("=" * 70)

    show("Step 1: Register Metadata", report.step_1_register)
    show("Step 2: Validate Definition", report.step_2_definition)
    show("Step 3: Entity Coherence", report.step_3_entity)
    show("Step 4: Data Quality Screening", report.step_4_quality)
    show("Step 5: AI Use Assessment", report.step_5_ai)
    show("Step 6: Governance Check", report.step_6_governance)
    show("Step 7: Readiness Decision", report.step_7_readiness)
    
    summary = report.step_8_summary.details.get("summary", {})
    print("\nStep 8: Summary Report")
    print(f"Status: {report.step_8_summary.status}")
    print(f"Readiness: {summary.get('readiness_status')}")
    if summary.get('blockers'):
        print(f"Blockers: {summary.get('blockers')}")
    
    # Quality enhancement steps
    show("Step 9: KPI Design Quality (SMART Framework)", report.step_9_design_quality)
    show("Step 10: Industry Best Practice Alignment", report.step_10_best_practices)



# ============================================================================
# NLP Demo: Survey Comment Categorization
# ============================================================================

def demo_nlp_survey_comments() -> None:
    """
    Demonstrate NLP-style survey comment categorization.

    Uses keyword-based classification as a pilot example.
    Production use would apply sentiment analysis, topic modeling, or an LLM.

    Aligned to AIR abstract: 'natural language processing to organize
    survey comments' — this function demonstrates that technique.

    Note: This is intentionally simple and transparent. The goal is to show
    how AI can structure open-ended feedback for human review, not to replace
    human interpretation.
    """

    sample_comments = [
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

    categories = {
        "Registration & Enrollment": [
            "registration", "enroll", "waitlist", "schedule", "course"
        ],
        "Advising & Support": [
            "advisor", "advising", "counselor", "support", "helpful"
        ],
        "Financial Aid & Billing": [
            "financial", "aid", "tuition", "payment", "award", "billing"
        ],
        "Facilities & Resources": [
            "library", "study", "campus", "facility", "space", "hours"
        ],
        "Faculty & Instruction": [
            "professor", "instructor", "feedback", "office hours", "teaching"
        ],
        "Career Services": [
            "career", "internship", "job", "employment", "placement"
        ],
    }

    print("\n" + "=" * 70)
    print("NLP DEMO: Survey Comment Categorization")
    print("Aligned to AIR Abstract: NLP to organize survey comments")
    print("=" * 70)
    print()
    print("Input: 10 open-ended student survey comments")
    print("Method: Keyword-based classification (pilot example)")
    print("Output: Categorized themes for human review")
    print()

    results = {}
    uncategorized = []

    for comment in sample_comments:
        comment_lower = comment.lower()
        matched = False
        for category, keywords in categories.items():
            if any(keyword in comment_lower for keyword in keywords):
                if category not in results:
                    results[category] = []
                results[category].append(comment)
                matched = True
                break
        if not matched:
            uncategorized.append(comment)

    print("-" * 70)
    for category, comments in sorted(results.items()):
        print(f"\n  {category} ({len(comments)} comment(s)):")
        for c in comments:
            print(f"    - {c}")

    if uncategorized:
        print(f"\n  Uncategorized ({len(uncategorized)} comment(s)):")
        for c in uncategorized:
            print(f"    - {c}")

    total = len(sample_comments)
    categorized = total - len(uncategorized)
    print()
    print("-" * 70)
    print(f"  Total comments: {total}")
    print(f"  Categorized:    {categorized} ({int(categorized/total*100)}%)")
    print(f"  Uncategorized:  {len(uncategorized)}")
    print()
    print("  Human review required: All categorizations should be verified")
    print("  before use in reporting or dashboard publication.")
    print()
    print("  Note: This is a keyword-based pilot example. Production NLP")
    print("  would use sentiment analysis, topic modeling, or an LLM API")
    print("  for higher accuracy and richer theme extraction.")
    print("=" * 70)

# ============================================================================
# Main Entry Point with Examples
# ============================================================================

def main() -> None:
    """
    Main entry point with examples.
    """
    
    # ========================================================================
    # EXAMPLE 1: Basic synthetic data example
    # ========================================================================
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Synthetic Data with 10-Step Assessment")
    print("=" * 70)
    
    example = KPIInput(
        name="First-Year Retention Rate",
        definition="Percentage of first-time, full-time degree-seeking undergraduates who return for the following fall term",
        formula="Returning FTFT Students / FTFT Cohort",
        time_period="Fall-to-fall, annually",
        primary_source_system="IPEDS",
        secondary_source_systems=["SIS"],
        intended_audience="Board of Trustees",

        identifier_fields=["student_id"],
        source_systems_in_join=["IPEDS"],

        historical_aggregates=[
            {"period": "Fall 2018", "value": 88.0},
            {"period": "Fall 2019", "value": 89.5},
            {"period": "Fall 2020", "value": 88.5},
            {"period": "Fall 2021", "value": 89.0},
            {"period": "Fall 2022", "value": 89.5},
            {"period": "Fall 2023", "value": 91.0},
        ],

        data_owner="Registrar",
        data_steward="Institutional Research",
        known_limitations="COVID-era cohorts may show atypical patterns; census date timing affects counts",
        bias_or_equity_risks="Retention rates vary by demographic segment; monitor equity gaps by race/ethnicity and income level",
        human_signoff_required=True,
    )

    report = run_kpi_readiness(example)
    _print_report(report)
    
    # NLP Demo
    demo_nlp_survey_comments()

    # Export outputs
    export_report_json(report, "retention_report.json")
    export_report_csv(report, "retention_summary.csv")
    
    # Generate chart
    anomalies = report.step_4_quality.details.get('anomalies', [])
    plot_time_series(example, anomalies, "retention_chart.png")
    
    print("\n" + "=" * 70)
    print("OUTPUTS GENERATED:")
    print("  - retention_report.json (complete structured report)")
    print("  - retention_summary.csv (executive summary)")
    print("  - retention_chart.png (time series visualization)")
    print("=" * 70)
    print("\nCreated by: Elmer Yglesias")
    print("Institution: St. John's College")
    print("Website: elmerdata.ai")
    print("ORCID: 0009-0004-9538-2159")
    print("License: MIT License (free to use, modify, and distribute)")
    print("GitHub: github.com/ElmYgl/kpi_readiness_10step")
    print("Presented at: AIR Forum 2026")


if __name__ == "__main__":
    main()
