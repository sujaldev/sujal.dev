from pathlib import Path

__all__ = [
    "PROJECT_ROOT", "CONTENT_DIR", "SRC_DIR", "BUILD_DIR", "HASH_CACHE_FILE",
]

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
CONTENT_DIR = PROJECT_ROOT / "content"
SRC_DIR = PROJECT_ROOT / "ssg"
BUILD_DIR = PROJECT_ROOT / "build"
HASH_CACHE_FILE = PROJECT_ROOT / ".cache/hashes.csv"
