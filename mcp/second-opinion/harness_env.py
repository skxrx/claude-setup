"""Load harness.env from the claude-setup root; process env overrides file values."""
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def _load() -> dict:
    cfg = {}
    f = _ROOT / "harness.env"
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            cfg[k.strip()] = v.strip()
    return cfg


_FILE = _load()


def get(key: str, default: str = "") -> str:
    v = os.environ.get(key)
    if v is not None and v != "":
        return v
    v = _FILE.get(key)
    if v is not None and v != "":
        return v
    return default
