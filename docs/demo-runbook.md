# Sprint 00-21 Demo Runbook

## Hazırlık

- Gerçek öğrenci verisi yerine sentetik, sabit şablon v1 kâğıdı kullanın.
- Şablondaki öğrenci adı, genel not ve sağdaki soru puanı hücrelerinin yerini değiştirmeyin.
- Fiziksel iPhone/iPad'de kamera iznini verin; simülatörü kamera kanıtı saymayın.

## Demo akışı

1. Uygulamanın giriş ekranı olmadan doğrudan tarama ekranında açıldığını gösterin.
2. Ders adını, soru sayısını, azami puanları ve soru–PÇ eşleşmelerini ayarlayın.
3. “Kâğıtları Tara” ile belge kamerasında birkaç sayfayı art arda çekin; kenar algılama ve perspektif düzeltmesini gösterin.
4. Her sayfanın kontrol ekranı açılmadan ayrı öğrenci satırı olarak eklendiğini gösterin.
5. Otomatik açılan kayıt ekranından kümülatif `sinav-sonuclari.xlsx` dosyasını kaydedin.
6. Excel'de öğrenci adı, genel not ve soru puanı hücrelerinin yeşil/sarı/kırmızı işaretlerini açıklayın.
7. “Yeni Kâğıtlar Ekle” ile bir seri daha tarayın ve güncel dosyada önceki satırların korunduğunu gösterin.
8. Son olarak renklerin OCR güvenini gösterdiğini, nihai not onayı olmadığını ve Android'in bu repoda bulunmadığını belirtin.

## Hata yolları

- Kamera kullanılamıyorsa fiziksel cihaz ve izinleri kontrol edin.
- Alan boş veya kırmızıysa sayfayı gölgesiz ve tam kadraj yeniden tarayın; Excel satırını gözle doğrulayın.
- Puan azami değerin dışındaysa ilgili Excel hücresi kırmızıya düşer.
- Şablon değiştiyse koordinatları kalibre etmeden doğruluk iddiasında bulunmayın.
