"""Root-level entry point — installs the package if needed, then runs the pipeline.

Usage:
    # Option A: run directly (adds src/ to path automatically)
    python run_pipeline.py

    # Option B: install as editable package, then use the CLI
    pip install -e .
    transcript-intelligence
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on the path so the package is importable without installation
SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from transcript_intelligence.pipeline import main  # noqa: E402

if __name__ == "__main__":
    main()
