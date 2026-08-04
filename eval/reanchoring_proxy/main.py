"""Portable frozen meta-archetype proxy for the SOT-2399 evaluation pool.

The policy is the repository champion pinned by the SOT-2399 manifest while
the deck is a separately frozen diversified archetype.  Keeping the adapter
small makes the opponent reproducible without depending on a sibling checkout.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location("sot_2399_frozen_champion", ROOT / "main.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load frozen champion proxy")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def agent(observation: dict[str, Any]) -> list[int]:
    """Delegate legal-action selection to the manifest-pinned champion."""
    return MODULE.agent(observation)
