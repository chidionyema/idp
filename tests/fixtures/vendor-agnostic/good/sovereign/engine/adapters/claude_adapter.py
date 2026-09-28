"""A real vendor CLI wrapper, kept out of the engine's own files under adapters/, LAW 34."""


def run_claude_cli(task: str) -> str:
    return f"anthropic claude -p {task!r}"
