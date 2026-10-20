# 00-22 — Cihaz İçi ONNX El Yazısı Rakam Tanıma

## Sonuç

00-21 Swift iOS belge kamerası, sabit şablon, seri sayfa, soru–PÇ ve renkli
Excel akışları korunmuştur. Genel not ve soru puanı hücreleri artık arkadaş
projesindeki `digit-crnn-v3` modeliyle cihazda okunur. Öğrenci adı Apple Vision
ile okunmaya devam eder; hedef şablonda henüz öğrenci numarası bölgesi olmadığı
için modelin numara modu ürün akışına bağlanmamıştır.

Kaynak sabitlemesi:

- Depo: `https://github.com/asosyal04440/bitirme-projesi`
- Commit: `ed1de27b20635ca8971685d0ec4135523b824ec0`
- Model: `models/digit-crnn-v3.onnx`
- SHA-256: `84db44945e13991f71fa77e891f6fa5a050c1feba7a1327310e3dc0b05011052`
- Boyut: 2.536.039 bayt
- Çalışma zamanı: Microsoft ONNX Runtime Swift Package Manager `1.24.2`

## Uygulama mimarisi

`ONNXDigitRecognizer`, çalışma zamanını uygulama kodundan ayıran tek adaptördür.
Model oturumu bir kez açılır ve eşzamanlı çağrılar kilitle korunur. Model girişi
ve çözme davranışı kaynak projenin Rust `recognition.rs` ve Python `model.py`
sözleşmesini izler:

1. RGB hücre kırpımı en-boy oranı korunarak 32 piksel yüksekliğe getirilir.
2. Genişlik yarım yukarı yuvarlanır, `16...512` aralığına sıkıştırılır ve 4'ün
   katına sağdan beyaz doldurulur.
3. Piksel merkezleri hizalı, kenarları sıkıştırılmış bilinear örnekleme yapılır;
   NCHW `float32` değerleri `[-1, 1]` aralığına çevrilir.
4. Çıktı `blank + 0123456789.~` sınıfları üzerinde açgözlü CTC ile çözülür;
   tekrarlar birleştirilir, blank atılır.
5. Güven, bütün zaman adımlarındaki kazanan olasılıkların en küçüğüdür.
6. Öğrenci numarası modu yalnızca rakamlara izin verir; puan/toplam modu ondalık
   nokta ile üstü çizili düzeltme işaretini de kabul eder.

Bu sınır sayesinde gelecekte model veya mobil çalışma zamanı değişirken tarama,
Excel ve PÇ kodu değiştirilmeden adaptör değiştirilebilir.

## İnceleme ve geri dönüş politikası

- `confidence >= 0.99`, boş olmayan, düzeltilmemiş ve azami puan aralığındaki
  model sonucu otomatik kabul edilebilir.
- `confidence < 0.99`, boş sonuç ve `~` düzeltme işareti insan kontrolü ister.
- Yazılı genel not ile soru toplamı farklıysa kâğıt kontrol ister.
- Model yükleme veya çıkarım hatasında Apple Vision devreye girer. Geri dönüş
  güveni en fazla `0.59` olduğundan sonuç otomatik kabul edilmez.
- Excel'in yeşil/sarı/kırmızı hücreleri korunmuştur; `Genel Güven` sütunu ayrıca
  `Kontrol gerekli` yazar.

## Kaynak modelin yayımlanmış ölçümleri

Kaynak depodaki JSON ölçümlerine göre sentetik test kümesinde alan bazlı tam
eşleşme puanlarda `%93,13`, genel toplamda `%83,5`, öğrenci numarasında `%63,0`
ve bütün alanlarda `%86,5`'tir. `0.99` eşiğinde kapsam `%42,75`, kabul edilen
alanların tam eşleşmesi `%99,22`'dir (1.200 alan, 4 kabul hatası).

CVL Digit Strings değerlendirmesinde, eğitimde görülmemiş 181 yazardan 4.687
sayı üzerinde tam eşleşme `%83,1`, karakter hata oranı `%3,21` olarak raporlanır.
Bu değerler İnönü sınav kâğıdı kamera fotoğraflarında doğruluk iddiası değildir.

## Doğrulama

- Ön işleme toplamları 15 Rust/Python referans fixture'ıyla `0.05` toleransında
  eşleşti.
- Aynı 15 hücrede Swift/ONNX metni bire bir, güveni `0.002` toleransında Rust
  referansıyla eşleşti.
- Apple Silicon macOS üzerinde 15 hücrelik çıkarım grubu `0,116 sn` sürdü. Bu
  yalnızca regresyon benchmark'ıdır; iPhone performans taahhüdü değildir.
- Dört mevcut tarama/şablon/Excel testi ve beş yeni model/politika/kırpma testi
  geçti: toplam 9 test, 0 hata.
- Xcode proje dosyası biçim doğrulamasından geçti. Bu çalışma ortamının Xcode
  süreçleri sistem modül önbelleğine yazamadığı için `generic/platform=iOS`
  imzasız derleme burada tamamlanamadı; gerçek CI/macOS kapısı açık kalır.

## Lisans ve veri kapısı

Kaynak depoda belirtilen committe `LICENSE` dosyası yoktur. Entegrasyon,
depo sahibinin bu proje için verdiği sözlü izne dayanır; yazılı ve kapsamı açık
bir lisansın yerini aldığı varsayılmamıştır. Modelin eğitim verileri içinde
kaynak deponun CC BY-NC 4.0 olarak tanımladığı CVL materyali vardır. Bu nedenle
model, yazılı izin ve veri lisansları ayrıca doğrulanmadan ticari dağıtıma uygun
kabul edilmemelidir. Ayrıntı ve atıflar `THIRD_PARTY_NOTICES.md` içindedir.
