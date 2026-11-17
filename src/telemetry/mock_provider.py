"""
Mac ve Linux geliştirme ortamında ACC telemetrisini simüle eden sahte sağlayıcı.
Gerçekçi lastik ısınma eğrileri, tur zamanları ve viraj ivmeleri üretir.
"""

import time
import math
import random
from typing import Optional

from src.telemetry.base import ITelemetryProvider
from src.core.models import TelemetrySample, WheelSet


# ACC oyununun telemetri akışını taklit eden sınıf
class MockTelemetryProvider(ITelemetryProvider):
    def __init__(self, track_name: str = "monza", car_model: str = "porsche_992_gt3_r"):
        self.track_name = track_name
        self.car_model = car_model
        self.ambient_temp = 22.0
        self.track_temp = 29.5

        # Simülasyon sayaçları
        self.packet_id = 0
        self.start_time = time.time()
        self.lap_duration_sec = 10.0 # Testleri hızlandırmak için 10 saniyelik sanal tur
        self.completed_laps = 0
        self.in_pit = False

        # Başlangıç soğuk lastik basınçları (Garaj çıkış anı)
        self.cold_pressures = WheelSet(fl=24.2, fr=24.4, rl=24.0, rr=24.3)
        self.current_pressures = WheelSet(fl=24.2, fr=24.4, rl=24.0, rr=24.3)

    def is_connected(self) -> bool:
        """Mock sağlayıcı her zaman bağlı kabul edilir."""
        return True

    def get_sample(self) -> Optional[TelemetrySample]:
        """Fizik değişimlerini hesaplayarak anlık telemetri karesi döner."""
        self.packet_id += 1
        elapsed = time.time() - self.start_time

        # Tur ve pit durumu takibi
        lap_progress = (elapsed % self.lap_duration_sec) / self.lap_duration_sec
        current_lap = int(elapsed // self.lap_duration_sec)

        # 4 tur atıldıktan sonra pite girmiş gibi simüle et
        if current_lap >= 4:
            self.in_pit = True
        else:
            self.in_pit = False
            self.completed_laps = current_lap

        # Lastiklerin turlar geçtikçe ısınma ve şişme eğrisi (Gay-Lussac simülasyonu)
        warmup_factor = min(1.0, (elapsed / (self.lap_duration_sec * 3.0)))

        # Monza saat yönünde olduğu için sol lastikler daha çok ısınır ve şişer
        target_increase_fl = 2.6
        target_increase_fr = 2.2
        target_increase_rl = 2.5
        target_increase_rr = 2.1

        self.current_pressures = WheelSet(
            fl=round(self.cold_pressures.fl + (target_increase_fl * warmup_factor) + random.uniform(-0.02, 0.02), 2),
            fr=round(self.cold_pressures.fr + (target_increase_fr * warmup_factor) + random.uniform(-0.02, 0.02), 2),
            rl=round(self.cold_pressures.rl + (target_increase_rl * warmup_factor) + random.uniform(-0.02, 0.02), 2),
            rr=round(self.cold_pressures.rr + (target_increase_rr * warmup_factor) + random.uniform(-0.02, 0.02), 2),
        )

        # Viraj ve düzlük dinamikleri (Sinüs dalgasıyla pist virajları taklidi)
        is_cornering = math.sin(lap_progress * math.pi * 6) > 0.3
        lateral_g = abs(math.sin(lap_progress * math.pi * 6) * 1.8) if is_cornering else 0.1
        speed = 120.0 + math.cos(lap_progress * math.pi * 4) * 80.0
        brake = 0.9 if (not is_cornering and speed < 140.0) else 0.0

        return TelemetrySample(
            packet_id=self.packet_id,
            speed_kmh=round(speed, 1),
            gear=4,
            rpms=7200,
            steer_angle=0.2 if is_cornering else 0.0,
            gas=0.8 if not is_cornering else 0.3,
            brake=brake,
            acc_lateral_g=round(lateral_g, 2),
            acc_longitudinal_g=round(-1.2 if brake > 0.5 else 0.6, 2),
            pressures=self.current_pressures,
            temperatures=WheelSet(fl=82.0, fr=78.5, rl=84.0, rr=79.0),
            wheel_slip=WheelSet(fl=0.08, fr=0.05, rl=0.09, rr=0.06),
            track_name=self.track_name,
            car_model=self.car_model,
            ambient_temp=self.ambient_temp,
            track_temp=self.track_temp,
            is_in_pit=self.in_pit,
            completed_laps=self.completed_laps,
            current_lap_time_ms=int(lap_progress * self.lap_duration_sec * 1000),
            last_lap_time_ms=105000,  # Mock turları 10 sn sürer ama gerçekçi bir tur süresi bildirir
        )

    def close(self) -> None:
        """Mock sağlayıcıda temizlenecek bellek alanı yoktur."""
        pass
