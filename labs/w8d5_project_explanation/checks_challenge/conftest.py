import sys
from pathlib import Path

# the Markdown helpers are shared with the lab checks
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "checks"))
