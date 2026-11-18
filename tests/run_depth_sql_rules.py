"""Pipe the temporary-table depth test into the already running API container."""
import subprocess
from pathlib import Path


root = Path(__file__).resolve().parents[1]
source = (root / "tests/depth_sql_rules.py").read_text(encoding="utf-8")
subprocess.run(["docker", "compose", "exec", "-T", "api", "python", "-"],
               cwd=root, input=source, text=True, timeout=20, check=True)
