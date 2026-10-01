# Veri Etiketleme Rehberi

Etiket birimi, kimliği kaldırılmış bir sınav kâğıdındaki öğrenci numarası alanı
ve her soru için öğretim elemanının yazdığı sayısal puandır. Gerçek ad-soyad veya
gereksiz sayfa bölümleri eğitim verisine alınmaz.

- Sayfa ve alan sınırları sürümlü sınav şablonuna göre işaretlenir.
- Okunamayan alan `unreadable`, boş alan `blank` olarak ayrılır; ikisi `0`
  puanla eş anlamlı değildir.
- Puan aralık dışındaysa düzeltilerek tahmin edilmez, `invalid` işaretlenir.
- Ana veri kümesinin bir bölümü iki bağımsız etiketleyici tarafından etiketlenir.
- Uyuşmazlık üçüncü yetkili değerlendiriciyle çözülür ve değişiklik kaydedilir.
- Veri bölme işlemi aynı öğrencinin kâğıtları eğitim ve test setlerine
  dağılmayacak şekilde öğrenci bazında yapılır.
- Model; alan doğruluğu, mutlak puan hatası, güven kalibrasyonu, cihaz ve görüntü
  kalitesi kırılımlarında raporlanır.
