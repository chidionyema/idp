# must-fail fixture for the executes gate: every assert reads this repository's own files back.
# The file it reads and the expectation it holds are the same statement written twice, so no
# defect can ever make this red. It starts nothing, opens nothing, calls nothing.
from pathlib import Path


def test_the_deployment_still_says_one_replica() -> None:
    yaml_text = Path("platform/jit/deployment.yaml").read_text()
    assert "replicas: 1" in yaml_text
