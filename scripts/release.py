"""Build results/ for the public repo: aggregate reports only, no raw trajectories.

Ghost names that come from our own Set B "invented" prompts are kept (we wrote them). Names the models invented
on their own are replaced by a salted SHA-256 prefix, because a repeatable invented name is exactly what an attacker
would register. Registry security teams can get the plain list on request.

    python -m scripts.release e4b g31b
"""
import hashlib, json, os, re, sys
from pathlib import Path

SALT = os.environ.get("GIL_SALT", "ghosts-in-the-loop-2026")
OURS = {json.loads(l)["prompt"] for l in open("prompts/set_b.jsonl", encoding="utf-8") if '"invented"' in l}


def ours(name: str) -> bool:
    return any(name.lower() in p.lower() for p in OURS)


def mask(name: str) -> str:
    return name if ours(name) else "h:" + hashlib.sha256((SALT + name.lower()).encode()).hexdigest()[:12]


def scrub(rep: dict) -> dict:
    for s in rep.values():
        s["top_ghosts"] = [[mask(n), c] for n, c in s.get("top_ghosts", [])]
    return rep


if __name__ == "__main__":
    out = Path("results"); out.mkdir(exist_ok=True)
    for m in sys.argv[1:]:
        rep = scrub(json.load(open(f"runs/{m}-report.json", encoding="utf-8")))
        (out / f"{m}-report.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
        print("wrote", out / f"{m}-report.json")
