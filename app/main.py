"""
app/main.py — Entry point for:
    python -m app.main --story AT-3
    python -m app.main --prompt "Create Flask Todo Application"

Delegates entirely to the existing CLI in cli/main.py.
"""

import sys
import os

# Ensure the project root is on the path when invoked as a module
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from cli.main import main  # noqa: E402

if __name__ == "__main__":
    main()
