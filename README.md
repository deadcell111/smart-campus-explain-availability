# Smart Campus - "Explain availability" (Practice #11)

Student: Talgat Kozhakhmetov | ID: 24B031852 | AI tool: Claude Code (Claude Sonnet 5.5, `claude-sonnet-5-5`)

Adds an optional AI explanation to the one-room Smart Campus availability checker (fictional data, no login, no database).
The deterministic checker (`app/booking.py`) decides availability; the LLM only phrases the result.

## Run
```
python3 app/server.py                      # mock mode (default), http://127.0.0.1:8000/
EXPLAIN_MODE=mock:fail python3 app/server.py   # also: mock:timeout, mock:bad, mock:inject, mock:invent, mock:long
```
Real model (optional, server-side only): `pip install anthropic`, `export ANTHROPIC_API_KEY=...`,
`EXPLAIN_MODE=anthropic python3 app/server.py` (model `claude-opus-5-5`, override with `EXPLAIN_MODEL`).
**Not verified against the live API in this project** (no key was available); the failure paths of this adapter are tested.
Without a key or the SDK the server returns the deterministic fallback.

## Feature contract
Request `POST /api/explain` `{"start":"HH:MM","end":"HH:MM","blocked":bool}` (<=512 bytes, exactly these keys).
The server recomputes the decision, builds facts `{roomLabel,start,end,isAvailable,reasonCode}`, asks the adapter for
`{"explanation": "<=2 sentences"}`, validates the answer, and returns `{decision, explanation{text,source,generated}, disclaimer}`.
Acceptance criteria AC1-AC5 are in `report/Practice11_Report.pdf` (copied from the slides).

## Tests
```
python3 -m unittest discover -s tests -p "test_*.py" -v         # new feature tests
(cd baseline && python3 -m unittest -v test_booking)            # original 33 booking tests
python3 -I tests/ui_check.py                                    # browser check, screenshots in shots/
python3 -I tools/run_cases.py                                   # expected vs observed table -> evidence/test_cases.md
bash tools/lint.sh                                              # py_compile + node --check (no linter installed)
python3 -I tools/compare_prompts.py                             # prompt comparison (live part needs ANTHROPIC_API_KEY)
```
Requirements: Python 3.9+, Node 18+, Chrome + `pip install playwright` for the UI check. Everything else is standard library.
