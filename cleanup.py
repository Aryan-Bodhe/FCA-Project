
#!/usr/bin/env python3

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent

# Directories to remove
DIRS_TO_REMOVE = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    "htmlcov",
    "build",
    "dist",
    "cache",
    "logs",
    ".coverage_cache",
}

# Files/patterns to remove
FILE_PATTERNS = [
    "*.pyc",
    "*.pyo",
    "*.log",
    ".coverage",
]

# Directories to never traverse
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

def cleanup():
    removed = 0

    for path in list(ROOT.rglob("*")):
        # Skip excluded directories
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue

        if not path.exists():
            continue

        if path.is_dir() and path.name in DIRS_TO_REMOVE:
            print(f"Removing directory: {path.relative_to(ROOT)}")
            shutil.rmtree(path)
            removed += 1
            continue

        if path.is_file() and any(path.match(p) for p in FILE_PATTERNS):
            print(f"Removing file: {path.relative_to(ROOT)}")
            path.unlink()
            removed += 1

    print(f"\nCleanup complete. Removed {removed} items.")

if __name__ == "__main__":
    cleanup()
