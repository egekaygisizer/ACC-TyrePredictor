"""
ACC Lastik Basıncı Asistanı - giriş noktası.
Kullanım:  python main.py                  (Windows + ACC)
           python main.py --mock           (Mac / test: sahte telemetri)
           python main.py --target 26.9    (Sorulmadan hedef sıcak basıncı belirle)
"""

import argparse
import time

from rich.live import Live

from src.app.controller import SessionController
from src.core.config import (
    DATABASE_PATH,
    MOCK_DATABASE_PATH,
    TARGET_HOT_PRESSURE_GT3,
    TELEMETRY_POLL_INTERVAL_SEC,
)
from src.predictor.ml_model import MLPressurePredictor
from src.storage.db_manager import DatabaseManager
from src.telemetry import create_telemetry_provider
from src.telemetry.mock_provider import MockTelemetryProvider
from src.ui.console_view import ConsoleView


def prompt_target_pressure(default: float = TARGET_HOT_PRESSURE_GT3) -> float:
    """Uygulama başlangıcında kullanıcıdan hedef sıcak lastik basıncını (PSI) alır."""
    while True:
        try:
            raw = input(f"Hedef sıcak lastik basıncı (PSI) [Varsayılan {default} için Enter]: ").strip()
        except EOFError:
            return default

        if not raw:
            return default

        try:
            value = round(float(raw.replace(",", ".")), 2)
            if 20.0 <= value <= 35.0:
                return value
            print("Lütfen 20.0 ile 35.0 PSI arasında geçerli bir değer girin.")
        except ValueError:
            print("Geçersiz giriş. Örnek: 26.8 veya 26,5")


def main() -> None:
    parser = argparse.ArgumentParser(description="ACC Lastik Basıncı Asistanı")
    parser.add_argument("--mock", action="store_true", help="Sahte telemetri kullan (ACC gerekmez)")
    parser.add_argument("--target", type=float, default=None, help="Hedef sıcak basınç (PSI)")
    args = parser.parse_args()

    target_hot = args.target if args.target is not None else prompt_target_pressure()

    provider = create_telemetry_provider(force_mock=args.mock)
    is_mock = isinstance(provider, MockTelemetryProvider)
    db = DatabaseManager(MOCK_DATABASE_PATH if is_mock else DATABASE_PATH)
    predictor = MLPressurePredictor(target_hot_pressure=target_hot)
    controller = SessionController(provider, db, predictor)
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
