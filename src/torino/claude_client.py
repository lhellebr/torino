import json
import subprocess


def ask_claude(
    prompt: str,
    allowed_tools: list[str] | None = None,
    timeout: int = 180,
) -> str:
    cmd = ["claude", "-p", "--output-format", "json"]
    if allowed_tools:
        cmd.extend(["--allowedTools", ",".join(allowed_tools)])
    cmd.append("-")

    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude Code failed: {result.stderr.strip()}")

    response = json.loads(result.stdout)
    return response.get("result", "")
