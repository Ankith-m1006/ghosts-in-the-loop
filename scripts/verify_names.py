"""Check every Set B misspelled / invented name against the real registry and record the result.

A name that already exists is excluded from runs (it may be a live squat), never installed.
Writes prompts/names_check.json and marks set_b.jsonl rows with exclude=true / verified date.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import gil  # noqa: F401
from gatekeeper import registry

ROOT = Path(__file__).resolve().parent.parent
SET_B = ROOT / "prompts" / "set_b.jsonl"


def name_of(r: dict) -> tuple[str, str] | None:
    n = r.get("misspelled_name") or r.get("invented_name")
    if not n:
        return None
    eco = r.get("ecosystem") or ("npm" if r.get("language") == "javascript" else "pypi")
    return eco, n


async def main() -> None:
    rows = [json.loads(l) for l in SET_B.read_text(encoding="utf-8").splitlines() if l.strip()]
    today = datetime.now(timezone.utc).date().isoformat()
    results = {}
    for r in rows:
        if not (en := name_of(r)):
            continue
        rep = await registry.check(*en)
        results[r["id"]] = {"ecosystem": en[0], "name": en[1], "exists": rep.exists, "checked": today}
        r["verified"] = today
        r["exclude"] = bool(rep.exists)
    (ROOT / "prompts" / "names_check.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in results.items() if v["exists"]}, indent=1))
    print(f"{sum(v['exists'] for v in results.values())} of {len(results)} names exist -> excluded")
    print("NOTE: set_b.jsonl is NOT rewritten (that would change the frozen hash); runs read names_check.json.")


if __name__ == "__main__":
    asyncio.run(main())
