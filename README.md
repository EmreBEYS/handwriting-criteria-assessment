# Handwriting Criteria Assessment

Sabit sınav şablonundaki öğrenci adı, soru puanları ve genel notu iPhone/iPad
kamerasıyla art arda okuyup soru–Program Çıktısı (PÇ) eşleşmeleriyle birlikte
tek bir renkli Excel tablosunda biriktiren yerel iOS uygulaması.

## Sprint 00-22 ürün kararı

12 Ekim 2026 danışman geri bildirimiyle önceki hesap, giriş ve PostgreSQL
mimarisi aktif ürün kapsamından çıkarıldı. Uygulama artık oturum açmaz, sunucuya
kişisel veri göndermez ve veritabanı gerektirmez. Belge tarama ile OCR cihazda
VisionKit, Apple Vision ve cihazdaki `digit-crnn-v3` ONNX modeli kullanılarak
yapılır. Öğrenci adı Apple Vision'da kalır; genel not ve soru puanları model
adaptöründen geçer.

Aktif akış:

```text
iOS belge kamerası
        ↓ otomatik kenar algılama ve perspektif düzeltme
Sabit şablon v1
        ↓ öğrenci adı (Vision) + 1…12 soru puanı ve genel not (ONNX)
Yeşil/sarı/kırmızı güven renkli seri sonuç satırları
        ↓
Gerçek renkli `.xlsx` çalışma kitabı
```

## 00-22 kapsamı

- iOS ve iPadOS'ta `VNDocumentCameraViewController` ile otomatik belge tarama
- Sabit sınav şablonunda 1–12 arasında değişken soru sayısı
- Her soru için düzenlenebilir azami puan ve PÇ kodu
- Öğrenci adı, soru puanları ve kâğıtta yazılı genel not için yerel OCR
- Soru puanlarından hesaplanan toplam ile yazılı genel not çapraz kontrolü
- Belge kamerasındaki her sayfayı ayrı kâğıt sayıp aynı oturum tablosuna ekleme
- Kontrol ekranına uğramadan seri OCR ve kümülatif Excel dışa aktarma
- Öğrenci adı, genel not ve soru hücrelerini yeşil/sarı/kırmızı güven rengiyle işaretleme
- Sonuçların Excel'in doğrudan açabildiği biçimlendirilmiş `.xlsx` çalışma kitabı olarak paylaşılması
- OCR sonucunu nihai/otomatik not olarak kabul etmeme; renkler kullanıcıya doğruluk iddiası sunmaz
- `0.99` altı model güvenini, boş/düzeltilmiş alanları ve toplam uyuşmazlığını incelemeye gönderme
- Model/çalışma zamanı hatasında düşük güvenli Apple Vision geri dönüşü
- Kaynak Rust/Python ön işleme ve CTC çözme sözleşmesiyle 15 fixture eşitlik testi

Android uygulaması bu repoda bulunmuyor ve 00-21 kapsamında var sayılmıyor.
Android ekibi aynı sabit şablon ve güven eşiklerini ayrı istemcide uygulamalıdır.

## Çalıştırma ve test

Gerçek uygulamayı çalıştırmak için `Package.swift` yerine
`mobile/ios/HandwritingCriteriaAssessment.xcodeproj` dosyasını Xcode ile açın.
`HandwritingCriteriaAssessment` şemasını ve bağlı iPhone/iPad'i seçin. İlk
çalıştırmada target'ın **Signing & Capabilities** bölümünden kendi Apple
geliştirici takımınızı seçmeniz gerekir. Kamera izin açıklaması projeye eklenmiştir.
Belge kamerası simülatörde doğrulanamaz.

Komut satırı testleri:

```bash
cd mobile/ios
swift test
```

Testler dinamik soru sayısını, güven eşiklerini, iki toplamın ayrı tutulmasını,
çoklu öğrenci satırlarını, renkli Excel'i ve ONNX ön işleme/çıkarım eşitliğini kapsar.

## Dizinler

- `mobile/ios/Sources/AppCore/Sprint21`: korunmuş uygulama akışı ve 00-22 model adaptörü
- `docs/sprint-00-22.md`: entegrasyon, ölçümler, kabul ölçütleri ve kalan kapılar
- `api`, `database`, `ml` ve iOS içindeki hariç tutulan eski klasörler: 00-20
  geçmişini koruyan legacy referans; aktif uygulama tarafından derlenmez veya kullanılmaz

Gerçek sınav kâğıtları kişisel veridir. Paylaşılan Excel dosyaları kurum
politikasına göre korunup silinmeli; OCR çıktısı nihai not kabul edilmemelidir.

## License

Projenin özgün kaynak kodu için [LICENSE](LICENSE) geçerlidir. Bundled model,
fixture'lar ve ONNX Runtime için [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
ayrıca geçerlidir; model ticari kullanım için temizlenmiş sayılmamalıdır.
