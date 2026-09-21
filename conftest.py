"""Make the vendored serum-mcp importable for every test, in any collection order."""
import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parent / "vendor" / "serum-mcp" / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
