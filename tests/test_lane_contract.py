import importlib.util
import pathlib

P = pathlib.Path(__file__).resolve().parents[1] / "bin" / "verify_three_proofs.py"


def _mod():
    spec = importlib.util.spec_from_file_location("v3p", P)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_contract_names_the_bound_the_enforcer_uses() -> None:
    m = _mod()
    text = m.lane_contract()
    assert f"at most {m.MAX_FILES_PER_CHANGE} files" in text
