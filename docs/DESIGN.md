# Tasarım Notları

Bu belge, tahmin motorunun **şu an kodda gerçekte ne yaptığını** ve neyin henüz doğrulanmadığını anlatır.

## Temel fikir

Hedef sıcak basınç sabittir (GT3 için 26.8 PSI). Garajda girilecek soğuk basınç:

```
soğuk basınç = hedef sıcak basınç − beklenen şişme (ΔP)
```

Asıl iş ΔP'yi tahmin etmektir. ΔP, bir stint boyunca lastiğin soğuk halinden kararlı sıcak haline şişme miktarıdır.

## Veri akışı

```
ACC paylaşılan bellek -> LapDetector -> feature_extractor -> SQLite -> Predictor -> arayüz
```

- **LapDetector:** Garajdaki basıncı soğuk basınç olarak kilitler ("stint kilidi"). Pitte tek karede basınç
  `TYRE_CHANGE_JUMP_PSI` (0.5 PSI) veya daha fazla sıçrarsa yeni lastik takılmış sayılır ve yeni stint başlar.
- **feature_extractor:** Bir turu tek satıra indirir: ortalama yanal G, tekerlek başına ortalama slip,
  sert fren süresi (fren > %80), turun son %10'undan kararlı sıcak basınç, ΔP.

## İki tahmin motoru

| Koşul | Motor |
|---|---|
| Bu pistte 5'ten az temiz tur | `RuleBasedPredictor` (fizik kuralları) |
| Bu pistte en az 5 temiz tur | `MLPressurePredictor` (`RandomForestRegressor`) |

### Kural tabanlı motor

```
ΔP = pistin base_delta'sı
   + (pist sıcaklığı − 26) × 0.05 + (hava sıcaklığı − 20) × 0.05
   + max(0, yanal G − 1.3) × 0.4          (sürüş verisi varsa)
```

Tekerlek bazında ofsetler eklenir: pist yönü (sol/sağ, ±0.15 PSI) ve aracın motor yerleşimi (ön/arka).
Sabitler `rule_based.py`, pist değerleri `track_database.py`, araç değerleri `car_database.py` içindedir.

### Makine öğrenmesi motoru

Her tur 4 örneğe (tekerlek başına 1) dönüştürülür. Girdiler: hava ve pist sıcaklığı, pistin `base_delta`'sı ve yönü,
araç arka-ön ofseti, tekerlek ön/arka, viraj dışı taraf mı, yanal G, slip, sert fren süresi. Hedef: o tekerleğin ΔP'si.

### Veri temizliği

Eğitimden önce şu turlar elenir (`MLPressurePredictor._sanitize_data`):

- Herhangi bir tekerlekte ΔP, 0.8–4.0 PSI aralığının dışında
- Ortalama yanal G < 0.4 (spin, çok yavaş tur, pit turu)
- Tur süresi < 40 sn

## Bilinen sınırlamalar

- **Sabitler gerçek ACC verisiyle kalibre edilmedi.** `base_delta`, sıcaklık katsayısı ve araç ofsetleri başlangıç tahminleridir.
- **Setup bilgisi okunmuyor.** Fren kanalı, kamber gibi ayarlar paylaşılan bellekte yok. Etkileri yalnızca sıcaklık ve slip üzerinden dolaylı yansır.
- **Model pist bazlı eğitilir, araç bazlı değil.** Aynı pistte farklı araçlarla sürülürse veriler karışır (araç ofseti girdi olarak verilir ama ayrı model yok).
- **Windows okuyucusu (`shared_memory.py`) gerçek ACC ile doğrulanmadı.** Alan sırası ve pit/stint davranışı denenmelidir.
- **Out-lap ayrıca elenmiyor.** Lastik henüz ısınmadığı için ilk tur ΔP'yi düşük gösterebilir.
