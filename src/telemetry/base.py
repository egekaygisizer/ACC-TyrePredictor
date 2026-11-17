"""
Telemetri veri sağlayıcıları için soyut taban arayüz (Interface).
SOLID: Dependency Inversion Prensibi - Üst modüller doğrudan donanım/işletim sistemine değil, bu arayüze bağımlıdır.
"""

from abc import ABC, abstractmethod
from typing import Optional
from src.core.models import TelemetrySample


# Telemetri sağlayıcılar için ortak arayüz sınıfı
class ITelemetryProvider(ABC):

    @abstractmethod
    def is_connected(self) -> bool:
        """Veri kaynağına (ACC veya Mock) bağlı olup olmadığını kontrol eder."""
        pass

    @abstractmethod
    def get_sample(self) -> Optional[TelemetrySample]:
        """Anlık telemetri karesini çeker, oyun açık değilse None döner."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Bağlantıyı ve açık olan bellek kaynaklarını serbest bırakır."""
        pass
