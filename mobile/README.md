# Mobile Applications

- `ios/`: Swift + SwiftUI istemcisi (kullanıcı tarafından geliştirilecek)
- `android/`: Kotlin + Jetpack Compose istemcisi (ekip arkadaşı tarafından
  geliştirilecek)

İki istemci de aynı `/api/v1` OpenAPI sözleşmesini kullanır. Ortak akış; giriş,
akademik bağlam/sınav seçimi, seri kamera çekimi, kalite uyarısı, işlem kuyruğu,
tahmin doğrulama/düzeltme ve Excel indirmedir. Model ve PostgreSQL'e doğrudan
bağlanmazlar; tüm erişim backend üzerinden yapılır.

Mevcut iOS paketi Home → Capture/Upload → Analysis → Results navigasyon
iskeletini içerir. Kamera, fotoğraf kitaplığı, ağ ve model bağlantıları henüz
aktif değildir. Android uygulaması ayrı ekip çalışması olarak eklenecektir.
