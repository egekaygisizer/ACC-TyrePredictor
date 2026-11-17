"""
Uygulama genelinde kullanılan veri sınıfları (Domain Models).
SOLID: Single Responsibility - Her model yalnızca kendi verisini temsil eder.
"""

from dataclasses import dataclass, field
from typing import Dict


# 4 tekerlek (FL, FR, RL, RR) için ortak veri taşıyıcı
@dataclass
class WheelSet:
    fl: float = 0.0 # Ön Sol (Front-Left)
    fr: float = 0.0 # Ön Sağ (Front-Right)
    rl: float = 0.0 # Arka Sol (Rear-Left)
    rr: float = 0.0 # Arka Sağ (Rear-Right)

    def to_dict(self) -> Dict[str, float]:
        """Sözlük formatına dönüştürür."""
        return {"FL": self.fl, "FR": self.fr, "RL": self.rl, "RR": self.rr}

    @classmethod
    def from_iterable(cls, values):
        """4 elemanlı liste veya demetten nesne üretir."""
        vals = list(values)
        return cls(fl=vals[0], fr=vals[1], rl=vals[2], rr=vals[3])


# Tekil bir anlık telemetri okuması (Snapshot)
@dataclass
class TelemetrySample:
    packet_id: int
    speed_kmh: float
    gear: int
    rpms: int
    steer_angle: float
    gas: float
    brake: float
    acc_lateral_g: float     # Yanal ivme (viraj zorlaması)
    acc_longitudinal_g: float  # Boyuna ivme (hızlanma/fren)
    
    # 4 Tekerlek verileri
    pressures: WheelSet      # PSI cinsinden anlık basınçlar
    temperatures: WheelSet   # °C cinsinden çekirdek sıcaklıkları
    wheel_slip: WheelSet     # Tekerlek kayma oranları
    
    # Seans ve çevre bilgileri
    track_name: str
    car_model: str
    ambient_temp: float      # Hava sıcaklığı (°C)
    track_temp: float        # Pist sıcaklığı (°C)
    is_in_pit: bool          # Araç pitte / garajda mı?
    completed_laps: int      # Tamamlanan tur sayısı
    current_lap_time_ms: int # Anlık tur süresi (ms)
    last_lap_time_ms: int = 0  # Son tamamlanan turun süresi (ms)
    is_live: bool = True       # Oyun aktif sürüşte mi? (menü / replay / duraklatma değil)


# Tamamlanan bir turun özet analizi (Öznitelikler & Etiket)
@dataclass
class LapSummary:
    lap_number: int
    lap_time_ms: int
    track_name: str
    car_model: str
    ambient_temp: float
    track_temp: float
    
    # Sürüş tarzı metrikleri (Öznitelikler)
    avg_lateral_g: float     # Tur boyunca mutlak yanal G ortalaması
    avg_slip: WheelSet       # Tur boyunca 4 tekerleğin ortalama kayması
    hard_brake_duration_sec: float # Sert frenleme süresi (>%80 fren)
    
    # Basınç değerleri
    cold_pressures: WheelSet # Garajdan çıkarkenki başlangıç soğuk basınçları
    hot_pressures: WheelSet  # Tur sonundaki kararlı sıcak basınçlar
    delta_pressures: WheelSet = field(default_factory=WheelSet) # Sıcak - Soğuk farkı (Şişme)
    
    def __post_init__(self):
        """Eğer delta henüz hesaplanmadıysa otomatik hesapla."""
        if self.delta_pressures.fl == 0.0 and self.hot_pressures.fl != 0.0:
            self.delta_pressures = WheelSet(
                fl=round(self.hot_pressures.fl - self.cold_pressures.fl, 2),
                fr=round(self.hot_pressures.fr - self.cold_pressures.fr, 2),
                rl=round(self.hot_pressures.rl - self.cold_pressures.rl, 2),
                rr=round(self.hot_pressures.rr - self.cold_pressures.rr, 2),
            )
