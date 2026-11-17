#!/usr/bin/env bash
# Runs every check and prints commands + results. Run from the project folder: bash run_all_tests.sh
cd "$(dirname "$0")" || exit 1
fail=0
run() { echo; echo "\$ $*"; "$@" 2>&1 | grep -v "^\[explain\]\|^\.*\[explain\]"; rc=${PIPESTATUS[0]}; echo "[exit code $rc]"; [ $rc -ne 0 ] && fail=1; }
run bash -c 'cd baseline && python3 -m unittest -v test_booking 2>&1 | tail -4'
run python3 -m unittest discover -s tests -p "test_*.py"
run python3 -I tests/ui_check.py
run python3 -I tools/run_cases.py
run bash tools/lint.sh
echo; [ $fail -eq 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECK FAILED"
