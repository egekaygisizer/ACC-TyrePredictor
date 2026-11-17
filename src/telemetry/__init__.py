"""
Telemetri sağlayıcı üretim fabrikası (Factory Pattern).
"""

import sys
from src.telemetry.base import ITelemetryProvider
from src.telemetry.mock_provider import MockTelemetryProvider
from src.telemetry.shared_memory import SharedMemoryProvider


def create_telemetry_provider(force_mock: bool = False) -> ITelemetryProvider:
    """Windows'ta gerçek ACC okuyucusunu, diğer sistemlerde (veya force_mock ile) sahte sağlayıcıyı döner."""
    if force_mock or not sys.platform.startswith("win"):
        return MockTelemetryProvider()
    return SharedMemoryProvider()
