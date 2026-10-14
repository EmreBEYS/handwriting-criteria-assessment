# 00-21 — Yerel Akıllı Sınav Kâğıdı Tarama

## Dayanak ve ürün yönü

12 Ekim 2026 danışman geri bildirimi, 00-20 sonunda hazırlanan hesap/JWT,
PostgreSQL ve sunucu merkezli akışı geçersiz kılmıştır. 00-21'in aktif ürünü
hesapsız, yerel çalışan iOS tarama demosudur. Eski backend ve veritabanı kodu
tarihsel izlenebilirlik için repoda tutulur fakat aktif iOS hedefine ve CI teslim
kapısına bağlı değildir.

## Uygulanan kapsam

1. VisionKit belge kamerası ile otomatik kenar algılama, kırpma ve perspektif düzeltme.
2. İnönü Sabit Sınav Şablonu v1 içinde öğrenci adı ve genel not alanları.
3. Aynı şablonda 1–12 arasında ayarlanabilen soru sayısı ve otomatik puan bölgeleri.
4. Her soru için düzenlenebilir azami puan ve PÇ kodu.
5. Apple Vision ile cihaz içi metin/rakam okuma; geçersiz veya aralık dışı puanda güven düşürme.
6. Okunan genel not ile soru puanlarının toplamını çapraz kontrol etme.
7. Belge kamerasında art arda çekilen her sayfayı ayrı sınav kâğıdı olarak okuma.
8. Sonuçları kontrol ekranı olmadan aynı oturum tablosuna yeni satır olarak ekleme.
9. Öğrenci adı, genel not ve soru puanlarını güven düzeyine göre yeşil, sarı veya kırmızı Excel hücresiyle işaretleme.
10. Öğrenci, soru–PÇ, puan, toplam ve güven bilgisini biçimlendirilmiş `.xlsx` çalışma kitabına aktarma.
11. Giriş ekranını, oturum bağımlılığını ve ağ yüklemesini aktif iOS derlemesinden çıkarma.

## Kapsam dışı / varsayılmayan

- Android kodu bu repoda olmadığı için değiştirilmedi veya test edilmiş sayılmadı.
- Gerçek el yazısı doğruluk oranı için veri bulunmadığından başarı yüzdesi iddia edilmedi.
- Birden fazla şablonun otomatik keşfi yapılmadı; her sayfa aynı seçili şablonla okunur.
- Harici servis veya kütüphane gerektirmeyen yerel `.xlsx` üretimi kullanıldı.
- Eski API/PostgreSQL kaynakları bu sprintte topluca silinmedi; aktif hedef dışına alındı.

## Sabit şablon sözleşmesi

Koordinatlar, düzeltilmiş dikey sayfaya göre sol üst başlangıçlı ve normalize
`0...1` aralığındadır. Şablon v1 öğrenci adını üst bilgi satırından, genel notu
sağ üst toplam hücresinden ve soru puanlarını sağdaki ardışık satırlardan okur.
Form tasarımı değişirse bu koordinatlar sürümlenmeden kullanılamaz.

## Güven politikası

| Aralık | Gösterge | Eylem |
|---|---|---|
| `>= 0.85` | Yeşil — Yüksek güven | Excel hücresi yeşil |
| `0.60...0.849` | Sarı — Kontrol önerilir | Excel hücresi sarı |
| `< 0.60` | Kırmızı — Kontrol gerekli | Excel hücresi kırmızı |

Genel not ile hesaplanan toplam ayrı sütunlarda tutulur. Renkler OCR güvenini
gösterir; nihai not onayı anlamına gelmez.

## Doğrulama

- Swift paketi macOS derleme kapısından geçti.
- Dört birim testi geçti: eşik sınırları, dinamik soru sayısı, yazılı/hesaplanan toplam ayrımı ve çok satırlı renkli Excel içeriği.
- Fiziksel iOS hedefi Xcode ile imzasız derleme kapısından geçti.
- Fiziksel cihaz kamerası ile gerçek şablon doğrulaması dış kapıdır.

## 00-22'ye bırakılanlar

- Danışman onaylı boş/dolu sınav örnekleriyle şablon koordinat kalibrasyonu
- Fiziksel iPhone ve iPad kamera testi
- El yazısı veri kümesiyle alan bazlı doğruluk ölçümü
- Android ekibiyle ortak şablon JSON'u ve eşik uyumluluğu
- Kurumun örnekleriyle Excel kolon ve renk düzeninin son kullanıcı doğrulaması
