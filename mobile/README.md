# Mobile Applications

- `ios/`: Swift + SwiftUI istemcisi (kullanıcı tarafından geliştirilecek)
- `android/`: Kotlin + Jetpack Compose istemcisi (ekip arkadaşı tarafından
  geliştirilecek)

İki istemci de aynı `/api/v1` OpenAPI sözleşmesini kullanır. Ortak akış; giriş,
akademik bağlam/sınav seçimi, seri kamera çekimi, kalite uyarısı, işlem kuyruğu,
tahmin doğrulama/düzeltme ve Excel indirmedir. Model ve PostgreSQL'e doğrudan
bağlanmazlar; tüm erişim backend üzerinden yapılır.

Mevcut iOS paketi gerçek kurum girişi, Keychain tabanlı oturum, token yenileme,
ders/sınav seçimi, kamera veya fotoğraf yükleme, kuyruk takibi ve insan
incelemesiyle atomik kayıt akışını içerir. Koyu zemin, turkuaz/açık mavi vurgu,
yuvarlatılmış kartlar ve erişilebilir durum göstergelerinden oluşan ortak bir
İnönü mobil görsel dili girişten sonuç ekranına kadar uygulanır.
`HCA_API_BASE_URL` Xcode şemasında
telefonun erişebildiği backend adresine ayarlanmalıdır. Kamera için uygulama
target'ına `NSCameraUsageDescription` eklenmelidir. Android uygulaması ayrı ekip
çalışması olarak eklenecektir.

Onay ekranından sonra istemci sınavın yetkili PÇ analizini yeniden yükler. Ağ
hatasında PÇ isteği bağımsız olarak tekrar denenebilir; onay isteği tekrarlanmaz.
Yükleme tekrarlarında aynı `client_request_id` korunarak backend'in mükerrerlik
koruması kullanılır. Fiziksel cihaz, canlı PostgreSQL ve nesne deposu kontrol
adımları için [`../docs/sprint-00-16.md`](../docs/sprint-00-16.md) belgesine bakın.
