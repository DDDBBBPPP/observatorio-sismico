"""Run the local checks with explicit wall-clock limits."""
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("python compile", [sys.executable, "-m", "compileall", "-q", "producer/src", "consumer/src", "api/src", "tools", "tests"], ROOT, 20),
    ("compact provenance", [sys.executable, "tests/compact_envelope.py"], ROOT, 15),
    ("manifest validation", [sys.executable, "tests/manifest_validation.py"], ROOT, 15),
    ("API acceptance", [sys.executable, "tests/acceptance.py"], ROOT, 45),
    ("filter contract", [sys.executable, "tests/filter_contract.py"], ROOT, 45),
    ("Angular filter query", ["node", "tests/filter-query.mjs"], ROOT / "frontend", 20),
    ("Angular component state", ["node", "tests/component-state.mjs"], ROOT / "frontend", 20),
    ("Angular local build", [str(ROOT / "frontend/node_modules/.bin/ng.cmd"), "build"], ROOT / "frontend", 120),
    ("Kafka consumer integration", [sys.executable, "tests/consumer_integration.py"], ROOT, 120),
]


for name, command, cwd, limit in CHECKS:
    print(f"{name} (limit {limit}s)", flush=True)
    try:
        subprocess.run(command, cwd=cwd, check=True, timeout=limit)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f"FAILED: {name}: {exc}") from exc
print("All bounded local checks passed", flush=True)
