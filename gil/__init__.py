"""Ghosts in the Loop: package hallucination as actions in Gemma 4 coding agents."""
import sys
from pathlib import Path

_TP = str(Path(__file__).resolve().parent.parent / "third_party")
if _TP not in sys.path:
    sys.path.insert(0, _TP)
