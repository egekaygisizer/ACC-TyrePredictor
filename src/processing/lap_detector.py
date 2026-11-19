"""
Canlı telemetri akışından tur tamamlanmalarını ve pite dönüş anını yakalayan durum takipçisi (State Machine).

Stint kilidi: Araç piste çıkınca soğuk basınç kilitlenir; yarış içi pit stopta ezilmez.
Kilit, pitte basınç aniden değişirse (yeni lastik / yeni basınç girildi) açılır ve yeni stint başlar.
"""

from typing import Optional, List
from src.core.models import TelemetrySample, LapSummary, WheelSet
from src.core.config import TYRE_CHANGE_JUMP_PSI
from src.processing.feature_extractor import extract_lap_features


# Telemetri akışını izleyip tur bitişlerini ve pit durumunu tespit eden sınıf
class LapDetector:
    def __init__(self):
        self.last_completed_laps: int = 0
        self.last_is_in_pit: bool = True
        self.current_lap_samples: List[TelemetrySample] = []
        self.cold_pressures: Optional[WheelSet] = None
        self.just_entered_pit: bool = False
        self.stint_active: bool = False  # True iken soğuk basınç kilitlidir
        self._prev_pressures: Optional[WheelSet] = None

    def reset_stint(self) -> None:
        """Yeni stint / yeni seans için kilidi açar ve soğuk basıncı unutur."""
        self.stint_active = False
        self.cold_pressures = None
        self.current_lap_samples.clear()

    @staticmethod
    def _has_valid_pressures(pressures: WheelSet) -> bool:
        """ACC garaj menüsünde araç henüz yere inmemişken 0.0 PSI döner; bunu filtreler."""
        return min(pressures.fl, pressures.fr, pressures.rl, pressures.rr) > 1.0

    @staticmethod
    def _tyres_changed(prev: Optional[WheelSet], curr: WheelSet) -> bool:
        """Bir önceki kareye göre herhangi bir lastikte ani basınç sıçraması var mı?"""
        if prev is None:
            return False
        pairs = ((prev.fl, curr.fl), (prev.fr, curr.fr), (prev.rl, curr.rl), (prev.rr, curr.rr))
        return any(abs(c - p) >= TYRE_CHANGE_JUMP_PSI for p, c in pairs)

    def process_sample(self, sample: TelemetrySample) -> Optional[LapSummary]:
        """Her kareyi işler; yeni bir tur tamamlandıysa LapSummary, aksi halde None döner."""
        self.just_entered_pit = False

        # Araç garaj/setup menüsündeyken ACC 0.0 PSI gönderir: bu kareyi soğuk basınç sanma
        if not self._has_valid_pressures(sample.pressures):
            if self.stint_active:
                self.reset_stint()
            self._prev_pressures = None
            return None

        prev_pressures = self._prev_pressures
        self._prev_pressures = sample.pressures

        # 1. Garaj / Pit
        if sample.is_in_pit:
            if not self.last_is_in_pit:
                self.just_entered_pit = True

            # Pitte basınç sıçradıysa yeni lastik takılmıştır: yeni stint
            if self.stint_active and self._tyres_changed(prev_pressures, sample.pressures):
                self.reset_stint()

            # Stint başlamadıysa garajdaki değer (ne olursa olsun) soğuk basınçtır
            if not self.stint_active:
                self.cold_pressures = sample.pressures

            self.last_is_in_pit = True
            self.current_lap_samples.clear()
            self.last_completed_laps = sample.completed_laps
            return None

        # 2. Pistte: ilk karede soğuk basıncı kilitle
        self.last_is_in_pit = False
        if not self.stint_active:
            if self.cold_pressures is None:
                self.cold_pressures = sample.pressures
            self.stint_active = True

        self.current_lap_samples.append(sample)

        # 3. Çizgi geçildi mi?
        if sample.completed_laps > self.last_completed_laps:
            self.last_completed_laps = sample.completed_laps

            # Gürültüden kaçınmak için turda en az 10 kare olmalı
            if len(self.current_lap_samples) >= 10:
                summary = extract_lap_features(self.current_lap_samples, self.cold_pressures)
                self.current_lap_samples.clear()
                return summary

            self.current_lap_samples.clear()

        return None
