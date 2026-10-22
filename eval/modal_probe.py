"""Throwaway: does Modal accept one 0.125-core job now? Prints the exact refusal if not."""

import datetime as dt

import modal

app = modal.App("yarngpt2-probe")


@app.function(cpu=0.125, memory=128, timeout=30)
def ping() -> str:
    return "pong"


print("PROBE at", dt.datetime.now(dt.UTC).isoformat())
try:
    with modal.enable_output(), app.run():
        print("PROBE result", ping.remote())
except Exception as exc:  # noqa: BLE001 -- a probe: say what happened
    print("PROBE refused", type(exc).__name__, str(exc)[:600])
