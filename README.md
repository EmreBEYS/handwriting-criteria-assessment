# Exam Paper Assessment and PÇ Analysis

Öğretim elemanlarının sınav kâğıtlarını mobil cihaz kamerasıyla seri biçimde
okutup öğrenci ve soru puanlarını çıkarmasını, sonuçları PostgreSQL'de
saklamasını ve Program Çıktısı (PÇ) analizleri ile Excel raporları üretmesini
sağlayan bitirme projesi.

## Hedef Sistem

- Öğretim elemanı kendi hesabıyla giriş yapar.
- Akademik yıl, Güz/Bahar dönemi, ders ve Vize/Final/Bütünleme sınavını seçer.
- Dinamik sayıdaki soruyu ve her sorunun PÇ ilişkisini tanımlar.
- iOS (Swift) veya Android (Kotlin) istemcisiyle kâğıtları art arda tarar.
- Ortak backend görüntüyü işler, öğrenci/soru puanlarını çıkarır ve düşük
  güvenli sonuçları kullanıcı onayına sunar.
- Onaylı sonuç tek işlemle kaydedilir ve istemciye “okundu ve kaydedildi”
  durumu döner.
- Ders, sınav, soru ve PÇ bazlı analiz ile Excel çıktısı üretilir.

## Mimari Özet

```text
iOS (Swift) ─┐
             ├─ HTTPS/JSON ─ API + kimlik doğrulama ─ PostgreSQL
Android      ─┘                    │
  (Kotlin)                         ├─ Nesne deposu (sınav görselleri)
                                   └─ OCR/ML iş kuyruğu
```

İki mobil istemci aynı sürümlü API sözleşmesini, backend'i, model hattını ve
PostgreSQL şemasını kullanır. Ham görüntüler veritabanında değil, erişimi
kısıtlı nesne deposunda tutulur; veritabanı yalnızca nesne anahtarını ve işlem
metadatasını saklar.

## Sprint Durumu

- **00-01 Requirements & Architecture:** Gereksinimler ve hedef mimari
  belgelendi. Ayrıntılar: [`docs/requirements.md`](docs/requirements.md) ve
  [`docs/architecture.md`](docs/architecture.md).
- **00-02 PostgreSQL Database Design:** İlişkisel model, kısıtlar ve ilk
  migration hazırlandı. Ayrıntılar: [`docs/database-design.md`](docs/database-design.md)
  ve [`database/README.md`](database/README.md).
- **00-03 Backend API Foundation:** Ortam ayarları, PostgreSQL bağlantısı,
  canlılık/hazır olma uçları ve merkezi API hata zarfı tamamlandı.
- **00-04 Authentication & User System:** Kuruma bağlı öğretim elemanı kaydı,
  Argon2id parola özeti, access/refresh JWT ve korumalı profil ucu tamamlandı.
- **00-05 Course & Academic Structure:** Akademik yıl, dönem ve ders CRUD
  uçları; ders açılışı; yıl/dönem filtreleri ve kurum izolasyonu tamamlandı.
  Ayrıntılar: [`docs/sprint-00-05.md`](docs/sprint-00-05.md).
- **00-06 Exam Definition:** Atanmış ders açılışlarını listeleme; Vize, Final ve
  Bütünleme sınavlarını taslak olarak oluşturma ve yönetme tamamlandı.
  Ayrıntılar: [`docs/sprint-00-06.md`](docs/sprint-00-06.md).
- **00-07 Questions & PÇ Mapping:** Dinamik sorular, PÇ ağırlıkları ve toplam
  puan/PÇ bütünlüğü denetlenen sınav etkinleştirme akışı tamamlandı.
  Ayrıntılar: [`docs/sprint-00-07.md`](docs/sprint-00-07.md).

## Repository Structure

```text
handwriting-criteria-assessment/
├── api/                    # Ortak backend ve API testleri
├── contracts/              # Sürümlü istek/yanıt şemaları
├── database/
│   └── migrations/         # Sıralı PostgreSQL migration dosyaları
├── data/                   # Yerel, anonimleştirilmiş ML verisi (Git dışı)
├── docs/                   # Gereksinim, mimari, veri ve etik kararları
├── ml/                     # OCR/puan çıkarma, eğitim ve değerlendirme
├── mobile/                 # Swift iOS ve Kotlin Android istemcileri
├── models/                 # Yerel model çıktıları (Git dışı)
└── tests/                  # Uçtan uca ve sözleşme testleri
```

## Başlangıç

### Python API and ML workspace

Python 3.11 or later is required:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,ml]'
uvicorn app.main:app --app-dir api --reload
```

Then open `http://127.0.0.1:8000/docs`. `GET /health/live` reports liveness and
`GET /health/ready` verifies the PostgreSQL connection.
`POST /v1/analyses` validates an image and intentionally returns
`MODEL_NOT_CONFIGURED` until an approved model exists.

Run Python checks from the repository root:

```bash
ruff check .
pytest
```

### iOS SwiftUI skeleton

Open `mobile/ios/Package.swift` in Xcode and run the
`HandwritingCriteriaAssessmentApp` scheme. The scaffold demonstrates:

```text
Home -> Capture / Upload -> Analysis -> Results
```

Camera selection, upload networking, analysis, and real result rendering are
deliberately inactive. Command-line verification is also available:

```bash
cd mobile/ios
swift test
```

Before model or dataset implementation, complete and approve:

- `docs/criteria-definition.md`
- `docs/ethics-and-privacy.md`
- `docs/annotation-guidelines.md`

See [Sprint 00-01](docs/sprint-00-01.md) for scope, closure criteria, and the
questions reserved for the supervisor meeting.

### Ortam ve PostgreSQL

Örnek bağlantı ve uygulama ayarlarını kopyalayın; gerçek parola ve anahtarları
yalnızca Git tarafından yok sayılan `.env` dosyasında tutun:

```bash
cp .env.example .env
```

İlk şemayı boş bir PostgreSQL veritabanına uygulamak için:

```bash
psql "$HCA_DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f database/migrations/001_initial_schema.sql
psql "$HCA_DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f database/migrations/002_academic_years.sql
```

Uygulama geliştirmeden önce açık ürün kararlarını
[`docs/requirements.md`](docs/requirements.md) içindeki “Açık Kararlar”
bölümünde kapatın. Gerçek sınav kâğıdı veya öğrenci verisi repoya eklenmemelidir.

## Güvenlik ve Etik

Sınav kâğıtları ve öğrenci başarı verileri kişisel veridir. En az yetki,
şifreli aktarım/depolama, denetim kaydı, açık saklama-silme süreleri ve düşük
güvenli model sonuçlarında insan onayı zorunludur. Sistem nihai notu öğretim
elemanı onayı olmadan öğrenci bilgi sistemine aktarmamalıdır.

## License

Kaynak kod için [LICENSE](LICENSE) geçerlidir. Veri kümeleri, önceden eğitilmiş
ağırlıklar ve üçüncü taraf varlıklar ayrıca lisanslanmalıdır.
