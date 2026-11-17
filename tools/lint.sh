#!/usr/bin/env bash
# No flake8/pylint/eslint is installed, so lint = byte-compile all Python + node --check all JS + script block of index.html.
cd "$(dirname "$0")/.." || exit 1
fail=0
python3 -m py_compile app/*.py tests/*.py tools/*.py && echo "py_compile: OK" || fail=1
node --check app/explain-client.js && echo "node --check explain-client.js: OK" || fail=1
python3 - <<'PY' || fail=1
import re, subprocess, tempfile, os
s = open("app/index.html").read(); js = re.search(r"<script>(.*?)</script>", s, re.S).group(1)
f = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False); f.write(js); f.close()
r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True); os.unlink(f.name)
print("node --check index.html inline script:", "OK" if r.returncode == 0 else r.stderr); raise SystemExit(r.returncode)
PY
exit $fail
