# Yol Haritası

## Durum

| Faz | İçerik | Durum |
|---|---|---|
| 1 | Telemetri katmanı: arayüz, sahte sağlayıcı, ACC paylaşılan bellek okuyucusu | ✅ Kod hazır, Windows'ta doğrulanacak |
| 2 | Tur tespiti, stint kilidi, öznitelik çıkarma, pist ve araç bilgi bankaları | ✅ |
| 3 | SQLite kaydı, pist bazlı sorgu | ✅ |
| 4 | Kural tabanlı ve ML tahmin motorları, veri temizliği | ✅ Sabitler kalibre edilecek |
| 5 | Canlı terminal paneli, `main.py` | ✅ |
| 6 | Windows'ta gerçek ACC ile doğrulama ve kalibrasyon | ⏳ Sırada |

## Sıradaki işler

- [ ] `check_telemetry.py` ile okunan değerleri oyundakilerle karşılaştır (basınç, sıcaklık, hava/pist, tur süresi).
- [ ] Pist ve araç adlarının ACC'nin verdiği adlarla eşleştiğini doğrula, eksikleri ekle.
- [ ] Pit stop ve yeni lastik algılamasını (`TYRE_CHANGE_JUMP_PSI`) gerçek oyunda dene.
- [ ] Birkaç pistte gerçek ΔP değerlerini topla, `base_delta` ve sıcaklık katsayılarını kalibre et.
- [ ] Out-lap'i (ısınma turu) eğitim verisinden ele.
- [ ] Modeli araç bazında ayırmayı değerlendir.
- [ ] Setup bilgisinin (fren kanalı vb.) etkisini ölç; gerekirse isteğe bağlı giriş ekle.

## Teknoloji

| Kütüphane | Kullanım |
|---|---|
| `ctypes` | ACC paylaşılan belleğini okumak (Windows) |
| `sqlite3` | Tur kayıtları |
| `pandas`, `numpy` | Veri hazırlama |
| `scikit-learn` | `RandomForestRegressor` |
| `rich` | Terminal paneli |
| `pytest` | Testler |

## Mimari ilkeler

SOLID ve KISS: telemetri kaynağı (`ITelemetryProvider`) ve tahmin motoru (`IPressurePredictor`) arayüzler arkasında,
böylece Mac'te sahte veri, Windows'ta gerçek veri; kural tabanlı veya ML motoru aynı kodla kullanılabilir.
Dosya yapısı için [README.md](README.md), tahmin mantığı için [docs/DESIGN.md](docs/DESIGN.md).
