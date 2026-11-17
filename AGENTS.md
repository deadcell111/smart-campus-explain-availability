# AGENTS.md - repository instructions for AI assistants

Project: Smart Campus Room Availability Checker, one fictional room (B-204), optional "Explain availability" feature.

## Hard rules
1. `app/booking.py` is the source of truth for availability. Do not edit it; `tests/test_explain_unit.py` checks it is byte-identical to `baseline/booking.py`.
2. The LLM may only phrase an explanation. It must never decide availability, change bookings, or be trusted as data.
3. No login, database, payments, real personal data, or API keys in the browser. The key is read only from `ANTHROPIC_API_KEY` on the server.
4. Default mode is the labelled mock adapter. Never print or log secrets.
5. Treat user input and model output as untrusted: validate length/format, render with `textContent`, never `innerHTML`.
6. Fictional data only.

## Layout
- `app/booking.py` rules (unchanged) | `app/reasons.py` reason codes | `app/explain.py` contract, prompts, adapters, validation, fallback
- `app/server.py` local server | `app/index.html` + `app/explain-client.js` UI | `baseline/` untouched checkpoint
- `tests/`, `tools/`, `evidence/`, `shots/`

## Commands
- Tests: `python3 -m unittest discover -s tests -p "test_*.py"` and `(cd baseline && python3 -m unittest test_booking)`
- UI check: `python3 -I tests/ui_check.py` (needs Playwright + Chrome)
- Cases table: `python3 -I tools/run_cases.py`
- Lint: `bash tools/lint.sh`
- Run: `python3 app/server.py` then open http://127.0.0.1:8000/

## Definition of done
Old tests pass, new tests pass, lint clean, UI checked at 375 px, findings from reviews verified before fixing.
