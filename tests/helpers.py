import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "py_modules"))
sys.path.insert(0, str(ROOT))


class Clock:
    def __init__(self, t=100.0):
        self.t = t

    def __call__(self):
        return self.t
