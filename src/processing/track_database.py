"""
ACC pistlerinin dönüş yönü, stres seviyesi ve pist bazlı taban lastik şişme (base_delta) bilgi bankası.
Düşük enerjili pistlerde (Monza ~1.6 PSI) ve yüksek enerjili pistlerde (Spa ~2.3 PSI) gerçekçi taban sağlar.
"""

from dataclasses import dataclass
from typing import Dict


# Pist karakteristik veri yapısı
@dataclass(frozen=True)
class TrackInfo:
    name: str
    direction: int     # 1: Saat yönü (Clockwise - sol lastikler daha çok şişer), -1: Ters (Counter-Clockwise)
    stress_level: int  # 1 (Düşük) ile 5 (Çok Yüksek lastik yükü)
    base_delta: float  # Referans hava şartlarında (20°C hava / 26°C pist) beklenen taban şişme miktarı (PSI)


# ACC'de yer alan GT3 pistlerinin gerçekçi lastik şişme parametreleri
TRACKS: Dict[str, TrackInfo] = {
    # --- DÜŞÜK ENERJİLİ / DÜZLÜK AĞIRLIKLI PİSTLER ---
    "monza": TrackInfo(name="monza", direction=1, stress_level=2, base_delta=1.6),
    "paul_ricard": TrackInfo(name="paul_ricard", direction=1, stress_level=3, base_delta=1.8),
    "indianapolis": TrackInfo(name="indianapolis", direction=1, stress_level=3, base_delta=1.8),
    "hungaroring": TrackInfo(name="hungaroring", direction=1, stress_level=3, base_delta=1.9),
    "imola": TrackInfo(name="imola", direction=-1, stress_level=3, base_delta=1.9),
    "valencia": TrackInfo(name="valencia", direction=-1, stress_level=3, base_delta=1.9),

    # --- ORTA ENERJİLİ PİSTLER ---
    "nurburgring": TrackInfo(name="nurburgring", direction=1, stress_level=4, base_delta=2.0),
    "misano": TrackInfo(name="misano", direction=1, stress_level=4, base_delta=2.0),
    "mount_panorama": TrackInfo(name="mount_panorama", direction=1, stress_level=4, base_delta=2.0),
    "barcelona": TrackInfo(name="barcelona", direction=1, stress_level=4, base_delta=2.1),
    "brands_hatch": TrackInfo(name="brands_hatch", direction=1, stress_level=4, base_delta=2.1),
    "kyalami": TrackInfo(name="kyalami", direction=-1, stress_level=4, base_delta=2.1),
    "laguna_seca": TrackInfo(name="laguna_seca", direction=-1, stress_level=4, base_delta=2.1),

    # --- YÜKSEK ENERJİLİ / SÜREKLİ YANAL YÜK PİSTLERİ ---
    "zandvoort": TrackInfo(name="zandvoort", direction=1, stress_level=5, base_delta=2.2),
    "cota": TrackInfo(name="cota", direction=-1, stress_level=4, base_delta=2.2),
    "watkins_glen": TrackInfo(name="watkins_glen", direction=1, stress_level=4, base_delta=2.2),
    "spa": TrackInfo(name="spa", direction=1, stress_level=5, base_delta=2.3),
    "silverstone": TrackInfo(name="silverstone", direction=1, stress_level=5, base_delta=2.3),
    "suzuka": TrackInfo(name="suzuka", direction=1, stress_level=5, base_delta=2.4),
}


# Pist adına göre TrackInfo getiren yardımcı fonksiyon
def get_track_info(track_name: str) -> TrackInfo:
    """Bilinmeyen bir pist durumunda ortalama değerler döner."""
    normalized = track_name.lower().replace(" ", "_").strip()
    return TRACKS.get(normalized, TrackInfo(name=track_name, direction=1, stress_level=3, base_delta=2.0))


# Pistin veritabanında tanımlı olup olmadığını döner (arayüzde uyarı göstermek için)
def is_known_track(track_name: str) -> bool:
    return track_name.lower().replace(" ", "_").strip() in TRACKS
