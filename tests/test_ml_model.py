"""
MLPressurePredictor birim testleri: Veri temizliği ve 5+ tur makine öğrenmesi eğitimi.
"""

from src.core.models import LapSummary, WheelSet
from src.storage.db_manager import DatabaseManager
from src.predictor.ml_model import MLPressurePredictor


def _create_lap(lap_num: int, track: str, car: str, delta: float, valid: bool = True) -> LapSummary:
    """Test için kontrollü LapSummary nesnesi üretir."""
    return LapSummary(
        lap_number=lap_num,
        lap_time_ms=105000 if valid else 20000, # Geçersizse tur süresi çok kısa
        track_name=track,
        car_model=car,
        ambient_temp=22.0,
        track_temp=28.0,
        avg_lateral_g=1.4 if valid else 0.1,    # Geçersizse spin/düşük ivme
        avg_slip=WheelSet(0.06, 0.05, 0.07, 0.05),
        hard_brake_duration_sec=3.0,
        cold_pressures=WheelSet(24.0, 24.0, 24.0, 24.0),
        hot_pressures=WheelSet(24.0 + delta, 24.0 + delta, 24.0 + delta, 24.0 + delta),
    )


def test_data_sanitization_removes_corrupted_laps(tmp_path):
    """Veri temizleyicinin kaza ve anormal şişme turlarını ayıkladığını doğrular."""
    db = DatabaseManager(db_path=tmp_path / "test_clean.db")
    ml = MLPressurePredictor(target_hot_pressure=26.8)

    # 4 geçerli tur ekle (delta = 2.0)
    for i in range(1, 5):
        db.save_lap(_create_lap(i, "monza", "porsche_992_gt3_r", delta=2.0, valid=True))

    # 1 kaza/spin turu ekle (yanal G düşük, süre kısa)
    db.save_lap(_create_lap(5, "monza", "porsche_992_gt3_r", delta=2.0, valid=False))

    # 1 anormal şişme turu ekle (delta = 6.0 PSI)
    db.save_lap(_create_lap(6, "monza", "porsche_992_gt3_r", delta=6.0, valid=True))

    df = db.to_dataframe()
    assert len(df) == 6

    # Temizlenmiş veri yalnızca 4 geçerli turu içermeli
    clean_df = ml._sanitize_data(df)
    assert len(clean_df) == 4

    # 5 temiz tur olmadığı için henüz eğitilmemeli (fallback devrede olmalı)
    assert ml.train_from_dataframe(df) is False
    assert ml.is_trained is False


def test_ml_training_and_prediction_with_5_laps(tmp_path):
    """5 temiz tur sağlandığında ML modelinin başarıyla eğitilip tahmin yaptığını doğrular."""
    db = DatabaseManager(db_path=tmp_path / "test_5laps.db")
    ml = MLPressurePredictor(target_hot_pressure=26.8)

    # 5 temiz tur kaydet
    for i in range(1, 6):
        db.save_lap(_create_lap(i, "monza", "bmw_m4_gt3", delta=1.8, valid=True))

    df = db.to_dataframe()
    assert len(df) == 5

    # Eğit
    trained = ml.train_from_dataframe(df)
    assert trained is True
    assert ml.is_trained is True

    # Tahmin iste: Delta ~1.8 PSI öğrenildiği için Soğuk Basınç ~26.8 - 1.8 = 25.0 PSI civarında çıkmalı
    pred = ml.predict(
        track_name="monza",
        car_model="bmw_m4_gt3",
        ambient_temp=22.0,
        track_temp=28.0
    )
    assert 24.5 <= pred.fl <= 25.5
    assert 24.5 <= pred.rr <= 25.5
