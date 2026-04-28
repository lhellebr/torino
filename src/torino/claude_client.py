import json
import subprocess


def ask_claude(prompt: str) -> dict:
    result = subprocess.run(
        ["claude", "-p", "--output-format", "json", prompt],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude Code failed: {result.stderr.strip()}")
    return json.loads(result.stdout)
