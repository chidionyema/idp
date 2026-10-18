"""Put the server package on sys.path for root-collected runs.

bin/idp-tests-for and CI run pytest from the repo root; pytest inserts this tests/
directory, not its parent, so `import main` / `from harness import ...` resolve only
when the server dir itself is importable. Added with test_db_conn_commit.py, which was
the first test here to import `main` (fastapi/psycopg modules) and exposed that
test_harness.py had never actually been collected from the root at all.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
