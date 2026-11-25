import sys

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles: print ✓ / Ge'ez safely
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from .cli import main  # noqa: E402
except ModuleNotFoundError as e:  # friendlier than a traceback on a fresh clone
    sys.exit(f"Missing Python package '{e.name}'. Install dependencies first:\n"
             f"    python -m pip install -r requirements.txt")

main()
