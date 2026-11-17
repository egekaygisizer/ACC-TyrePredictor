"""
src/core/models.py için birim testler.
"""

from src.core.models import WheelSet, LapSummary


def test_wheel_set_methods():
    """WheelSet nesnesinin sözlük ve liste dönüşümlerini test eder."""
    ws = WheelSet(fl=24.1, fr=24.3, rl=23.9, rr=24.2)
    d = ws.to_dict()
    assert d["FL"] == 24.1
    assert d["FR"] == 24.3

    ws_from_list = WheelSet.from_iterable([25.0, 25.1, 25.2, 25.3])
    assert ws_from_list.fl == 25.0
    assert ws_from_list.rr == 25.3


def test_lap_summary_auto_delta():
    """LapSummary nesnesinde delta_pressures'ın otomatik hesaplanmasını test eder."""
    cold = WheelSet(fl=24.0, fr=24.0, rl=24.0, rr=24.0)
    hot = WheelSet(fl=26.4, fr=26.7, rl=26.3, rr=26.5)

    summary = LapSummary(
        lap_number=1,
        lap_time_ms=105000,
        track_name="monza",
        car_model="porsche_992_gt3_r",
        ambient_temp=22.0,
        track_temp=30.0,
        avg_lateral_g=1.45,
        avg_slip=WheelSet(0.06, 0.05, 0.07, 0.06),
        hard_brake_duration_sec=3.2,
        cold_pressures=cold,
        hot_pressures=hot,
    )

    # Otomatik hesaplanan şişme miktarları (Sıcak - Soğuk)
    assert summary.delta_pressures.fl == 2.4
    assert summary.delta_pressures.fr == 2.7
    assert summary.delta_pressures.rl == 2.3
    assert summary.delta_pressures.rr == 2.5
