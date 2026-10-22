"""Throwaway: does Modal accept a trivial job on free credits right now? No image build, no GPU."""
import modal

app = modal.App("yarn-probe")


@app.function(cpu=0.125, memory=128, timeout=30)
def ping() -> str:
    return "ok"


@app.local_entrypoint()
def main() -> None:
    print("PROBE", ping.remote())
