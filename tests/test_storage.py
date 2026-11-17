"""
Faz 3 birim testleri: SQLite veritabanı yönetimi ve pist bazlı filtrelemeler.
"""

from src.core.models import LapSummary, WheelSet
from src.storage.db_manager import DatabaseManager


def _create_dummy_lap(lap_num: int, track: str) -> LapSummary:
    """Testler için sahte LapSummary nesnesi üretir."""
    return LapSummary(
        lap_number=lap_num,
        lap_time_ms=105000,
        track_name=track,
        car_model="porsche_992_gt3_r",
        ambient_temp=22.0,
        track_temp=30.0,
        avg_lateral_g=1.45,
        avg_slip=WheelSet(0.06, 0.05, 0.07, 0.06),
        hard_brake_duration_sec=3.2,
        cold_pressures=WheelSet(24.0, 24.2, 23.9, 24.1),
        hot_pressures=WheelSet(26.6, 26.5, 26.4, 26.2),
    )


def test_database_lifecycle_and_track_counts(tmp_path):
    """Veritabanına kayıt ekleme ve piste özel 5+ tur filtrelemesini test eder."""
    db_file = tmp_path / "test_sessions.db"
    db = DatabaseManager(db_path=db_file)

    assert db.get_lap_count() == 0

    # Monza için 5 tur kaydet
    for i in range(1, 6):
        db.save_lap(_create_dummy_lap(i, "monza"))

    # Spa için 2 tur kaydet
    for i in range(1, 3):
        db.save_lap(_create_dummy_lap(i, "spa"))

    # Toplam ve pist bazlı sorgulamalar
    assert db.get_lap_count() == 7
    assert db.get_lap_count("monza") == 5 # Monza'da 5+ tur kuralı karşılandı!
    assert db.get_lap_count("spa") == 2   # Spa'da henüz 2 tur var (< 5 tur fallback)
    assert db.get_lap_count("silverstone") == 0


def test_to_dataframe_filtering(tmp_path):
    """to_dataframe fonksiyonunun pist bazlı doğru filtreleme yaptığını doğrular."""
    db_file = tmp_path / "test_df.db"
    db = DatabaseManager(db_path=db_file)

    # 3 Monza, 1 Kyalami kaydet
    db.save_lap(_create_dummy_lap(1, "monza"))
    db.save_lap(_create_dummy_lap(2, "monza"))
    db.save_lap(_create_dummy_lap(3, "monza"))
    db.save_lap(_create_dummy_lap(1, "kyalami"))

    # Genel tablo
    df_all = db.to_dataframe()
    assert len(df_all) == 4
    assert "delta_fl" in df_all.columns
    assert "avg_lateral_g" in df_all.columns

    # Yalnızca Monza tablosu
    df_monza = db.to_dataframe(track_name="monza")
    assert len(df_monza) == 3
    assert all(df_monza["track_name"] == "monza")

    # Yalnızca Kyalami tablosu
    df_kyalami = db.to_dataframe(track_name="kyalami")
    assert len(df_kyalami) == 1
