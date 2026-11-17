"""
Lastik basınç tahmin motorları için ortak arayüz (Strategy Pattern).
SOLID: Open/Closed - Yeni bir tahmin motoru eklemek mevcut kodu değiştirmeyi gerektirmez.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict
from src.core.models import WheelSet


# Tüm tahmin motorlarının uyması gereken sözleşme
class IPressurePredictor(ABC):

    @abstractmethod
    def predict(
        self,
        track_name: str,
        car_model: str,
        ambient_temp: float,
        track_temp: float,
        driver_style: Optional[Dict[str, float]] = None,
    ) -> WheelSet:
        """Hedef sıcak basınca ulaşmak için garajda girilmesi gereken 4 tekerlek soğuk basıncını döner."""
        pass
