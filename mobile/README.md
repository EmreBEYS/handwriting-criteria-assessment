# Mobile Applications

- `ios/`: Swift + SwiftUI istemcisi (kullanıcı tarafından geliştirilecek)
- `android/`: Kotlin + Jetpack Compose istemcisi (ekip arkadaşı tarafından
  geliştirilecek)

İki istemci de aynı `/api/v1` OpenAPI sözleşmesini kullanır. Ortak akış; giriş,
akademik bağlam/sınav seçimi, seri kamera çekimi, kalite uyarısı, işlem kuyruğu,
tahmin doğrulama/düzeltme ve Excel indirmedir. Model ve PostgreSQL'e doğrudan
bağlanmazlar; tüm erişim backend üzerinden yapılır.

Mevcut iOS paketi gerçek kurum girişi, Keychain tabanlı oturum, token yenileme
ve ortak API için tip güvenli ağ temelini içerir. Tarama/inceleme ekranları bu
temelin üzerine bağlanmaktadır. Android uygulaması ayrı ekip çalışması olarak
eklenecektir.
