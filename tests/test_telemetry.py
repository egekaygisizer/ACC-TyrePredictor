"""
Telemetri katmanı (Mock, Shared Memory ve Factory) birim testleri.
"""

import sys

import pytest

from src.telemetry.base import ITelemetryProvider
from src.telemetry.mock_provider import MockTelemetryProvider
from src.telemetry.shared_memory import SharedMemoryProvider
from src.telemetry import create_telemetry_provider


def test_mock_telemetry_provider():
    """MockTelemetryProvider'ın gerçekçi TelemetrySample nesneleri ürettiğini doğrular."""
    provider = MockTelemetryProvider(track_name="monza", car_model="porsche_992_gt3_r")
    assert provider.is_connected() is True

    sample1 = provider.get_sample()
    assert sample1 is not None
    assert sample1.track_name == "monza"
    assert sample1.car_model == "porsche_992_gt3_r"
    assert 20.0 <= sample1.pressures.fl <= 30.0
    assert sample1.speed_kmh >= 0.0

    sample2 = provider.get_sample()
    assert sample2.packet_id > sample1.packet_id


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Windows'ta ACC açıksa gerçekten bağlanır")
def test_shared_memory_returns_none_without_acc():
    """Windows dışında SharedMemoryProvider çökmeden 'bağlı değil' demeli."""
    provider = SharedMemoryProvider()
    assert provider.is_connected() is False
    assert provider.get_sample() is None
    provider.close()  # Hata fırlatmamalı


def test_telemetry_factory():
    """create_telemetry_provider fonksiyonunun ortama göre doğru nesneyi ürettiğini doğrular."""
    # force_mock=True her zaman Mock döner
    mock_prov = create_telemetry_provider(force_mock=True)
    assert isinstance(mock_prov, MockTelemetryProvider)
    assert isinstance(mock_prov, ITelemetryProvider)
