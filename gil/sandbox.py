"""One throwaway Docker container per episode (python:3.12 + Node 22, see docker/Dockerfile).

The container holds nothing of value: no credentials, no mounted host folders except its own /work,
dropped capabilities, memory and CPU limits, deleted at the end of the episode. It needs the network to
reach the real PyPI and npm registries, which is the point of the study.
"""
from __future__ import annotations

import asyncio
import uuid

IMAGE = "gil-sandbox:latest"


class DockerSandbox:
    def __init__(self, image: str = IMAGE, memory: str = "2g", cpus: str = "1.0"):
        self.image, self.memory, self.cpus = image, memory, cpus
        self.name = f"gil-{uuid.uuid4().hex[:10]}"

    async def _docker(self, *args: str, timeout: int = 120) -> tuple[int, str]:
        proc = await asyncio.create_subprocess_exec("docker", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout)
        except asyncio.TimeoutError:
            proc.kill()
            raise
        return proc.returncode or 0, out.decode("utf-8", "replace")

    async def __aenter__(self) -> "DockerSandbox":
        code, out = await self._docker("run", "-d", "--rm", "--name", self.name, "--memory", self.memory, "--cpus", self.cpus,
                                       "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "512",
                                       "-w", "/work", self.image, "sleep", "infinity")
        if code:
            raise RuntimeError(f"sandbox failed to start: {out}")
        return self

    async def run(self, command: str, timeout: int) -> tuple[int, str]:
        try:
            return await self._docker("exec", self.name, "bash", "-lc", command, timeout=timeout)
        except asyncio.TimeoutError:
            await self._docker("exec", self.name, "pkill", "-f", "-9", ".", timeout=10)
            raise

    async def __aexit__(self, *exc: object) -> None:
        await self._docker("rm", "-f", self.name, timeout=60)
