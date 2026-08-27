# ruff: noqa: I001, N999
"""Step 02 command entry: match C workbook rows to B workbook rows."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent.workflows.reconciliation.match_c_to_b import main


if __name__ == "__main__":
    main()
