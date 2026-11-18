"""Check repository-local Markdown link targets after documentation moves."""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import re


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[[^\]]*\]\((<[^>]+>|[^\s)]+)")
SKIP_DIRS = {"node_modules", ".git", "dist", ".angular"}


def main() -> None:
    broken = []
    checked = 0
    for path in ROOT.rglob("*.md"):
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        in_fence = False
        for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for match in LINK.finditer(line):
                raw = match.group(1).strip("<>")
                parsed = urlsplit(raw)
                if parsed.scheme or raw.startswith(("#", "//")):
                    continue
                target = (path.parent / unquote(parsed.path)).resolve()
                checked += 1
                if not target.exists():
                    broken.append(f"{path.relative_to(ROOT)}:{number}: {raw}")
    if broken:
        raise SystemExit("Enlaces internos rotos:\n" + "\n".join(broken))
    print(f"Enlaces internos comprobados: {checked}; rotos: 0")


if __name__ == "__main__":
    main()
