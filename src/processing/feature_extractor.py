"""
Bir tur boyunca toplanan yüzlerce telemetri karesinden öznitelik (Feature) çıkaran modül.
Gürültülü anlık verileri tek bir temiz özet satırına (LapSummary) dönüştürür.
"""

from typing import List
from src.core.models import TelemetrySample, LapSummary, WheelSet


# Bir turdaki telemetri listesini analiz edip özet çıkaran fonksiyon
def extract_lap_features(samples: List[TelemetrySample], cold_pressures: WheelSet) -> LapSummary:
    """
    Tur içindeki anlık telemetri örneklerini özetler:
    - Ortalama yanal G kuvveti (Sürüş agresifliği)
    - 4 tekerleğin ortalama kayma (slip) oranları
    - Sert frenleme (>%80) süresi (Jant ve fren ısısı transferi)
    - Tur sonundaki kararlı sıcak lastik basınçları
    """
    if not samples:
        raise ValueError("Öznitelik çıkarmak için en az bir telemetri örneği gereklidir.")

    last_sample = samples[-1]
    sample_count = len(samples)

    # 1. Ortalama Yanal G (Mutlak değer ortalaması: Sağa veya sola fark etmeksizin viraj zorlaması)
    total_lateral_g = sum(abs(s.acc_lateral_g) for s in samples)
    avg_lateral_g = round(total_lateral_g / sample_count, 2)

    # 2. Ortalama Tekerlek Kayma Oranları (Slip)
    avg_slip_fl = sum(s.wheel_slip.fl for s in samples) / sample_count
    avg_slip_fr = sum(s.wheel_slip.fr for s in samples) / sample_count
    avg_slip_rl = sum(s.wheel_slip.rl for s in samples) / sample_count
    avg_slip_rr = sum(s.wheel_slip.rr for s in samples) / sample_count
    
    avg_slip = WheelSet(
        fl=round(avg_slip_fl, 3),
        fr=round(avg_slip_fr, 3),
        rl=round(avg_slip_rl, 3),
        rr=round(avg_slip_rr, 3),
    )

    # 3. Sert fren süresi (Fren > %80 olan karelerin toplam süresi)
    # 20 Hz örnekleme sıklığında her kare yaklaşık 0.05 saniyedir
    hard_brake_samples = sum(1 for s in samples if s.brake > 0.8)
    hard_brake_duration_sec = round(hard_brake_samples * 0.05, 1)

    # 4. Kararlı Sıcak Basınçlar:
    # Viraj anındaki anlık basınç sıçramalarından kaçınmak için turun son %10'unun ortalamasını alırız
    tail_size = max(1, int(sample_count * 0.1))
    tail_samples = samples[-tail_size:]
    
    hot_pressures = WheelSet(
        fl=round(sum(s.pressures.fl for s in tail_samples) / tail_size, 2),
        fr=round(sum(s.pressures.fr for s in tail_samples) / tail_size, 2),
        rl=round(sum(s.pressures.rl for s in tail_samples) / tail_size, 2),
        rr=round(sum(s.pressures.rr for s in tail_samples) / tail_size, 2),
    )

    return LapSummary(
        lap_number=last_sample.completed_laps,
        lap_time_ms=last_sample.last_lap_time_ms,  # Çizgi geçilince "son tur süresi" güncellenir
        track_name=last_sample.track_name,
        car_model=last_sample.car_model,
        ambient_temp=last_sample.ambient_temp,
        track_temp=last_sample.track_temp,
        avg_lateral_g=avg_lateral_g,
        avg_slip=avg_slip,
        hard_brake_duration_sec=hard_brake_duration_sec,
        cold_pressures=cold_pressures,
        hot_pressures=hot_pressures,
    )
