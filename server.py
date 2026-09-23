"""Compatibility entry point for python server.py and server:app."""

import sys
from pathlib import Path

# Allow running a checkout before an editable install. Wheels use the package directly.
source = Path(__file__).resolve().parent / "src"
if source.is_dir():
    sys.path.insert(0, str(source))

from zscore_dashboard.serving.app import create_app, main  # noqa: E402

app = create_app()

if __name__ == "__main__":
    main()
