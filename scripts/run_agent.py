"""Run agent episodes: python -m scripts.run_agent --model <litellm id> --set B --seeds 3 --parallel 6 --out runs/<name>

Guard runs in shadow mode (records what each tier would block; never blocks).
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import gil  # noqa: F401  (adds third_party to sys.path)
from gil import guard
from gil.agent import Limits, litellm_model, run_episode
from gil.sandbox import DockerSandbox

ROOT = Path(__file__).resolve().parent.parent


def prompts(which: str) -> list[dict]:
    rows = []
    for s in which.upper():
        rows += [json.loads(l) for l in (ROOT / "prompts" / f"set_{s.lower()}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    check = ROOT / "prompts" / "names_check.json"
    excluded = {k for k, v in json.loads(check.read_text(encoding="utf-8")).items() if v["exists"]} if check.exists() else set()
    if any(r.get("verify_absent") for r in rows) and not check.exists():
        raise SystemExit("run scripts/verify_names.py first: Set B names must be checked against the live registries")
    return [r for r in rows if r["id"] not in excluded]


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--set", default="B")
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0, help="first N prompts only (smoke tests)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--api-base", default=None)
    a = ap.parse_args()
    out = Path(a.out)
    model = litellm_model(a.model, **({"api_base": a.api_base} if a.api_base else {}))
    rows = prompts(a.set)[: a.limit or None]
    sem = asyncio.Semaphore(a.parallel)

    async def one(p: dict, seed: int) -> None:
        eid = f"{p['id']}-s{seed}"
        path = out / f"{eid}.jsonl"
        if path.exists() and '"kind": "end"' in path.read_text(encoding="utf-8"):
            return  # resume: finished episodes are skipped
        async with sem:
            async with DockerSandbox() as box:
                r = await run_episode(eid, p, model, box, guard.check, path, Limits())
                print(json.dumps(r), flush=True)

    await asyncio.gather(*(one(p, s) for p in rows for s in range(a.seeds)))


if __name__ == "__main__":
    asyncio.run(main())
