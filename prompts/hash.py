"""Print the SHA-256 of each prompt file (the pre-registration hashes for the paper).

    python -m prompts.hash            # set_a.jsonl, set_b.jsonl
    python -m prompts.hash FILE ...
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = [HERE / "set_a.jsonl", HERE / "set_b.jsonl"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    paths = [Path(p) for p in (argv if argv is not None else sys.argv[1:])] or DEFAULT
    for p in paths:
        print(f"{sha256_file(p)}  {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
