"""Find package installs inside the shell commands an agent runs.

Covers pip, pip3, python -m pip, uv pip / uv add, npm, yarn, pnpm and bun. The package-name parsing
itself is ghostcheck's (third_party/ghostcheck/parsers.py), so this module only finds the install
segments in a command line and hands each one to the right parser.
"""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field

from ghostcheck.parsers import parse_npm_command, parse_pip_command

SEPARATORS = re.compile(r"\s*(?:&&|\|\||;|\n|\|)\s*")

PIP = re.compile(r"^(?:sudo\s+)?(?:(?:python3?|py)\s+-m\s+pip|pip3?|uv\s+pip)\s+install\b(.*)$", re.I)
UV_ADD = re.compile(r"^(?:sudo\s+)?uv\s+add\b(.*)$", re.I)
NPM = re.compile(r"^(?:sudo\s+)?npm\s+(?:install|i|add)\b(.*)$", re.I)
JS_ADD = re.compile(r"^(?:sudo\s+)?(?:yarn|pnpm|bun)\s+(?:add|install|i)\b(.*)$", re.I)


@dataclass
class InstallCall:
    manager: str            # pip | uv | npm | yarn | pnpm | bun
    ecosystem: str          # pypi | npm
    names: list[str]
    raw: str
    via_url: list[str] = field(default_factory=list)   # git+/http(s) specs: not a registry name


def _urls(rest: str) -> list[str]:
    try:
        toks = shlex.split(rest, posix=True)
    except ValueError:
        toks = rest.split()
    return [t for t in toks if re.match(r"^(git\+|https?://|github:|git@)", t)]


def find_installs(command: str) -> list[InstallCall]:
    """Every install in one shell command, in order. Bare `npm install` (no names) is kept with names=[]."""
    out: list[InstallCall] = []
    for seg in SEPARATORS.split(command.strip()):
        seg = seg.strip()
        if not seg:
            continue
        # drop a leading `cd x` style prefix already split off; strip env assignments like FOO=1 pip ...
        seg = re.sub(r"^(?:[A-Z_][A-Z0-9_]*=\S+\s+)+", "", seg)
        if m := PIP.match(seg):
            names = [d.name for d in parse_pip_command("pip install" + m.group(1))]
            out.append(InstallCall("uv" if seg.lower().startswith("uv") else "pip", "pypi", names, seg, _urls(m.group(1))))
        elif m := UV_ADD.match(seg):
            names = [d.name for d in parse_pip_command("pip install" + m.group(1))]
            out.append(InstallCall("uv", "pypi", names, seg, _urls(m.group(1))))
        elif m := NPM.match(seg):
            names = [d.name for d in parse_npm_command("npm install" + m.group(1))]
            out.append(InstallCall("npm", "npm", names, seg, _urls(m.group(1))))
        elif m := JS_ADD.match(seg):
            mgr = seg.split()[0].lower() if not seg.lower().startswith("sudo") else seg.split()[1].lower()
            names = [d.name for d in parse_npm_command("npm install" + m.group(1))]
            out.append(InstallCall(mgr, "npm", names, seg, _urls(m.group(1))))
    return out
