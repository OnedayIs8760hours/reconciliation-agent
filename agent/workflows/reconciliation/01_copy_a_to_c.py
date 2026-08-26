# ruff: noqa: I001, N999
"""Step 01 command entry: copy A workbook to an initial C workbook draft."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent.workflows.reconciliation.copy_a_to_c import main


if __name__ == "__main__":
    main()
