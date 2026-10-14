# Mobile Applications

## iOS — aktif 00-21 uygulaması

`ios/Package.swift` ile açılan SwiftUI uygulaması hesap veya backend gerektirmez.
VisionKit belge kamerası sayfa kenarlarını otomatik bulur ve perspektifi düzeltir;
Vision sabit şablondaki öğrenci adı, genel not ve dinamik soru puanı bölgelerini
cihazda okur. Belge kamerasındaki her sayfa ayrı kâğıt sayılır; kontrol ekranı
açılmadan aynı oturumun renkli Excel tablosuna yeni satır olarak eklenir.

Fiziksel cihaz uygulaması için `ios/HandwritingCriteriaAssessment.xcodeproj`
açılmalıdır. `Package.swift` yalnızca paket testleri içindir ve kamera demosunu
`My Mac` üzerinde çalıştırmaz.

Güven eşikleri:

- yeşil / yüksek: `>= 0.85`
- sarı / kontrol önerilir: `>= 0.60` ve `< 0.85`
- kırmızı / kontrol gerekli: `< 0.60`

Excel dosyasında renkler “Genel Güven” metniyle de desteklenir. Okunan genel not
ve hesaplanan soru toplamı ayrı sütunlardır; dosya nihai not onayı sayılmaz.

## Android

Bu repoda Android kodu yoktur. Android istemcisinin varlığı veya davranışı
00-21 iOS uygulamasında varsayılmaz.

## Legacy

`Sources/AppCore/Features`, `Navigation`, `Networking`, `ScanQueue` ve `Session`
00-20 hesap/backend mimarisinin tarihsel kodudur ve `Package.swift` tarafından
aktif hedeften hariç tutulur.
