# Mobile Applications

## iOS — aktif 00-22 uygulaması

`ios/Package.swift` ile açılan SwiftUI uygulaması hesap veya backend gerektirmez.
VisionKit belge kamerası sayfa kenarlarını otomatik bulur ve perspektifi düzeltir;
Vision sabit şablondaki öğrenci adını okur. Genel not ve dinamik soru puanı
bölgeleri cihazdaki `digit-crnn-v3.onnx` modeliyle, ONNX Runtime 1.24.2 üzerinden
okunur. Belge kamerasındaki her sayfa ayrı kâğıt sayılır ve aynı oturumun renkli
Excel tablosuna yeni satır olarak eklenir.

Fiziksel cihaz uygulaması için `ios/HandwritingCriteriaAssessment.xcodeproj`
açılmalıdır. `Package.swift` yalnızca paket testleri içindir ve kamera demosunu
`My Mac` üzerinde çalıştırmaz.

Güven eşikleri:

- yeşil / yüksek: `>= 0.85`
- sarı / kontrol önerilir: `>= 0.60` ve `< 0.85`
- kırmızı / kontrol gerekli: `< 0.60`

Modelin doğrulama kümesinde seçilmiş otomatik kabul eşiği `0.99`'dur. Bunun
altındaki ONNX tahminleri, boş hücreler, üstü çizilmiş düzeltmeler ve yazılı
toplam–soru toplamı uyuşmazlıkları öğretim elemanı kontrolü ister. Model veya
çalışma zamanı açılamazsa rakam alanları Apple Vision ile okunmaya devam eder;
bu teknik geri dönüşün güveni `0.59` ile sınırlandığı için kesin kabul edilmez.

Excel dosyasında renkler “Genel Güven” metniyle de desteklenir. Okunan genel not
ve hesaplanan soru toplamı ayrı sütunlardır; dosya nihai not onayı sayılmaz.

## Android

Bu repoda Android kodu yoktur. Android istemcisinin varlığı veya davranışı
00-21 iOS uygulamasında varsayılmaz.

## Legacy

`Sources/AppCore/Features`, `Navigation`, `Networking`, `ScanQueue` ve `Session`
00-20 hesap/backend mimarisinin tarihsel kodudur ve `Package.swift` tarafından
aktif hedeften hariç tutulur.

Model kökeni, ölçümler ve yeniden kullanım sınırları için
[`docs/sprint-00-22.md`](../docs/sprint-00-22.md) ve
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) okunmalıdır.
