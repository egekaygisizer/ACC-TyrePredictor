"""
Fizik kurallarına dayalı tahmin motoru (veri yokken veya pistte < 5 tur varken kullanılır).

Mantık: Soğuk Basınç = Hedef Sıcak (26.8) - Beklenen Şişme (ΔP)
ΔP = Pist Taban Şişmesi (Monza: 1.6, Spa: 2.3 vb.) + Sıcaklık Sapması + Yön/Araç Dengesi + Sürüş Agresifliği
"""

from typing import Optional, Dict
from src.predictor.base import IPressurePredictor
from src.core.models import WheelSet
from src.core.config import TARGET_HOT_PRESSURE_GT3
from src.processing.track_database import get_track_info
from src.processing.car_database import get_rear_bias

TEMP_COEFF = 0.05           # Her 1 °C sıcaklık farkı için PSI etkisi
SIDE_BIAS_PSI = 0.15        # Viraj dışı kalan taraf lastiklerinin ekstra şişmesi
AGGRESSION_COEFF = 0.4      # 1.3 G üzerindeki her 1 G için ekstra PSI


# Kural tabanlı lastik basınç hesaplayıcı
class RuleBasedPredictor(IPressurePredictor):
    def __init__(self, target_hot_pressure: float = TARGET_HOT_PRESSURE_GT3):
        self.target_hot_pressure = target_hot_pressure

    def predict(
        self,
        track_name: str,
        car_model: str,
        ambient_temp: float,
        track_temp: float,
        driver_style: Optional[Dict[str, float]] = None,
    ) -> WheelSet:
        track = get_track_info(track_name)

        # 1. Ortak şişme: Piste özel taban şişme (Monza ~1.6, Spa ~2.3) + sıcaklık sapması
        # Referans kabul: 26°C pist / 20°C hava
        delta = track.base_delta
        delta += (track_temp - 26.0) * TEMP_COEFF + (ambient_temp - 20.0) * TEMP_COEFF
        
        # Sürüş stili varsa (yüksek yanal G ekstra sürtünme ısısı üretir)
        if driver_style and "avg_lateral_g" in driver_style:
            delta += max(0.0, driver_style["avg_lateral_g"] - 1.3) * AGGRESSION_COEFF

        # 2. Tekerlek bazlı ofsetler:
        # - Pist yönü (saat yönünde sol taraf viraj dışıdır, daha çok şişer)
        # - Araç motor yerleşimi (Porsche arka motorda arka lastikler daha çok şişer)
        left = SIDE_BIAS_PSI * track.direction
        rear = get_rear_bias(car_model)

        delta_fl = delta + left - (rear / 2.0)
        delta_fr = delta - left - (rear / 2.0)
        delta_rl = delta + left + (rear / 2.0)
        delta_rr = delta - left + (rear / 2.0)

        # 3. Soğuk basınç = hedef sıcak - beklenen şişme
        return WheelSet(
            fl=round(self.target_hot_pressure - delta_fl, 1),
            fr=round(self.target_hot_pressure - delta_fr, 1),
            rl=round(self.target_hot_pressure - delta_rl, 1),
            rr=round(self.target_hot_pressure - delta_rr, 1),
        )
