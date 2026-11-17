"""
SQLite veritabanı yönetim servisi (Repository Pattern).
Tamamlanan turların özetlerini kaydeder, sorgular ve ML eğitimi için Pandas DataFrame döner.
"""

import sqlite3
from pathlib import Path
from typing import Optional
import pandas as pd

from src.core.config import DATABASE_PATH
from src.core.models import LapSummary


# Tur kayıtlarını SQLite üzerinde saklayan ve getiren servis sınıfı
class DatabaseManager:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DATABASE_PATH
        # Veri klasörü yoksa otomatik oluştur
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Veritabanı bağlantısı oluşturur."""
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        """Tablolar henüz yoksa oluşturur."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS laps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    lap_number INTEGER,
                    lap_time_ms INTEGER,
                    track_name TEXT,
                    car_model TEXT,
                    ambient_temp REAL,
                    track_temp REAL,
                    avg_lateral_g REAL,
                    avg_slip_fl REAL,
                    avg_slip_fr REAL,
                    avg_slip_rl REAL,
                    avg_slip_rr REAL,
                    hard_brake_duration_sec REAL,
                    cold_fl REAL,
                    cold_fr REAL,
                    cold_rl REAL,
                    cold_rr REAL,
                    hot_fl REAL,
                    hot_fr REAL,
                    hot_rl REAL,
                    hot_rr REAL,
                    delta_fl REAL,
                    delta_fr REAL,
                    delta_rl REAL,
                    delta_rr REAL
                )
            """)
            conn.commit()

    def save_lap(self, lap: LapSummary) -> int:
        """Tamamlanan bir turun özetini veritabanına ekler ve eklenen satır ID'sini döner."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO laps (
                    lap_number, lap_time_ms, track_name, car_model,
                    ambient_temp, track_temp, avg_lateral_g,
                    avg_slip_fl, avg_slip_fr, avg_slip_rl, avg_slip_rr,
                    hard_brake_duration_sec,
                    cold_fl, cold_fr, cold_rl, cold_rr,
                    hot_fl, hot_fr, hot_rl, hot_rr,
                    delta_fl, delta_fr, delta_rl, delta_rr
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lap.lap_number, lap.lap_time_ms, lap.track_name.lower().strip(), lap.car_model,
                lap.ambient_temp, lap.track_temp, lap.avg_lateral_g,
                lap.avg_slip.fl, lap.avg_slip.fr, lap.avg_slip.rl, lap.avg_slip.rr,
                lap.hard_brake_duration_sec,
                lap.cold_pressures.fl, lap.cold_pressures.fr, lap.cold_pressures.rl, lap.cold_pressures.rr,
                lap.hot_pressures.fl, lap.hot_pressures.fr, lap.hot_pressures.rl, lap.hot_pressures.rr,
                lap.delta_pressures.fl, lap.delta_pressures.fr, lap.delta_pressures.rl, lap.delta_pressures.rr
            ))
            conn.commit()
            return cursor.lastrowid

    def get_lap_count(self, track_name: Optional[str] = None) -> int:
        """
        Kayıtlı toplam tur sayısını döner.
        track_name verilirse sadece o pistteki tur sayısını döner (5+ tur kontrolü için).
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if track_name:
                cursor.execute("SELECT COUNT(*) FROM laps WHERE track_name = ?", (track_name.lower().strip(),))
            else:
                cursor.execute("SELECT COUNT(*) FROM laps")
            return cursor.fetchone()[0]

    def to_dataframe(self, track_name: Optional[str] = None) -> pd.DataFrame:
        """
        Kayıtları ML modelinin eğitilmesi için Pandas DataFrame formatında döner.
        track_name verilirse yalnızca o pistin verilerini filtreler.
        """
        with self._get_connection() as conn:
            if track_name:
                query = "SELECT * FROM laps WHERE track_name = ?"
                return pd.read_sql_query(query, conn, params=(track_name.lower().strip(),))
            else:
                query = "SELECT * FROM laps"
                return pd.read_sql_query(query, conn)
