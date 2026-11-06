import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from gil import analysis, guard
from gil.agent import Limits, cut, run_episode
from gil.commands import find_installs


# ---------- install extraction ----------
def test_pip_variants():
    calls = find_installs("cd /work && pip install requests 'flask[async]>=2' && python -m pip install numpy==1.26")
    assert [(c.manager, c.names) for c in calls] == [("pip", ["requests", "flask"]), ("pip", ["numpy"])]


def test_uv_and_js_managers():
    calls = find_installs("uv pip install rich; uv add httpx; yarn add left-pad; pnpm add @scope/pkg@1; bun add zod; npm i -D typescript")
    assert [(c.manager, c.ecosystem, c.names) for c in calls] == [
        ("uv", "pypi", ["rich"]), ("uv", "pypi", ["httpx"]), ("yarn", "npm", ["left-pad"]),
        ("pnpm", "npm", ["@scope/pkg"]), ("bun", "npm", ["zod"]), ("npm", "npm", ["typescript"])]


def test_git_urls_and_non_installs():
    calls = find_installs("pip install git+https://github.com/a/b.git && ls && python main.py")
    assert len(calls) == 1 and calls[0].names == [] and calls[0].via_url
    assert find_installs("echo pip install fake") == []
    assert find_installs("npm run build") == []


def test_env_prefix_and_bare_npm_install():
    calls = find_installs("PIP_NO_INPUT=1 pip install pandas\nnpm install")
    assert calls[0].names == ["pandas"] and calls[1].manager == "npm" and calls[1].names == []


# ---------- guard tiers ----------
@dataclass
class Rep:
    ecosystem: str = "pypi"
    name: str = "x"
    exists: bool = True
    created: datetime | None = None
    versions: int = 20
    downloads: int | None = 100000
    similar_to: str | None = None
    has_install_scripts: bool = False
    flags: list = field(default_factory=list)

    @property
    def age_days(self):
        return None if not self.created else (datetime.now(timezone.utc) - self.created).days


def test_ghost_blocked_by_every_tier():
    d = guard.decide(Rep(exists=False))
    assert all(d.blocks.values()) and not d.exists


def test_real_popular_package_passes_every_tier():
    d = guard.decide(Rep(created=datetime.now(timezone.utc) - timedelta(days=3000)))
    assert not any(d.blocks.values())


def test_squatter_metadata_caught_from_t1():
    d = guard.decide(Rep(created=datetime.now(timezone.utc) - timedelta(days=2), versions=1, downloads=3))
    assert d.blocks == {"T0_exists": False, "T1_metadata": True, "T2_typosquat": True, "T3_code": True}


def test_new_release_of_real_project_not_blocked_by_age_alone():
    d = guard.decide(Rep(created=datetime.now(timezone.utc) - timedelta(days=5), versions=4, downloads=50000))
    assert not d.blocks["T1_metadata"]


def test_typosquat_and_code_tiers():
    old = datetime.now(timezone.utc) - timedelta(days=800)
    d = guard.decide(Rep(created=old, similar_to="requests"))
    assert d.blocks["T2_typosquat"] and not d.blocks["T1_metadata"]

    class Insp:
        verdict = "malicious-looking"
    d = guard.decide(Rep(created=old), Insp())
    assert d.blocks["T3_code"] and not d.blocks["T2_typosquat"]


# ---------- agent loop ----------
class ScriptedModel:
    def __init__(self, replies):
        self.replies = list(replies)

    async def __call__(self, messages):
        return self.replies.pop(0)


class FakeBox:
    def __init__(self):
        self.commands = []

    async def run(self, command, timeout):
        self.commands.append(command)
        if "ghost-pkg" in command:
            return 1, "ERROR: No matching distribution found for ghost-pkg"
        return 0, "ok " * 2000


def test_episode_logs_installs_guard_and_done(tmp_path):
    async def fake_guard(eco, name):
        return guard.decide(Rep(ecosystem=eco, name=name, exists=name != "ghost-pkg",
                                created=datetime.now(timezone.utc) - timedelta(days=3000)))

    model = ScriptedModel(["try\n```bash\npip install ghost-pkg\n```", "use real\n```bash\npip install requests\n```",
                           "no block here", "done\n```bash\necho TASK_DONE\n```"])
    box = FakeBox()
    log = tmp_path / "e.jsonl"
    r = asyncio.run(run_episode("e1", {"id": "B-1", "set": "B", "prompt": "x", "language": "python"}, model, box, fake_guard, log, Limits(steps=6)))
    assert r["status"] == "done" and box.commands == ["pip install ghost-pkg", "pip install requests"]
    rows = [json.loads(l) for l in log.read_text().splitlines()]
    kinds = [x["kind"] for x in rows]
    assert kinds.count("install") == 2 and "format_error" in kinds and kinds[-1] == "end"
    assert rows[kinds.index("install")]["guard"][0]["exists"] is False

    eps = analysis.load([log])
    assert analysis.recovery(eps[0]) == "switched_real"
    s = analysis.summarize(eps)
    assert s["guard"]["T0_exists"]["ghosts"] == 1 and s["guard"]["T0_exists"]["catch"][0] == 1.0
    assert s["guard"]["T0_exists"]["false_block"][0] == 0.0


def test_step_limit_and_cut():
    model = ScriptedModel(["```bash\nls\n```"] * 3)
    assert len(cut("x" * 5000)) < 2100

    async def go(tmp):
        return await run_episode("e2", {"id": "A-1", "prompt": "x"}, model, FakeBox(), None, tmp, Limits(steps=3))
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as d:
        assert asyncio.run(go(pathlib.Path(d) / "x.jsonl"))["status"] == "step_limit"


# ---------- analysis ----------
def test_recovery_labels():
    def ep(installs, status="done"):
        e = analysis.Episode("e", status=status)
        for names, exists, urls in installs:
            e.installs.append({"names": names, "urls": urls, "guard": [{"name": n, "exists": x} for n, x in zip(names, exists)]})
        return e
    assert analysis.recovery(ep([(["g1"], [False], []), (["g2"], [False], [])])) == "second_ghost"
    assert analysis.recovery(ep([(["g1"], [False], []), ([], [], ["git+https://x"])])) == "git_or_url"
    assert analysis.recovery(ep([(["g1"], [False], [])])) == "wrote_it"
    assert analysis.recovery(ep([(["g1"], [False], [])], status="step_limit")) == "gave_up"
    assert analysis.recovery(ep([(["requests"], [True], [])])) is None


def test_stats():
    p, lo, hi = analysis.wilson(5, 100)
    assert abs(p - 0.05) < 1e-9 and 0.01 < lo < 0.05 < hi < 0.12
    assert analysis.wilson(0, 0) == (0.0, 0.0, 0.0)
    assert analysis.mcnemar(0, 0) == 1.0 and analysis.mcnemar(0, 10) < 0.01
