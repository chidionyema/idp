"""A stray vendor name that must never reach the workflow file."""


def step(runner: str) -> str:
    if runner == "claude":
        return "special-cased for anthropic's CLI"
    return runner
