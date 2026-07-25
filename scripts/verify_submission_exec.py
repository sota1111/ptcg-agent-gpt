"""Verify the built submission under Kaggle's exec-style loading contract."""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ARCHIVE = REPO / "submission.tar.gz"
SMOKE_PROGRAM = """
import os
from pathlib import Path

agent_dir = Path(os.environ["KAGGLE_AGENT_DIR"])
namespace = {}
source = (agent_dir / "main.py").read_text()
exec(compile(source, "main.py", "exec"), namespace)
assert "__file__" not in namespace
assert len(namespace["agent"]({"select": None})) == 60
print("exec compatibility: PASS")
"""


def main() -> int:
    if not ARCHIVE.is_file():
        raise SystemExit(f"missing submission archive: {ARCHIVE}")

    with (
        tempfile.TemporaryDirectory(prefix="ptcg-submit-") as extracted_dir,
        tempfile.TemporaryDirectory(prefix="ptcg-cwd-") as unrelated_cwd,
        tarfile.open(ARCHIVE, "r:gz") as archive,
    ):
        archive.extractall(extracted_dir, filter="data")

        env = os.environ.copy()
        env["KAGGLE_AGENT_DIR"] = extracted_dir
        env.pop("PYTHONPATH", None)
        subprocess.run(
            [sys.executable, "-I", "-c", SMOKE_PROGRAM],
            cwd=unrelated_cwd,
            env=env,
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
