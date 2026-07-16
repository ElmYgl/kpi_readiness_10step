"""
Test Script — kpi_parser.py v1.1.0 Level 2A No-API Mode
MIT License
Copyright (c) 2026 Elmer Yglesias

Purpose:
  Verify the four v1.1.0 Level 2A test cases from ROADMAP.md before release:

    Test 1 — No-API activation:  mode detection switches to no_api when
                                 ANTHROPIC_API_KEY is absent
    Test 2 — Valid paste:        a pasted JSON response is parsed and the
                                 pipeline receives correct fields
    Test 3 — Bad paste:          malformed JSON is handled cleanly with a
                                 retry, not a crash
    Test 4 — Backward compat:    API key present selects the v1.0.0 API
                                 path; Level 2A logic never activates

  Test KPI: First-Year Retention Rate (same KPI as the manuscript
  demonstration in Section 6 and Table II).

Usage:
  python test_kpi_parser_v11.py

Requires:
  Python 3.8+ only. No packages, no API key, no network access.
  kpi_parser.py must be in the same directory.
"""

from __future__ import annotations

import io
import json
import os
import sys
from contextlib import redirect_stdout
from unittest import mock

import kpi_parser


# ============================================================================
# Test KPI — First-Year Retention Rate (manuscript demonstration KPI)
# ============================================================================

RETENTION_DESCRIPTION = """
First-Year Retention Rate. Percentage of first-time, full-time
degree-seeking undergraduates who return for the following fall term.
Formula: Returning FTFT Students / FTFT Cohort x 100.
Reported fall-to-fall, annually. Primary source: IPEDS.
Data owner: Registrar. Data steward: Institutional Research.
Audience: Board of Trustees.
Limitations: COVID-era cohorts may show atypical patterns.
Equity risks: retention varies by demographic segment; monitor gaps.
Historical: Fall 2018: 88.0, Fall 2019: 89.5, Fall 2020: 88.5,
Fall 2021: 89.0, Fall 2022: 89.5, Fall 2023: 91.0
"""

# The JSON an external LLM would return for the description above
VALID_LLM_RESPONSE = json.dumps({
    "name": "First-Year Retention Rate",
    "definition": ("Percentage of first-time, full-time degree-seeking "
                   "undergraduates who return for the following fall term"),
    "formula": "Returning FTFT Students / FTFT Cohort x 100",
    "time_period": "Fall-to-fall, annually",
    "primary_source_system": "IPEDS",
    "secondary_source_systems": ["SIS"],
    "identifier_fields": ["student_id"],
    "source_systems_in_join": ["IPEDS"],
    "intended_audience": "Board of Trustees",
    "data_owner": "Registrar",
    "data_steward": "Institutional Research",
    "known_limitations": "COVID-era cohorts may show atypical patterns",
    "bias_or_equity_risks": ("Retention varies by demographic segment; "
                             "monitor equity gaps"),
    "human_signoff_required": True,
    "historical_aggregates": [
        {"period": "Fall 2018", "value": 88.0},
        {"period": "Fall 2019", "value": 89.5},
        {"period": "Fall 2020", "value": 88.5},
        {"period": "Fall 2021", "value": 89.0},
        {"period": "Fall 2022", "value": 89.5},
        {"period": "Fall 2023", "value": 91.0},
    ],
}, indent=2)

# Same response wrapped in markdown fences — common LLM behavior
FENCED_LLM_RESPONSE = "```json\n" + VALID_LLM_RESPONSE + "\n```"

MALFORMED_RESPONSE = '{"name": "Broken KPI", "definition": missing quotes here}'


# ============================================================================
# Test Harness
# ============================================================================

RESULTS = []


def record(test_name: str, passed: bool, detail: str = "") -> None:
    RESULTS.append((test_name, passed, detail))
    marker = "PASS" if passed else "FAIL"
    print(f"  [{marker}] {test_name}")
    if detail and not passed:
        print(f"         {detail}")


def paste_feeder(*lines_groups):
    """
    Build a fake input() that feeds pre-scripted console lines.
    Each call to the returned function pops the next line.
    """
    queue = [line for group in lines_groups for line in group]

    def fake_input(prompt=""):
        if not queue:
            raise EOFError
        return queue.pop(0)

    return fake_input


def as_paste(text: str):
    """Convert a block of text into console lines ending with Enter twice."""
    return text.split("\n") + ["", ""]


# ============================================================================
# Test 1 — No-API activation
# ============================================================================

def test_1_no_api_activation():
    print("\nTest 1 — No-API mode activates when key is absent")
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        record("detect_mode() returns 'no_api' without key",
               kpi_parser.detect_mode() == "no_api")
        record("get_api_key() returns None without key",
               kpi_parser.get_api_key() is None)

    # Empty-string key must also count as absent
    with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "   "}):
        record("blank key treated as absent",
               kpi_parser.detect_mode() == "no_api")


# ============================================================================
# Test 2 — Valid paste flows through
# ============================================================================

def test_2_valid_paste():
    print("\nTest 2 — Valid pasted JSON is parsed correctly")

    os.environ.pop("ANTHROPIC_API_KEY", None)

    # Scripted console: choose [1] paste, then paste response, Enter twice
    fake = paste_feeder(["1"], as_paste(VALID_LLM_RESPONSE))
    buf = io.StringIO()
    with mock.patch("builtins.input", fake), redirect_stdout(buf):
        parsed = kpi_parser.parse_kpi_no_api(RETENTION_DESCRIPTION)

    record("parsed name matches",
           parsed.get("name") == "First-Year Retention Rate",
           f"got: {parsed.get('name')}")
    record("6 historical data points preserved",
           len(parsed.get("historical_aggregates", [])) == 6)
    record("human_signoff_required is True",
           parsed.get("human_signoff_required") is True)
    record("prompt printed to console",
           "PROMPT — paste this into your AI environment" in buf.getvalue())
    record("prompt saved to parser_prompt.txt",
           os.path.exists("parser_prompt.txt"))

    # Fenced variant — LLMs often wrap JSON in markdown fences
    fake = paste_feeder(["1"], as_paste(FENCED_LLM_RESPONSE))
    with mock.patch("builtins.input", fake), redirect_stdout(io.StringIO()):
        parsed_fenced = kpi_parser.parse_kpi_no_api(RETENTION_DESCRIPTION)
    record("markdown-fenced response also parses",
           parsed_fenced.get("name") == "First-Year Retention Rate")


# ============================================================================
# Test 3 — Bad paste handled cleanly
# ============================================================================

def test_3_bad_paste_retry():
    print("\nTest 3 — Malformed JSON triggers clean retry, then succeeds")

    os.environ.pop("ANTHROPIC_API_KEY", None)

    # Attempt 1: malformed paste. Attempt 2: valid paste. Should succeed.
    fake = paste_feeder(
        ["1"], as_paste(MALFORMED_RESPONSE),
        ["1"], as_paste(VALID_LLM_RESPONSE),
    )
    buf = io.StringIO()
    with mock.patch("builtins.input", fake), redirect_stdout(buf):
        parsed = kpi_parser.parse_kpi_no_api(RETENTION_DESCRIPTION)

    out = buf.getvalue()
    record("malformed paste did not crash", True)
    record("error message shown to user",
           "Could not parse the response as JSON" in out)
    record("retry prompt shown", "try again" in out)
    record("second attempt succeeded",
           parsed.get("name") == "First-Year Retention Rate")

    # Three malformed attempts must exit(1), not crash with a traceback
    fake = paste_feeder(
        ["1"], as_paste(MALFORMED_RESPONSE),
        ["1"], as_paste(MALFORMED_RESPONSE),
        ["1"], as_paste(MALFORMED_RESPONSE),
    )
    exited_cleanly = False
    with mock.patch("builtins.input", fake), redirect_stdout(io.StringIO()):
        try:
            kpi_parser.parse_kpi_no_api(RETENTION_DESCRIPTION)
        except SystemExit as e:
            exited_cleanly = (e.code == 1)
    record("three failures exit cleanly with code 1", exited_cleanly)


# ============================================================================
# Test 4 — Backward compatibility
# ============================================================================

def test_4_backward_compat():
    print("\nTest 4 — API key present selects v1.0.0 API path")

    with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-123"}):
        record("detect_mode() returns 'api' with key",
               kpi_parser.detect_mode() == "api")

        # parse_kpi() must route to the API function — verify by mocking it
        with mock.patch.object(
            kpi_parser, "parse_kpi_with_claude",
            return_value={"name": "routed-to-api"}
        ) as api_fn, mock.patch.object(
            kpi_parser, "parse_kpi_no_api"
        ) as no_api_fn:
            result = kpi_parser.parse_kpi(RETENTION_DESCRIPTION)
            record("parse_kpi() routed to API path",
                   result.get("name") == "routed-to-api"
                   and api_fn.called)
            record("Level 2A logic never activated",
                   not no_api_fn.called)

    # And the reverse routing without a key
    os.environ.pop("ANTHROPIC_API_KEY", None)
    with mock.patch.object(
        kpi_parser, "parse_kpi_no_api",
        return_value={"name": "routed-to-no-api"}
    ) as no_api_fn, mock.patch.object(
        kpi_parser, "parse_kpi_with_claude"
    ) as api_fn:
        result = kpi_parser.parse_kpi(RETENTION_DESCRIPTION)
        record("parse_kpi() routed to no-API path without key",
               result.get("name") == "routed-to-no-api"
               and no_api_fn.called and not api_fn.called)


# ============================================================================
# Prompt content check — the exported prompt must be self-contained
# ============================================================================

def test_6_api_error_handling():
    print("\nTest 6 — API errors exit cleanly, no traceback")
    import anthropic

    # Build a fake client whose create() raises AuthenticationError
    class FakeMessages:
        def create(self, **kwargs):
            raise anthropic.AuthenticationError(
                message="invalid x-api-key",
                response=mock.Mock(status_code=401, headers={}),
                body=None,
            )

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "bad-key"}):
        with mock.patch.object(anthropic, "Anthropic", FakeClient):
            buf = io.StringIO()
            exited = False
            code = None
            with redirect_stdout(buf):
                try:
                    kpi_parser.parse_kpi_with_claude(RETENTION_DESCRIPTION)
                except SystemExit as e:
                    exited = True
                    code = e.code
            out = buf.getvalue()
            record("auth error exits cleanly (no traceback)", exited and code == 1)
            record("auth error message is user-friendly",
                   "authentication failed" in out)
            record("auth error points to no-API mode",
                   "Level 2A" in out)


def test_5_prompt_content():
    print("\nTest 5 — Exported prompt is complete and self-contained")
    prompt = kpi_parser.build_full_prompt(RETENTION_DESCRIPTION)
    record("contains field schema", '"historical_aggregates"' in prompt)
    record("contains JSON-only instruction",
           "Return ONLY the JSON object" in prompt)
    record("contains the KPI description",
           "First-Year Retention Rate" in prompt)
    record("no unfilled placeholders", "{description}" not in prompt)


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    print("=" * 70)
    print("kpi_parser.py v1.1.0 — Level 2A Test Suite")
    print("Test KPI: First-Year Retention Rate")
    print("=" * 70)

    test_1_no_api_activation()
    test_2_valid_paste()
    test_3_bad_paste_retry()
    test_4_backward_compat()
    test_5_prompt_content()
    test_6_api_error_handling()

    passed = sum(1 for _, p, _ in RESULTS if p)
    total = len(RESULTS)

    print("\n" + "=" * 70)
    print(f"SUMMARY: {passed}/{total} checks passed")
    print("=" * 70)

    if passed == total:
        print("All checks passed — Level 2A is ready for release.")
        return 0
    print("Some checks failed — review output above before release.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
