"""Build prompts/set_a.jsonl (300) and prompts/set_b.jsonl (100).

    python -m prompts.build

Row fields: id, set, language, prompt, plus domain / source / stress fields. The pilot's 150 rows
are copied from prompts/pilot_prompts.jsonl (the Ghost Packages pilot, commit fee2803) with their
original ids prefixed "pilot-".
"""
from __future__ import annotations

import json
from pathlib import Path

from . import source

HERE = Path(__file__).resolve().parent
PILOT = HERE / "pilot_prompts.jsonl"
SET_A = HERE / "set_a.jsonl"
SET_B = HERE / "set_b.jsonl"


def _lang_tag(lang: str) -> str:
    return "py" if lang == "python" else "js"


def build_set_a() -> list[dict]:
    rows = []
    for line in PILOT.read_text("utf-8").splitlines():
        if not line.strip():
            continue
        p = json.loads(line)
        rows.append({"id": f"A-pilot-{p['id']}", "set": "A", "language": p["language"], "prompt": p["task"],
                     "domain": p["domain"], "source": "pilot"})
    for lang, items in (("python", source.SET_A_PYTHON), ("javascript", source.SET_A_JS)):
        for i, (domain, task) in enumerate(items, 1):
            rows.append({"id": f"A-new-{_lang_tag(lang)}{i:03d}", "set": "A", "language": lang, "prompt": task,
                         "domain": domain, "source": "new"})
    return rows


def build_set_b() -> list[dict]:
    rows = []

    def add(kind: str, i: int, lang: str, task: str, **extra):
        rows.append({"id": f"B-{kind}-{i:02d}", "set": "B", "language": lang, "prompt": task,
                     "stress_type": kind, **extra})

    for i, (lang, task) in enumerate(source.SET_B_TIME, 1):
        add("time", i, lang, task)
    for i, (lang, task, wrong, real) in enumerate(source.SET_B_MISSPELLED, 1):
        add("misspelled", i, lang, task, misspelled_name=wrong, real_name=real,
            ecosystem="pypi" if lang == "python" else "npm", verify_absent=True, verified=None)
    for i, (lang, task, name) in enumerate(source.SET_B_INVENTED, 1):
        add("invented", i, lang, task, invented_name=name,
            ecosystem="pypi" if lang == "python" else "npm", verify_absent=True, verified=None)
    for i, (lang, task) in enumerate(source.SET_B_LONGTAIL, 1):
        add("longtail", i, lang, task)
    return rows


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    a, b = build_set_a(), build_set_b()
    write(SET_A, a)
    write(SET_B, b)
    print(f"wrote {len(a)} rows to {SET_A.name}, {len(b)} rows to {SET_B.name}")


if __name__ == "__main__":
    main()
