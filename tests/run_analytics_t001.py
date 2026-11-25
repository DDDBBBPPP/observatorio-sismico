"""Run T001 migrations and role tests in a disposable, isolated PostgreSQL container."""
import subprocess
import time
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
NAME = f"observatorio-analytics-t001-{uuid4().hex[:12]}"


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=check)


def main() -> None:
    run("docker", "run", "--rm", "-d", "--network", "none", "--name", NAME,
        "-e", "POSTGRES_PASSWORD=local-test-only", "postgres:16-alpine")
    try:
        for _ in range(60):
            ready = run("docker", "exec", NAME, "pg_isready", "-U", "postgres", check=False)
            if ready.returncode == 0:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("Disposable PostgreSQL did not become ready")

        for source, target in (
            (ROOT / "tests" / "analytics_t001.sql", "/tmp/tests/analytics_t001.sql"),
            (ROOT / "supabase" / "migrations" / "202611250001_analytics_private.sql",
             "/tmp/supabase/migrations/202611250001_analytics_private.sql"),
            (ROOT / "supabase" / "migrations" / "202611250002_analytics_rpc.sql",
             "/tmp/supabase/migrations/202611250002_analytics_rpc.sql"),
        ):
            run("docker", "exec", NAME, "mkdir", "-p", str(Path(target).parent).replace("\\", "/"))
            run("docker", "cp", str(source), f"{NAME}:{target}")

        result = run("docker", "exec", NAME, "psql", "-U", "postgres", "-d", "postgres",
                     "-v", "ON_ERROR_STOP=1", "-f", "/tmp/tests/analytics_t001.sql",
                     check=False)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        print("T001 SQL, permissions, idempotence and revision tests: PASS")
    finally:
        run("docker", "rm", "-f", NAME, check=False)


if __name__ == "__main__":
    main()
