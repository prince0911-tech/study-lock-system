from __future__ import annotations

import sys
from pathlib import Path

from backend.services.watchdog import run_watchdog


def main() -> None:
    target = Path(sys.argv[1]).resolve()
    run_watchdog(target)


if __name__ == "__main__":
    main()
