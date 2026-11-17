"""
ACC Lastik Basıncı Asistanı - giriş noktası.
Kullanım:  python main.py          (Windows + ACC)
           python main.py --mock   (Mac / test: sahte telemetri)
"""

import argparse
import time

from rich.live import Live

from src.app.controller import SessionController
from src.core.config import DATABASE_PATH, MOCK_DATABASE_PATH, TELEMETRY_POLL_INTERVAL_SEC
from src.predictor.ml_model import MLPressurePredictor
from src.storage.db_manager import DatabaseManager
from src.telemetry import create_telemetry_provider
from src.telemetry.mock_provider import MockTelemetryProvider
from src.ui.console_view import ConsoleView


def main() -> None:
    parser = argparse.ArgumentParser(description="ACC Lastik Basıncı Asistanı")
    parser.add_argument("--mock", action="store_true", help="Sahte telemetri kullan (ACC gerekmez)")
    args = parser.parse_args()

    provider = create_telemetry_provider(force_mock=args.mock)
    is_mock = isinstance(provider, MockTelemetryProvider)
    db = DatabaseManager(MOCK_DATABASE_PATH if is_mock else DATABASE_PATH)
    controller = SessionController(provider, db, MLPressurePredictor())
    view = ConsoleView()

    # Ana döngü: oku -> işle -> çiz. Durdurmak için Ctrl+C
    with Live(view.render(controller.state), console=view.console, refresh_per_second=4) as live:
        try:
            while True:
                live.update(view.render(controller.update()))
                time.sleep(TELEMETRY_POLL_INTERVAL_SEC)
        except KeyboardInterrupt:
            pass
        finally:
            provider.close()


if __name__ == "__main__":
    main()
