# API

iOS ve Android istemcilerinin kullandığı ortak, sürümlü backend burada yer
alır. FastAPI uygulaması `api/app` altındadır; PostgreSQL bağlantısı, canlılık
ve hazır olma kontrolleri, request ID içeren merkezi hata zarfı ve OpenAPI sunar.

Model henüz bağlı olmadığı için mevcut analiz ucu bilinçli olarak
`MODEL_NOT_CONFIGURED` döndürür. Hedef teknoloji Python 3.11+, FastAPI,
Pydantic, SQLAlchemy ve Alembic; hedef API tabanı `/api/v1` olacaktır.

00-04 kapsamında öğretim elemanı kaydı, giriş, access/refresh JWT üretimi ve
korumalı kullanıcı profili eklendi. Kayıt, var olan bir `institution_code`
gerektirir; API üzerinden kurum oluşturulmaz.

00-05 kapsamında akademik yıl, dönem ve ders CRUD uçları ile ders açılışı ve
yıl/dönem bazlı ders filtreleri eklendi. Bu uçların tamamı access JWT gerektirir
ve verileri oturum açan kullanıcının kurumuyla sınırlar.

| Yöntem | Uç | Açıklama |
|---|---|---|
| `GET` | `/health/live` | API süreci canlılık kontrolü |
| `GET` | `/health/ready` | PostgreSQL `SELECT 1` hazır olma kontrolü |
| `POST` | `/api/v1/auth/register` | Öğretim elemanı kaydı ve token üretimi |
| `POST` | `/api/v1/auth/login` | Kurum + e-posta + parola ile giriş |
| `POST` | `/api/v1/auth/refresh` | Refresh JWT ile yeni token çifti |
| `GET` | `/api/v1/users/me` | Bearer access JWT gerektiren profil |
| `GET/POST` | `/api/v1/academic-years` | Akademik yıl listeleme/oluşturma |
| `GET/PATCH/DELETE` | `/api/v1/academic-years/{id}` | Akademik yıl CRUD |
| `GET/POST` | `/api/v1/semesters` | Dönem listeleme/oluşturma |
| `GET/PATCH/DELETE` | `/api/v1/semesters/{id}` | Dönem CRUD |
| `GET/POST` | `/api/v1/courses` | Ders listeleme/oluşturma ve filtreleme |
| `GET/PATCH/DELETE` | `/api/v1/courses/{id}` | Ders CRUD |
| `POST` | `/api/v1/course-offerings` | Dersi dönemde açma ve hocayı atama |
| `GET` | `/api/v1/course-offerings` | Kullanıcının atandığı ders açılışları |
| `GET` | `/api/v1/course-offerings/{id}` | Atanmış ders açılışı ayrıntısı |
| `GET/POST` | `/api/v1/course-offerings/{id}/exams` | Sınav listeleme/oluşturma |
| `GET/PATCH/DELETE` | `/api/v1/exams/{id}` | Taslak sınav yönetimi |
| `GET` | `/api/v1/course-offerings/{id}/program-outcomes` | Seçilebilir PÇ listesi |
| `GET/POST` | `/api/v1/exams/{id}/questions` | Dinamik soru listeleme/oluşturma |
| `GET/PATCH/DELETE` | `/api/v1/questions/{id}` | Taslak sınav sorusu yönetimi |
| `PUT` | `/api/v1/questions/{id}/program-outcomes` | Soru–PÇ ağırlıklarını değiştirme |
| `POST` | `/api/v1/exams/{id}/activate` | Bütünlük denetimi ve etkinleştirme |
| `GET/POST` | `/api/v1/students` | Kurum öğrencilerini listeleme/oluşturma |
| `GET/PATCH` | `/api/v1/students/{id}` | Öğrenci okuma, güncelleme ve pasifleştirme |
| `GET/POST` | `/api/v1/course-offerings/{id}/enrollments` | Ders öğrenci listesi yönetimi |
| `DELETE` | `/api/v1/course-offerings/{id}/enrollments/{student_id}` | Ders kaydını pasifleştirme |

API ilerleyen sprintlerde akademik bağlam, sınav/soru tanımı, asenkron tarama işi,
sonuç onayı, PÇ analizi ve Excel dışa aktarmadan sorumludur. OCR/ML işi istek
süresi içinde değil worker üzerinden çalıştırılır. Uygulama başladığında üretilen
OpenAPI belgesi iki mobil istemci için sözleşmenin kaynağı olacaktır.
