"""
Oturum denetleyicisi: her döngüde telemetriyi okur, turları kaydeder, modeli günceller
ve ekranın çizeceği SessionState'i üretir.
"""

import time
from typing import Optional

from src.app.session import ConnectionStatus, SessionState
from src.core.models import LapSummary, TelemetrySample, WheelSet
from src.predictor.ml_model import MLPressurePredictor
from src.processing.car_database import is_known_car
from src.processing.lap_detector import LapDetector
from src.processing.track_database import is_known_track
from src.storage.db_manager import DatabaseManager
from src.telemetry.base import ITelemetryProvider


def _fmt_wheels(ws: WheelSet, sign: bool = False) -> str:
    f = "+.2f" if sign else ".1f"
    return f"FL {ws.fl:{f}} | FR {ws.fr:{f}} | RL {ws.rl:{f}} | RR {ws.rr:{f}}"


# Telemetri -> tur tespiti -> veritabanı -> tahmin akışını yöneten sınıf
class SessionController:
    def __init__(
        self,
        provider: ITelemetryProvider,
        db: DatabaseManager,
        predictor: MLPressurePredictor,
        detector: Optional[LapDetector] = None,
    ):
        self.provider = provider
        self.db = db
        self.predictor = predictor
        self.detector = detector or LapDetector()
        self.state = SessionState(laps_needed_for_ml=predictor.min_laps_to_train)
        self._connected = False
        self._session_key = None          # (pist, araç): değişirse yeni seans başlar
        self._stint_was_locked = False
        self._rec_key = None              # Öneriyi gereksiz yere yeniden hesaplamamak için

    # ---------- Dışa açık tek giriş noktası ----------
    def update(self) -> SessionState:
        """Bir telemetri karesi işler ve güncel durumu döner."""
        sample = self.provider.get_sample()
        if sample is None:
            self._on_disconnected()
            return self.state

        if not self._connected:
            self._connected = True
            self._log("Oyuna bağlanıldı")

        self._check_new_session(sample)
        self._apply_sample(sample)

        if not sample.is_live:
            self.state.status = ConnectionStatus.NOT_LIVE
            return self.state

        lap = self.detector.process_sample(sample)
        self._update_stint_state(sample)
        if lap is not None:
            self._on_lap_completed(lap)
        self._refresh_recommendation(sample)
        return self.state

    # ---------- Yardımcılar ----------
    def _log(self, message: str) -> None:
        self.state.events.append(f"{time.strftime('%H:%M:%S')}  {message}")

    def _on_disconnected(self) -> None:
        if self._connected:
            self._log("Oyunla bağlantı koptu")
        self._connected = False
        self._session_key = None
        self.state.status = ConnectionStatus.WAITING_FOR_GAME
        self.state.sample = None

    def _check_new_session(self, sample: TelemetrySample) -> None:
        """Pist veya araç değiştiyse yeni seans başlatır."""
        key = (sample.track_name, sample.car_model)
        if key == self._session_key:
            return
        self._session_key = key
        self.detector.reset_stint()
        self._stint_was_locked = False
        self.state.session_laps.clear()
        self.state.cold_pressures = None
        self.state.cold_locked = False
        self.state.recommended = None

        self.state.warnings = []
        if not is_known_track(sample.track_name):
            self.state.warnings.append(f"Pist '{sample.track_name}' veritabanında yok, varsayılan değerler kullanılıyor")
        if not is_known_car(sample.car_model):
            self.state.warnings.append(f"Araç '{sample.car_model}' veritabanında yok, dengeli kabul ediliyor")

        self._log(f"Yeni seans: {sample.track_name} / {sample.car_model}")
        self._retrain(sample.track_name, announce=False)

    def _apply_sample(self, sample: TelemetrySample) -> None:
        s = self.state
        s.sample = sample
        s.track_name = sample.track_name
        s.car_model = sample.car_model
        s.ambient_temp = sample.ambient_temp
        s.track_temp = sample.track_temp

    def _update_stint_state(self, sample: TelemetrySample) -> None:
        s = self.state
        locked = self.detector.stint_active
        s.status = ConnectionStatus.IN_PIT if sample.is_in_pit else ConnectionStatus.DRIVING
        s.cold_pressures = self.detector.cold_pressures
        s.cold_locked = locked

        if self.detector.just_entered_pit:
            self._log("Pite girildi")
        if locked and not self._stint_was_locked and s.cold_pressures:
            self._log(f"Piste çıkıldı, bu stint için SOĞUK basınç kilitlendi: {_fmt_wheels(s.cold_pressures)}")
        if not locked and self._stint_was_locked:
            self._log("Yeni lastik / basınç algılandı, yeni stint başlıyor")
        self._stint_was_locked = locked

    def _on_lap_completed(self, lap: LapSummary) -> None:
        self.db.save_lap(lap)
        self.state.session_laps.append(lap)
        self._log(f"Tur {lap.lap_number} kaydedildi, şişme (ΔP): {_fmt_wheels(lap.delta_pressures, sign=True)}")
        self._retrain(lap.track_name, announce=True)

    def _retrain(self, track_name: str, announce: bool) -> None:
        """O pistin verileriyle modeli yeniden eğitir (yeterli temiz tur yoksa kural tabanlı kalır)."""
        df = self.db.to_dataframe(track_name)
        was_trained = self.predictor.is_trained
        self.predictor.train_from_dataframe(df)
        self.state.valid_track_laps = self.predictor.valid_lap_count(df)
        self._rec_key = None  # Öneriyi yeniden hesaplat
        if announce and self.predictor.is_trained and not was_trained:
            self._log("Yeterli tur birikti, makine öğrenmesi modeli devrede")

    def _refresh_recommendation(self, sample: TelemetrySample) -> None:
        """Koşullar veya model değiştiyse yeni soğuk basınç önerisi hesaplar."""
        laps = self.state.session_laps
        style = None
        if laps:
            last = laps[-1]
            slips = last.avg_slip
            style = {
                "avg_lateral_g": last.avg_lateral_g,
                "avg_slip": (slips.fl + slips.fr + slips.rl + slips.rr) / 4,
                "hard_brake_duration": last.hard_brake_duration_sec,
            }

        key = (sample.track_name, sample.car_model, round(sample.ambient_temp), round(sample.track_temp),
               len(laps), self.predictor.is_trained)
        if key == self._rec_key:
            return
        self._rec_key = key

        self.state.recommended = self.predictor.predict(
            sample.track_name, sample.car_model, sample.ambient_temp, sample.track_temp, style
        )
        trained = self.predictor.is_trained
        self.state.model_name = (
            "Makine öğrenmesi (bu pistin verisiyle)" if trained else "Kural tabanlı (fizik modeli)"
        )
