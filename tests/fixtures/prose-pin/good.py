# must-pass fixture for the R76 prose_pin_scan gate: asserts grade parsed structure.
import pathlib

import yaml


def test_every_model_row_names_a_provider() -> None:
    doc = yaml.safe_load(pathlib.Path("some/config.yaml").read_text())
    rows = doc["model_list"]
    assert rows
    assert all(r["litellm_params"]["model"] for r in rows)
