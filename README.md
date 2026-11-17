# ACC Tyre Pressure Predict

Assetto Corsa Competizione (ACC) için, garajda girilmesi gereken **soğuk lastik basıncını** öneren bir telemetri asistanı.
Program ACC'nin paylaşılan belleğinden canlı veri okur, her turu SQLite'a kaydeder ve hava/pist sıcaklığı, pist, araç ve
sürüş stiline göre hedef sıcak basınca (GT3: 26.8 PSI) ulaşmak için gereken soğuk basıncı hesaplar.

> **Durum:** Geliştirme aşamasında. Windows'ta gerçek ACC ile doğrulama sürüyor, öneriler henüz kalibre edilmedi.
> Ayrıntılar için [docs/DESIGN.md](docs/DESIGN.md) ve [ROADMAP.md](ROADMAP.md).

## Nasıl çalışır?

1. ACC açıkken `main.py` çalıştırılır, ek ayar gerekmez.
2. Garajdaki basınç, piste çıkıldığı anda o stintin soğuk basıncı olarak kilitlenir.
3. Her tur bitince şişme (ΔP) hesaplanıp `data/sessions.db`'ye yazılır.
4. Bir pistte 5 temiz tur birikene kadar fizik kuralları, sonrasında o pistin verisiyle eğitilen bir
   `RandomForestRegressor` önerir.
5. Ekran, bir sonraki stint için garajda girilecek 4 lastiğin soğuk basıncını gösterir.

## Kurulum

Python 3.10+ gerekir.

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Kullanım

```bash
python main.py                 # Windows + ACC (gerçek veri)
python main.py --mock          # ACC'siz deneme (sahte telemetri, ayrı veritabanı)
python check_telemetry.py      # ACC'den okunan ham değerleri kontrol et
```

Gerçek ACC verisi yalnızca **Windows**'ta okunabilir. Diğer sistemlerde otomatik olarak sahte telemetri kullanılır.

## Testler

```bash
pytest
```

## Proje yapısı

```
main.py              Giriş noktası (canlı panel)
check_telemetry.py   Telemetri bağlantı kontrolü
src/
  core/              Veri modelleri ve ayarlar
  telemetry/         ACC paylaşılan bellek okuyucusu ve sahte sağlayıcı
  processing/        Tur tespiti, öznitelik çıkarma, pist ve araç bilgi bankaları
  storage/           SQLite kayıtları
  predictor/         Kural tabanlı ve ML tahmin motorları
  app/               Oturum denetleyicisi
  ui/                Rich terminal paneli
tests/               Birim testleri
docs/DESIGN.md       Tasarım notları
```

## Not

Bu proje bağımsız bir öğrenci projesidir; Kunos Simulazioni ile bir bağlantısı yoktur.
