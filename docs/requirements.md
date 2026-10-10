# 00-01 — Gereksinimler

## 1. Amaç ve Başarı Ölçütü

Sistem, yetkili öğretim elemanının bir sınava ait kâğıtları mobil kamerayla seri
okutmasını, model çıktısını doğrulamasını, soru puanlarını güvenli biçimde
kaydetmesini ve PÇ analizini Excel olarak almasını sağlar.

İlk sürüm başarılı sayılırsa öğretim elemanı tanımlı bir sınav için en az bir
kâğıdı baştan sona işleyebilir; dinamik soru puanları onaydan sonra doğru sınav
ve öğrenciyle ilişkili saklanır; aynı yükleme yinelendiğinde ikinci kayıt oluşmaz;
PÇ hesabı onaylı puanlardan yeniden üretilebilir.

## 2. Roller

| Rol | Yetki |
|---|---|
| Kurum yöneticisi | Kullanıcı, program, ders, öğrenci ve ders atamalarını yönetir |
| Öğretim elemanı | Atandığı ders/sınavı tanımlar, kâğıt okur, sonucu düzeltip onaylar, rapor alır |
| Sistem/worker | Görüntüyü işler, tahmin ve güven skoru üretir; nihai onay vermez |

Öğrenci ilk sürümde uygulama kullanıcısı değildir.

## 3. Kapsam

### İlk sürüme dahil

- Kurum hesabıyla güvenli giriş ve çıkış
- Akademik yıl, Güz/Bahar, ders ve sınav türü seçimi
- Vize, Final ve Bütünleme sınavı tanımı
- Sınava dinamik sayıda soru ve azami puan ekleme
- Her soruyu bir veya daha fazla PÇ'ye ağırlıkla bağlama
- iOS kameradan seri kâğıt gönderimi
- Görüntü kalite kontrolü ve yeniden çekim uyarısı
- Öğrenci numarası, soru puanları ve model güveninin çıkarılması
- Kullanıcı doğrulaması/düzeltmesi ve atomik kayıt
- “Okundu ve kaydedildi” durumu
- Sınav, soru, öğrenci ve PÇ bazlı analiz
- `.xlsx` dışa aktarma
- Denetim kaydı ve yetki kontrolü

### İlk sürüme dahil değil

- Notların öğrenci bilgi sistemine otomatik gönderilmesi
- Öğrencinin kendi sonucunu gördüğü portal
- İnternet olmadan tam model çalıştırma
- Kompozisyonun anlamsal/doğruluk değerlendirmesi
- Öğretim elemanı onayı olmadan nihai not verme

## 4. Fonksiyonel Gereksinimler

| Kimlik | Gereksinim | Kabul ölçütü |
|---|---|---|
| FR-001 | Kullanıcı kendi hesabıyla giriş yapmalıdır. | Geçerli hesap token alır; hatalı bilgi genel hata döndürür. |
| FR-002 | Kullanıcı yalnızca atandığı dersleri görmelidir. | Başka ders kimliğiyle istek `403` veya kaynak gizleniyorsa `404` döner. |
| FR-003 | Ders bağlamı akademik yıl ve dönemle ayrılmalıdır. | Aynı ders farklı yıl/dönemde farklı açılış olarak saklanır. |
| FR-004 | Sınav türü Vize, Final veya Bütünleme olmalıdır. | Tür veritabanı kısıtı ve API doğrulamasıyla korunur. |
| FR-005 | Soru sayısı dinamik olmalıdır. | 1..N soru eklenebilir; sıra numarası aynı sınavda tektir. |
| FR-006 | Soru azami puanları sınav toplamıyla uyumlu olmalıdır. | Yayınlama/onay öncesi toplam kontrol edilir. |
| FR-007 | Soru birden fazla PÇ'ye bağlanabilmelidir. | Pozitif ağırlıklar saklanır; soru başına toplam ağırlık 1 olmalıdır. |
| FR-008 | Mobil istemci kâğıtları art arda gönderebilmelidir. | Önceki iş sürerken yeni çekim kuyruğa alınabilir. |
| FR-009 | Yükleme tekrarları mükerrer sonuç üretmemelidir. | `client_request_id` aynı kullanıcı için tek iş üretir. |
| FR-010 | Sistem öğrenci ve soru puanı tahmini üretmelidir. | Her tahmin değer, güven ve model sürümü taşır. |
| FR-011 | Belirsiz sonuç insan incelemesine düşmelidir. | Eşik altı kimlik/puan `needs_review` olur. |
| FR-012 | Kullanıcı sonucu düzeltebilmelidir. | Değişen alanlar önceki/yeni değer ve aktörle denetlenir. |
| FR-013 | Onay tek işlemde kaydedilmelidir. | Eksik/hatalı puanda hiçbir kısmi kesin kayıt oluşmaz. |
| FR-014 | Başarılı onay açık durum döndürmelidir. | Yanıt `saved` durumu ve `saved_at` içerir. |
| FR-015 | Bir öğrenci için aynı sınavda tek etkin kâğıt olmalıdır. | Veritabanı benzersizlik kısıtı çakışmayı önler. |
| FR-016 | PÇ analizi yalnız onaylı sonuçları kullanmalıdır. | İşlenmekte/reddedilmiş kâğıt rapora girmez. |
| FR-017 | Sistem Excel raporu üretmelidir. | Dosya öğrenci-soru matrisi, toplamlar ve PÇ özetini içerir. |
| FR-018 | Yönetici öğretim elemanı/ders ataması yapabilmelidir. | Atama tarih aralığı ve rolü saklanır. |

## 5. İş Kuralları

- `academic_year` başlangıç yılıyla tanımlanır; görünen değer örneğin
  `2026–2027` olarak üretilir.
- Sınav toplam puanı pozitiftir; soru puanı sıfırdan büyük ve sınav toplamından
  büyük olamaz.
- Bütünleme, raporlama için ilgili final sınavına bağlanabilir; katılmayan
  öğrenciler “0” ile “yok” arasında ayrıştırılır.
- Her öğrenci numarası kurum içinde benzersizdir; ad-soyad rapor için ayrı
  alanlarda ve erişim kontrollü tutulur.
- Tahmin puanı `[0, soru azami puanı]`, güven değeri `[0,1]` aralığındadır.
- Kesin puan model tahmini değil, öğretim elemanının onayladığı değerdir.
- Bir kâğıdın toplamı kesin soru puanlarının toplamıdır; ayrı elle yazılan
  toplam varsa yalnızca çapraz kontrol verisidir.
- PÇ ağırlıkları kesirli tutulur; soru başına toplam 1 olmalıdır. Bu kontrol
  transaction sonunda tetikleyiciyle doğrulanır.

## 6. Fonksiyonel Olmayan Gereksinimler

| Kimlik | Gereksinim | Hedef |
|---|---|---|
| NFR-001 | Güvenlik | TLS, güçlü parola özeti, kısa ömürlü token, en az yetki |
| NFR-002 | Gizlilik | Ham görsel özel depoda; loglarda kişisel veri yok |
| NFR-003 | Performans | Normal API p95 < 500 ms; OCR asenkron |
| NFR-004 | Geri bildirim | Yükleme kabulü < 2 sn; iş durumu görünür |
| NFR-005 | Güvenilirlik | Onay transaction'ı atomik; tekrar istek idempotent |
| NFR-006 | Taşınabilirlik | iOS yalnızca sürümlü `/api/v1` sözleşmesine bağlanır |
| NFR-007 | İzlenebilirlik | İstek, iş, model sürümü ve değişiklik aktörü izlenebilir |
| NFR-008 | Yedekleme | Günlük DB yedeği; düzenli geri yükleme testi |
| NFR-009 | Erişilebilirlik | Sistem mesajları renk dışında metin/ikonla da anlaşılır |
| NFR-010 | Test | Kritik iş kuralları unit + DB integration + contract testine sahip |

## 7. Excel Çıktısı

Çalışma kitabı en az üç sayfa içermelidir:

1. **Öğrenci Puanları:** öğrenci numarası, her dinamik soru, toplam ve durum.
2. **Soru Analizi:** soru azami/ortalama puanı, başarı yüzdesi ve yanıt sayısı.
3. **PÇ Analizi:** PÇ kodu/açıklaması, elde edilen/ağırlıklı azami puan ve yüzde.

Dosya, üretim zamanı, akademik bağlam, ders, sınav ve raporu üreten kullanıcıyı
metadata olarak taşımalıdır.

## 8. Uçtan Uca Kabul Senaryosu

1. Öğretim elemanı 2026–2027/Güz bağlamında dersini ve Vizeyi seçer.
2. Beş soruyu farklı azami puanlarla tanımlar ve PÇ ağırlıklarını girer.
3. İki öğrenci kâğıdını art arda çeker; ikisi ayrı kuyruk işi olur.
4. Bir kâğıtta düşük güvenli puan görülür; kullanıcı düzeltir ve onaylar.
5. Uygulama her kâğıt için `saved` ve zaman bilgisini gösterir.
6. Aynı `client_request_id` tekrar gönderilince yeni kâğıt oluşmaz.
7. Excel'deki soru toplamları veritabanındaki kesin puanlarla, PÇ yüzdeleri de
   belgelenmiş formülle eşleşir.

## 9. Açık Kararlar

Geliştirmeye başlamadan ürün sahibi/danışmanla netleştirilmelidir:

- Sınav kâğıdı şablonu sabit mi, QR/barkod var mı?
- Öğrenci numarası basılı mı, el yazısı mı?
- Model yalnızca yazılmış sayısal puanı mı okuyacak, cevabın doğruluğunu mu
  değerlendirecek? Bu tasarım **yazılmış soru puanını okuma** varsayımındadır.
- PÇ ağırlıklarının toplamı 1 mi olmalı, yoksa kurum başka yöntem mi kullanıyor?
- Bir derste birden fazla öğretim elemanının onay yetkisi olacak mı?
- Ham görüntü ve raporların saklama/silme süresi nedir?
- Sınav toplam puanı her zaman 100 mü, serbest mi?
- Kurumun Excel şablonu ve PÇ başarı eşiği nedir?
