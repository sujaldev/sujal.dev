from pathlib import Path

__all__ = [
    "ROOT", "BUILD_DIR", "DIST_DIR",
]

ROOT = Path(__file__).parent.parent.resolve() / "src"
BUILD_DIR = ROOT / "build"
DIST_DIR = BUILD_DIR / "dist"
SITE_IGNORE = ".siteignore"
