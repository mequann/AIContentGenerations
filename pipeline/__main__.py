import sys

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles: print ✓ / Ge'ez safely
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .cli import main  # noqa: E402

main()
