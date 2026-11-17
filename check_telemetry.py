"""
Telemetri bağlantı kontrolü: ACC'den okunan ham değerleri birkaç saniye ekrana basar.
Windows'ta ACC açıkken çalıştırıp değerleri oyundakilerle karşılaştır.

Kullanım:  python check_telemetry.py            (gerçek ACC, Windows)
           python check_telemetry.py --mock     (sahte veri)
"""

import argparse
import time

from src.telemetry import create_telemetry_provider


def main() -> None:
    parser = argparse.ArgumentParser(description="ACC telemetri bağlantı kontrolü")
    parser.add_argument("--mock", action="store_true", help="Sahte telemetri kullan")
    parser.add_argument("--seconds", type=int, default=10, help="Kaç saniye okunacağı")
    args = parser.parse_args()

    provider = create_telemetry_provider(force_mock=args.mock)
    try:
        for _ in range(args.seconds * 2):
            s = provider.get_sample()
            if s is None:
                print("ACC bulunamadı, bekleniyor...")
            else:
                print(
                    f"{s.track_name} | {s.car_model} | canlı={s.is_live} pit={s.is_in_pit} "
                    f"tur={s.completed_laps} son_tur={s.last_lap_time_ms}ms | "
                    f"hava={s.ambient_temp} pist={s.track_temp} | "
                    f"PSI {s.pressures.fl} {s.pressures.fr} {s.pressures.rl} {s.pressures.rr} | "
                    f"°C {s.temperatures.fl} {s.temperatures.fr} {s.temperatures.rl} {s.temperatures.rr}"
                )
            time.sleep(0.5)
    finally:
        provider.close()


if __name__ == "__main__":
    main()
