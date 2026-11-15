"""The licence files published with the Express middleware match the repository's.

The middleware is published from middleware/express, so it keeps its own copies
of LICENSE and NOTICE.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIDDLEWARE = ROOT / "middleware" / "express"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_middleware_licence_files_match_the_repository():
    for name in ("LICENSE", "NOTICE"):
        assert _text(MIDDLEWARE / name) == _text(ROOT / name), name


def test_middleware_package_lists_the_licence_files():
    files = json.loads(_text(MIDDLEWARE / "package.json"))["files"]
    assert "LICENSE" in files
    assert "NOTICE" in files
