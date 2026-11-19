"""
Faz 2 birim testleri: Pist veritabanı, öznitelik çıkarıcı ve tur tespit motoru.
"""

import pytest
from src.core.models import TelemetrySample, WheelSet
from src.processing.track_database import get_track_info
from src.processing.feature_extractor import extract_lap_features
from src.processing.lap_detector import LapDetector


def test_track_database():
    """Pistlerin dönüş yönü ve stres seviyesi sorgulamalarını test eder."""
    monza = get_track_info("monza")
    assert monza.direction == 1
    assert monza.stress_level == 2

    kyalami = get_track_info("kyalami")
    assert kyalami.direction == -1
    assert kyalami.stress_level == 4

    unknown = get_track_info("istanbul_park")
    assert unknown.direction == 1
    assert unknown.stress_level == 3


def test_feature_extractor():
    """extract_lap_features fonksiyonunun doğru ortalamalar ve sıcak basınçlar ürettiğini test eder."""
    cold_pressures = WheelSet(fl=24.0, fr=24.0, rl=24.0, rr=24.0)
    samples = []

    # 10 örnek oluştur
    for i in range(10):
        s = TelemetrySample(
            packet_id=i, speed_kmh=150.0, gear=4, rpms=6500, steer_angle=0.1,
            gas=0.8, brake=0.9 if i < 2 else 0.0, # İlk 2 kare sert fren
            acc_lateral_g=1.5, acc_longitudinal_g=0.2,
            pressures=WheelSet(fl=26.0 + (i * 0.05), fr=26.2, rl=25.9, rr=26.1),
            temperatures=WheelSet(80, 80, 80, 80),
            wheel_slip=WheelSet(0.08, 0.05, 0.07, 0.05),
            track_name="spa", car_model="ferrari_296_gt3",
            ambient_temp=24.0, track_temp=32.0,
            is_in_pit=False, completed_laps=1, current_lap_time_ms=120000
        )
        samples.append(s)

    summary = extract_lap_features(samples, cold_pressures)

    assert summary.lap_number == 1
    assert summary.avg_lateral_g == 1.5
    assert summary.hard_brake_duration_sec == 0.1 # 2 kare * 0.05s = 0.1s
    assert summary.avg_slip.fl == 0.08
    assert summary.delta_pressures.fl > 2.0 # 24.0'dan 26.x'e şişme

    # Boş örnek listesi ValueError fırlatmalı
    with pytest.raises(ValueError):
        extract_lap_features([], cold_pressures)


def test_lap_detector_lifecycle():
    """LapDetector'ın garaj -> pist -> tur tamamlama -> pit döngüsünü hatasız yakaladığını test eder."""
    detector = LapDetector()
    cold = WheelSet(fl=24.1, fr=24.3, rl=24.0, rr=24.2)

    # 1. Aşama: Garajda bekleme
    sample_pit = TelemetrySample(
        packet_id=1, speed_kmh=0.0, gear=0, rpms=1000, steer_angle=0.0,
        gas=0.0, brake=0.0, acc_lateral_g=0.0, acc_longitudinal_g=0.0,
        pressures=cold, temperatures=WheelSet(50, 50, 50, 50),
        wheel_slip=WheelSet(0, 0, 0, 0), track_name="monza", car_model="porsche_992_gt3_r",
        ambient_temp=22.0, track_temp=28.0, is_in_pit=True, completed_laps=0, current_lap_time_ms=0
    )
    res = detector.process_sample(sample_pit)
    assert res is None
    assert detector.cold_pressures == cold

    # 2. Aşama: Piste çıkış ve 0. turun sürülmesi (12 kare)
    for i in range(12):
        sample_track = TelemetrySample(
            packet_id=i + 2, speed_kmh=180.0, gear=5, rpms=7000, steer_angle=0.1,
            gas=0.9, brake=0.0, acc_lateral_g=1.4, acc_longitudinal_g=0.2,
            pressures=WheelSet(fl=26.5, fr=26.3, rl=26.2, rr=26.1),
            temperatures=WheelSet(82, 80, 81, 79), wheel_slip=WheelSet(0.06, 0.05, 0.06, 0.05),
            track_name="monza", car_model="porsche_992_gt3_r", ambient_temp=22.0, track_temp=28.0,
            is_in_pit=False, completed_laps=0, current_lap_time_ms=i * 5000
        )
        assert detector.process_sample(sample_track) is None

    # 3. Aşama: Finish çizgisini geçiş (completed_laps: 0 -> 1)
    finish_sample = TelemetrySample(
        packet_id=15, speed_kmh=230.0, gear=6, rpms=7800, steer_angle=0.0,
        gas=1.0, brake=0.0, acc_lateral_g=0.1, acc_longitudinal_g=0.5,
        pressures=WheelSet(fl=26.6, fr=26.4, rl=26.3, rr=26.2),
        temperatures=WheelSet(83, 81, 82, 80), wheel_slip=WheelSet(0.05, 0.04, 0.05, 0.04),
        track_name="monza", car_model="porsche_992_gt3_r", ambient_temp=22.0, track_temp=28.0,
        is_in_pit=False, completed_laps=1, current_lap_time_ms=105000
    )
    lap_summary = detector.process_sample(finish_sample)
    assert lap_summary is not None
    assert lap_summary.lap_number == 1
    assert lap_summary.avg_lateral_g > 0.0

    # 4. Aşama: Pite dönüş (Stint sonu)
    pit_entry_sample = TelemetrySample(
        packet_id=16, speed_kmh=45.0, gear=1, rpms=2500, steer_angle=0.0,
        gas=0.1, brake=0.2, acc_lateral_g=0.0, acc_longitudinal_g=-0.2,
        pressures=WheelSet(fl=26.6, fr=26.4, rl=26.3, rr=26.2),
        temperatures=WheelSet(80, 78, 79, 77), wheel_slip=WheelSet(0, 0, 0, 0),
        track_name="monza", car_model="porsche_992_gt3_r", ambient_temp=22.0, track_temp=28.0,
        is_in_pit=True, completed_laps=1, current_lap_time_ms=130000
    )
    detector.process_sample(pit_entry_sample)
    assert detector.just_entered_pit is True
    # Sıcak lastiklerle pite girildiğinde orijinal soğuk basınçlar ezilmemeli!
    assert detector.cold_pressures == cold


def test_lap_detector_ignores_zero_pressure_in_garage_menu():
    """ACC garaj menüsünde 0.0 PSI gelirken soğuk basıncın 0 olarak kilitlenmediğini doğrular."""
    detector = LapDetector()

    # Menüde 0.0 PSI geliyor
    menu_sample = TelemetrySample(
        packet_id=1, speed_kmh=0.0, gear=0, rpms=0, steer_angle=0.0,
        gas=0.0, brake=0.0, acc_lateral_g=0.0, acc_longitudinal_g=0.0,
        pressures=WheelSet(0.0, 0.0, 0.0, 0.0), temperatures=WheelSet(0, 0, 0, 0),
        wheel_slip=WheelSet(0, 0, 0, 0), track_name="paul_ricard", car_model="mclaren_720s_gt3_evo",
        ambient_temp=30.0, track_temp=38.0, is_in_pit=True, completed_laps=0, current_lap_time_ms=0,
    )
    detector.process_sample(menu_sample)
    assert detector.cold_pressures is None
    assert detector.stint_active is False

    # Drive'a basılıp piste çıkıldığında gerçek soğuk basınç kilitlenmeli
    drive_sample = TelemetrySample(
        packet_id=2, speed_kmh=60.0, gear=1, rpms=3000, steer_angle=0.0,
        gas=0.3, brake=0.0, acc_lateral_g=0.0, acc_longitudinal_g=0.1,
        pressures=WheelSet(24.5, 24.4, 24.6, 24.5), temperatures=WheelSet(70, 70, 70, 70),
        wheel_slip=WheelSet(0, 0, 0, 0), track_name="paul_ricard", car_model="mclaren_720s_gt3_evo",
        ambient_temp=30.0, track_temp=38.0, is_in_pit=False, completed_laps=0, current_lap_time_ms=1000,
    )
    detector.process_sample(drive_sample)
    assert detector.stint_active is True
    assert detector.cold_pressures == WheelSet(24.5, 24.4, 24.6, 24.5)

    # ESC -> Return to Garage (0.0 PSI) geldiğinde stint sıfırlanmalı
    detector.process_sample(menu_sample)
    assert detector.stint_active is False
    assert detector.cold_pressures is None
