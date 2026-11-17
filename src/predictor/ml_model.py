"""
Scikit-Learn tabanlı makine öğrenmesi (Random Forest Regressor) tahmin motoru.
Veri kalitesi filtreleme (Data Sanitization) ve pist bazlı 5+ tur hiyerarşisi içerir.
"""

from typing import Optional, Dict
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from src.predictor.base import IPressurePredictor
from src.predictor.rule_based import RuleBasedPredictor
from src.core.models import WheelSet
from src.core.config import TARGET_HOT_PRESSURE_GT3
from src.processing.track_database import get_track_info
from src.processing.car_database import get_rear_bias


# Makine öğrenmesiyle lastik şişme miktarını tahmin eden model
class MLPressurePredictor(IPressurePredictor):
    def __init__(self, target_hot_pressure: float = TARGET_HOT_PRESSURE_GT3):
        self.target_hot_pressure = target_hot_pressure
        self.fallback_predictor = RuleBasedPredictor(target_hot_pressure)
        self.model = RandomForestRegressor(n_estimators=40, random_state=42)
        self.is_trained: bool = False
        self.min_laps_to_train: int = 5 # En az 5 tur olmadan ML'e geçilmez

    def _sanitize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Kaza, spin veya geçersiz ısınma turlarını eğitim setinden temizler."""
        if df.empty:
            return df

        # 1. Aşırı uç şişme değerlerini ele (GT3'te şişme 0.8 ile 4.0 PSI arasında olmalıdır)
        valid_delta = (
            (df["delta_fl"] >= 0.8) & (df["delta_fl"] <= 4.0) &
            (df["delta_fr"] >= 0.8) & (df["delta_fr"] <= 4.0) &
            (df["delta_rl"] >= 0.8) & (df["delta_rl"] <= 4.0) &
            (df["delta_rr"] >= 0.8) & (df["delta_rr"] <= 4.0)
        )

        # 2. Spin atılmış veya aşırı yavaş turları ele (Yanal G > 0.4 olmalı)
        valid_driving = df["avg_lateral_g"] >= 0.4

        # 3. Geçersiz tur süresini ele (En az 40 saniyelik gerçek bir tur)
        valid_time = df["lap_time_ms"] >= 40000

        return df[valid_delta & valid_driving & valid_time].copy()

    def valid_lap_count(self, df: pd.DataFrame) -> int:
        """Temizlikten geçen (eğitimde kullanılabilir) tur sayısını döner."""
        return len(self._sanitize_data(df))

    def _prepare_wheel_features(self, df: pd.DataFrame):
        """Her tur kaydını 4 bağımsız tekerlek örneğine dönüştürür (1 tur = 4 veri noktası)."""
        X_rows = []
        y_rows = []

        for _, row in df.iterrows():
            track_info = get_track_info(row["track_name"])
            rear_bias = get_rear_bias(row["car_model"])

            base_features = {
                "ambient_temp": float(row["ambient_temp"]),
                "track_temp": float(row["track_temp"]),
                "track_base_delta": float(track_info.base_delta),
                "direction": float(track_info.direction),
                "rear_bias": float(rear_bias),
                "avg_lateral_g": float(row["avg_lateral_g"]),
                "hard_brake_duration": float(row["hard_brake_duration_sec"]),
            }

            # 4 Tekerlek için bağımsız öznitelik vektörleri oluştur
            # (tekerlek_adi, is_front, is_loaded_side, slip, delta)
            wheels_meta = [
                ("fl", 1.0, 1.0 if track_info.direction == 1 else 0.0, row["avg_slip_fl"], row["delta_fl"]),
                ("fr", 1.0, 1.0 if track_info.direction == -1 else 0.0, row["avg_slip_fr"], row["delta_fr"]),
                ("rl", 0.0, 1.0 if track_info.direction == 1 else 0.0, row["avg_slip_rl"], row["delta_rl"]),
                ("rr", 0.0, 1.0 if track_info.direction == -1 else 0.0, row["avg_slip_rr"], row["delta_rr"]),
            ]

            for _, is_front, is_loaded, slip, delta in wheels_meta:
                feat = [
                    base_features["ambient_temp"],
                    base_features["track_temp"],
                    base_features["track_base_delta"],
                    base_features["direction"],
                    base_features["rear_bias"],
                    is_front,
                    is_loaded,
                    base_features["avg_lateral_g"],
                    float(slip),
                    base_features["hard_brake_duration"],
                ]
                X_rows.append(feat)
                y_rows.append(float(delta))

        return X_rows, y_rows

    def train_from_dataframe(self, df: pd.DataFrame) -> bool:
        """Veritabanından gelen verileri temizler ve modeli eğitir."""
        clean_df = self._sanitize_data(df)

        # En az 5 geçerli temiz tur yoksa modeli eğitme (kural tabanlı devam et)
        if len(clean_df) < self.min_laps_to_train:
            self.is_trained = False
            return False

        X, y = self._prepare_wheel_features(clean_df)
        self.model.fit(X, y)
        self.is_trained = True
        return True

    def predict(
        self,
        track_name: str,
        car_model: str,
        ambient_temp: float,
        track_temp: float,
        driver_style: Optional[Dict[str, float]] = None,
    ) -> WheelSet:
        """Model eğitildiyse ML ile tahmin eder; eğitilmediyse kural tabanlı motora devreder."""
        if not self.is_trained:
            return self.fallback_predictor.predict(track_name, car_model, ambient_temp, track_temp, driver_style)

        track_info = get_track_info(track_name)
        rear_bias = get_rear_bias(car_model)
        style = driver_style or {}
        avg_lat_g = style.get("avg_lateral_g", 1.35)
        avg_slip = style.get("avg_slip", 0.06)
        hard_brake = style.get("hard_brake_duration", 3.0)

        # 4 Tekerlek için öznitelik vektörlerini hazırla
        # [amb, track, base_delta, dir, rear_bias, is_front, is_loaded, lat_g, slip, brake]
        feat_fl = [ambient_temp, track_temp, track_info.base_delta, track_info.direction, rear_bias, 1.0, 1.0 if track_info.direction == 1 else 0.0, avg_lat_g, avg_slip, hard_brake]
        feat_fr = [ambient_temp, track_temp, track_info.base_delta, track_info.direction, rear_bias, 1.0, 1.0 if track_info.direction == -1 else 0.0, avg_lat_g, avg_slip, hard_brake]
        feat_rl = [ambient_temp, track_temp, track_info.base_delta, track_info.direction, rear_bias, 0.0, 1.0 if track_info.direction == 1 else 0.0, avg_lat_g, avg_slip, hard_brake]
        feat_rr = [ambient_temp, track_temp, track_info.base_delta, track_info.direction, rear_bias, 0.0, 1.0 if track_info.direction == -1 else 0.0, avg_lat_g, avg_slip, hard_brake]

        deltas = self.model.predict([feat_fl, feat_fr, feat_rl, feat_rr])

        # Soğuk Basınç = Hedef Sıcak - Tahmin Edilen Şişme
        return WheelSet(
            fl=round(self.target_hot_pressure - deltas[0], 1),
            fr=round(self.target_hot_pressure - deltas[1], 1),
            rl=round(self.target_hot_pressure - deltas[2], 1),
            rr=round(self.target_hot_pressure - deltas[3], 1),
        )
