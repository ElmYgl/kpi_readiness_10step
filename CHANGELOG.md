# Changelog

All notable changes to the KPI Readiness Pipeline are documented here.

Author: Elmer Yglesias | St. John's College | elmerdata.ai
ORCID: 0009-0004-9538-2159 | MIT License
GitHub: github.com/ElmYgl/kpi_readiness_10step

---

## [1.1.0 — Week 1] — 2026-07-16

### Added — Level 2A: No-API Prompt-Export Mode (`kpi_parser.py`)

When no `ANTHROPIC_API_KEY` is detected, the parser now switches
automatically to prompt-export mode instead of exiting with an error:

- Prints the exact structured prompt it would have sent to the LLM,
  with clear delimiters, ready to paste into Claude.ai, ChatGPT,
  Copilot, Gemini, or any LLM
- Saves the prompt to `parser_prompt.txt` for convenience
- Accepts the JSON response pasted back interactively (Enter twice to
  finish) or loaded from a saved `.json` / `.txt` file
- Strips markdown code fences automatically if the LLM wrapped its
  response in them
- Validates the pasted JSON with up to three retry attempts and clear
  error messages — never crashes on a bad paste
- Continues the pipeline identically to API mode after the response is
  received: human review guardrail, `parsed_kpi.json`, automatic
  handoff to `kpi_readiness_10step.py`

New entry level:

| Level | Requires | Best for |
|-------|----------|----------|
| 1 — Core only | Python only | Any office, no AI budget |
| **2A — No-API mode ★ NEW** | Python only | Offices without approved API credits — works with any LLM |
| 2 — With parser | Python + API key | Remove technical friction |
| 3 — Full pipeline | Python + API key | Complete AI-assisted experience |

### Added — Clean API error handling (`kpi_parser.py`)

The Level 2 API path now catches authentication, rate-limit, connection,
and API status errors and prints a short, plain-language message instead
of a Python traceback. Each message points the user to no-API mode
(Level 2A) as a fallback. An invalid or expired key no longer produces
an alarming stack trace.

### Added — Test suite

- `test_kpi_parser_v11.py`: 25 automated checks covering no-API
  activation, valid paste, markdown-fenced paste, malformed-paste retry
  and clean exit, backward compatibility routing, prompt completeness,
  and clean API error handling. Runs on Python 3.8+ with no packages, no API key, and
  no network access. Test KPI: First-Year Retention Rate.

### Changed

- `parse_kpi()` is the new unified entry point; it routes to the API
  path (Level 2) when a key is present and to prompt-export mode
  (Level 2A) when it is not
- API-key and import error messages now mention the no-API alternative

### Unchanged (backward compatibility)

- With `ANTHROPIC_API_KEY` set, behavior is identical to v1.0.0 —
  Level 2A logic never activates
- Human review guardrail, three historical data options, file upload
  with fuzzy column matching, and the bridge handoff are unchanged
- `kpi_readiness_10step.py` and `kpi_improver.py` are untouched in
  Week 1 (improver no-API mode ships in Week 3 per ROADMAP.md)

### Acknowledgments

Level 2A implements the no-API mode concept proposed by Yolanda Uzzell
(CSU Fullerton), who identified API procurement approval as a real
adoption barrier and described the paste-based workflow this release
formalizes.

---

## [1.0.0] — 2026-05

AIR Forum 2026 release.

- Initial public release
- Three-tool pipeline: `kpi_parser.py`, `kpi_readiness_10step.py`,
  `kpi_improver.py`
- 10-step validation framework
- EDUCAUSE / AGB / NACUBO industry standards (9 criteria)
- SMART + Tufte dual design quality assessment
- MIT License
