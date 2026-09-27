"""SigNoz is gone and bin/idp-no-signoz-gate keeps it gone.

Founder, 2026-09-27: "remove signoz" and "don't let it come back". The gate reads every tracked
YAML/JSON/Terraform file Flux, CI or a template can ship, and refuses a deployable SigNoz
identifier. Each way it came in before is one case below, taken from what origin/main carried on
the day it was removed; history in comments and prose is not refused.
"""

import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "idp-no-signoz-gate"

CAME_BACK = {
    "chart": "spec:\n  chart:\n    spec:\n      chart: signoz\n",
    "repository": "spec:\n  url: https://charts.signoz.io\n",
    "image": "containers:\n  - image: signoz/signoz-otel-collector:0.111.5\n",
    "endpoint": "env:\n  - { name: OTEL_EXPORTER_OTLP_ENDPOINT, value: "
    "http://signoz-otel-collector.observability.svc:4318 }\n",
    "host": "links:\n  - url: https://signoz.${ESTATE_ZONE}\n",
    "list item": "records: [langfuse]\nnames:\n  - signoz\n",
    "clickhouse table": 'q: "SELECT count() FROM signoz_logs.distributed_logs_v2"\n',
    "shell in a workflow": 'run: |\n  check "signoz-otel-collector" "observability" "deploy"\n',
}

HISTORY = (
    "# The old signoz-otel-collector took 2.0 cores (b679856e).\n"
    "why: >-\n  Langfuse and SigNoz share one ClickHouse, measured 2026-09-07.\n"
    "reason: SigNoz ClickHouse 2026-09-08 (a new pod every ~40s).\n"
)


def _gate(tmp_path: pathlib.Path, files: dict[str, str]) -> subprocess.CompletedProcess:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for name, text in files.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    return subprocess.run([str(GATE), str(tmp_path)], capture_output=True, text=True)


@pytest.mark.parametrize("case", sorted(CAME_BACK))
def test_a_deployable_signoz_identifier_is_refused(tmp_path, case) -> None:
    out = _gate(tmp_path, {"platform/x/release.yaml": CAME_BACK[case]})
    assert out.returncode == 1, (case, out.stdout)
    assert "REFUSED platform/x/release.yaml" in out.stdout


def test_history_is_not_refused(tmp_path) -> None:
    out = _gate(tmp_path, {"platform/x/notes.yaml": HISTORY})
    assert out.returncode == 0, out.stdout


def test_outside_what_ships_is_not_read(tmp_path) -> None:
    out = _gate(tmp_path, {"docs/x.yaml": CAME_BACK["chart"]})
    assert out.returncode == 0, out.stdout


def test_this_repository_carries_none() -> None:
    out = subprocess.run([str(GATE), str(ROOT)], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout
