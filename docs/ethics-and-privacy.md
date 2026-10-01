# Etik, Gizlilik ve Veri Koruma

Sınav görüntüsü, öğrenci numarası ve not bilgisi kişisel veridir. Veri toplamadan
önce kurumun hukuki dayanağı/onay süreci, aydınlatma metni, işleme amacı,
saklama süresi, erişim rolleri, silme prosedürü ve olay müdahale süreci yazılı
olarak onaylanmalıdır.

- Gerçek veri ve görseller Git'e, uygulama loguna veya geliştirici cihazı
  yedeğine eklenmez.
- Ham görseller özel ve şifreli nesne deposunda; ilişkisel kayıtlar erişimi
  kısıtlı PostgreSQL'de tutulur.
- Eğitim verisi mümkün olduğunca kimliksizleştirilir; öğrenci numarası gerekli
  değilse kırpılır veya geri döndürülemez biçimde ayrılır.
- Öğretim elemanı yalnızca atandığı dersin verisini görebilir; rapor indirme ve
  puan değişiklikleri denetlenir.
- Model çıktısı nihai akademik karar değildir. Düşük güvenli veya değiştirilen
  her değer öğretim elemanı onayı gerektirir.
- Saklama süresi dolunca hem görüntü hem türetilmiş kişisel kayıtlar kurum
  politikasına göre silinir veya anonimleştirilir.
- İstatistik/araştırma amacıyla yeniden kullanım, ilk amaçtan ayrıysa ayrıca
  yetkilendirilir.
