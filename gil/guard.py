"""The install-time guard, in four cumulative tiers (RQ4).

T0 exists      block names the registry reports as not found (a ghost)
T1 metadata    + block brand-new, single-version, unused packages (squatter metadata)
T2 typosquat   + block names one typo away from a popular package
T3 code        + block packages whose code reads as malicious (Gatekeeper's Inspector)

`decide` is pure (takes a registry report, an optional code inspection) so it can be tested offline and
replayed later on the logged reports. `check` does the live lookups. The guard runs in shadow mode in the
main runs: it records what each tier WOULD do; nothing is blocked.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

TIERS = ("T0_exists", "T1_metadata", "T2_typosquat", "T3_code")


@dataclass
class Decision:
    ecosystem: str
    name: str
    exists: bool
    blocks: dict[str, bool]                 # tier -> would this tier block it
    reasons: dict[str, list[str]] = field(default_factory=dict)
    report: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _young_and_unused(rep: Any) -> list[str]:
    why = []
    age = getattr(rep, "age_days", None)
    if age is not None and age < 30:
        why.append(f"published {age} days ago")
    if getattr(rep, "versions", 0) <= 1:
        why.append("one version")
    dl = getattr(rep, "downloads", None)
    if dl is not None and dl < 100:
        why.append(f"{dl} downloads")
    # Squatter metadata = brand new AND (one version or almost no downloads). Age alone blocks real releases.
    if why and why[0].startswith("published") and len(why) >= 2:
        return why
    return []


def decide(rep: Any, inspection: Any | None = None) -> Decision:
    """rep: gatekeeper PackageReport (or anything with the same attributes)."""
    reasons: dict[str, list[str]] = {t: [] for t in TIERS}
    if not rep.exists:
        reasons["T0_exists"].append("not found in the registry")
    meta = _young_and_unused(rep) if rep.exists else []
    reasons["T1_metadata"] = list(reasons["T0_exists"]) + meta
    typo = [f"one typo from {rep.similar_to}"] if rep.exists and getattr(rep, "similar_to", None) else []
    reasons["T2_typosquat"] = reasons["T1_metadata"] + typo
    code = []
    if inspection is not None and getattr(inspection, "verdict", None) == "malicious-looking":
        code = ["code reads as malicious"]
    reasons["T3_code"] = reasons["T2_typosquat"] + code
    blocks = {t: bool(reasons[t]) for t in TIERS}
    report = {k: getattr(rep, k, None) for k in ("created", "versions", "downloads", "similar_to", "has_install_scripts")}
    if report.get("created") is not None:
        report["created"] = str(report["created"])
    return Decision(rep.ecosystem, rep.name, bool(rep.exists), blocks, reasons, report)


async def check(ecosystem: str, name: str, read_code: bool = True) -> Decision:
    """Live lookup against the real registry. Code is only read for packages that exist and already look risky."""
    from gatekeeper import registry  # vendored in third_party/
    rep = await registry.check(ecosystem, name)
    inspection = None
    if read_code and rep.exists and (rep.flags or rep.similar_to):
        from gatekeeper import inspect_pkg
        try:
            inspection = await inspect_pkg.inspect(ecosystem, name)
        except Exception:  # a failed read must not crash a run; T3 then equals T2 for this name
            inspection = None
    return decide(rep, inspection)
