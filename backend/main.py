from __future__ import annotations

from backend.api.server import run_api
from backend.app_controller import AppController


def main() -> None:
    controller = AppController()
    run_api(controller)


if __name__ == "__main__":
    main()
