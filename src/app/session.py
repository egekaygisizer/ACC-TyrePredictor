"""
Arayüzün çizdiği oturum durumu. Yalnızca veri taşır, iş mantığı içermez.
"""

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, List, Optional

from src.core.config import TARGET_HOT_PRESSURE_GT3
from src.core.models import LapSummary, TelemetrySample, WheelSet


# Programın oyunla ilişkisini özetleyen durumlar
class ConnectionStatus(Enum):
    WAITING_FOR_GAME = "Oyun bekleniyor (ACC'yi başlat)"
    NOT_LIVE = "Oyuna bağlı - sürüşte değil (menü / duraklatma / replay)"
    IN_PIT = "Garajda / pit yolunda"
    DRIVING = "Pistte - veri toplanıyor"


# Ekranda gösterilecek tüm bilgiler
@dataclass
class SessionState:
    laps_needed_for_ml: int
    target_hot_pressure: float = TARGET_HOT_PRESSURE_GT3
    status: ConnectionStatus = ConnectionStatus.WAITING_FOR_GAME
    sample: Optional[TelemetrySample] = None
    track_name: str = ""
    car_model: str = ""
    ambient_temp: float = 0.0
    track_temp: float = 0.0
    cold_pressures: Optional[WheelSet] = None   # Bu stint için belirlenen soğuk basınç
    cold_locked: bool = False                   # True: piste çıkıldı, değer kilitlendi
    recommended: Optional[WheelSet] = None      # Bir sonraki stint için önerilen soğuk basınç
    model_name: str = "-"
    valid_track_laps: int = 0                   # Bu pistte eğitime uygun temiz tur sayısı
    total_track_laps: int = 0                   # Bu pistte veritabanına kayıtlı toplam tur sayısı
    session_laps: List[LapSummary] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    events: Deque[str] = field(default_factory=lambda: deque(maxlen=8))
