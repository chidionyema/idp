import pathlib

W = pathlib.Path(".github/workflows")


def test_every_caller_passes_the_seed_app() -> None:
    offenders = []
    for f in sorted(W.glob("*.yml")):
        t = f.read_text()
        if "./.github/actions/github-app-token" not in t:
            continue
        if "seed_app_id:" not in t or "seed_pem_b64:" not in t:
            offenders.append(f.name)
    assert offenders == [], f"callers passing only the retired OCI inputs: {offenders}"
