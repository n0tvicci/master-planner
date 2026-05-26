import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path


async def run_and_log(cmd: list[str], log_path: Path, cwd: str | None = None) -> None:
    """Run subprocess, write all stdout+stderr to log_path, append [DONE] when finished."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=cwd,
    )
    with log_path.open("w", encoding="utf-8", buffering=1) as f:
        async for line in proc.stdout:
            f.write(line.decode(errors="replace").rstrip() + "\n")
    await proc.wait()
    with log_path.open("a", encoding="utf-8") as f:
        f.write("[DONE]\n")


async def tail_log(log_path: Path, poll_interval: float = 0.1) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted lines from log_path. Stops when [DONE] is seen."""
    position = 0
    while True:
        if log_path.exists():
            with log_path.open("r", encoding="utf-8") as f:
                f.seek(position)
                content = f.read()
            if content:
                for line in content.splitlines():
                    if line == "[DONE]":
                        return
                    yield f"data: {line}\n\n"
                position += len(content.encode("utf-8"))
        await asyncio.sleep(poll_interval)
