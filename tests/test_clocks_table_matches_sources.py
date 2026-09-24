"""crew#716 CP2: verify the clocks table matches its sources."""

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BIN = str(ROOT / "bin" / "estate-clocks")

# Load the bin script using the same pattern as other tests
spec = importlib.util.spec_from_file_location(
    "estate_clocks", BIN, loader=SourceFileLoader("estate_clocks", BIN)
)
estate_clocks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(estate_clocks)


def test_render_matches_file():
    """The rendered output must match the file on disk."""
    output = estate_clocks.render(ROOT)
    clocks_md = ROOT / "docs" / "scheduling" / "CLOCKS.md"
    actual = clocks_md.read_text()
    assert output == actual, "run bin/estate-clocks"


def test_every_cronjob_file_appears():
    """Every CronJob file under platform/ must appear in the page."""
    output = estate_clocks.render(ROOT)
    platform_dir = ROOT / "platform"
    if not platform_dir.exists():
        return  # nothing to check

    for yaml_path in platform_dir.rglob("*.yaml"):
        # A tracked file that cannot be read is a failure, not a skip (silent-green class).
        content = yaml_path.read_text()

        for doc in yaml.safe_load_all(content):
            if doc is None:
                continue
            if doc.get("kind") != "CronJob":
                continue

            rel_path = str(yaml_path.relative_to(ROOT))
            assert rel_path in output, f"CronJob file {rel_path} not in page"


def test_every_schedule_job_appears():
    """Every job with a cron in scheduler/schedule.yml must appear in the page."""
    output = estate_clocks.render(ROOT)
    spec = ROOT / "scheduler" / "schedule.yml"
    if not spec.exists():
        return  # nothing to check

    data = yaml.safe_load(spec.read_text()) or {}
    jobs = data.get("jobs", {})

    for job_name, job_def in jobs.items():
        # Only check jobs that have a cron (i.e., are clocks)
        if job_def.get("cron"):
            assert job_name in output, f"Job {job_name} not in page"
