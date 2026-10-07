"""
Pytest Configuration & Fixtures.
Ensures project root directory is present in sys.path before any test modules are collected.
"""

import sys
from pathlib import Path

# Explicitly ensure project root directory (exam-planner) is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
