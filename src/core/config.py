"""
Uygulama genel yapılandırma ve varsayılan ayar sabitleri.
"""

from pathlib import Path

# Proje ana dizini
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Veri tabanı ve dosya yolları
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "sessions.db"
MOCK_DATABASE_PATH = DATA_DIR / "mock_sessions.db"  # Sahte veri gerçek sürüş geçmişine karışmasın

# ACC GT3 lastik hedef basınç değerleri (PSI)
TARGET_HOT_PRESSURE_GT3 = 26.8 # GT3 arabaları için ideal kuru zemin sıcak basınç hedefi
MIN_OPTIMAL_PRESSURE = 26.5    # Kabul edilebilir taban sıcak basınç
MAX_OPTIMAL_PRESSURE = 27.0    # Kabul edilebilir tavan sıcak basınç

# Telemetri okuma sıklığı
TELEMETRY_POLL_INTERVAL_SEC = 0.05 # 20 Hz okuma hızı (KISS ve düşük işlemci kullanımı)

# Pitte tek karede bu kadar PSI'den büyük basınç değişimi = yeni lastik takıldı / yeni basınç girildi
# Not: Varsayım; Windows'ta gerçek ACC ile doğrulanmalı
TYRE_CHANGE_JUMP_PSI = 0.5
