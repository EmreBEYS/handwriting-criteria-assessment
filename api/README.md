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

| Yöntem | Uç | Açıklama |
|---|---|---|
| `GET` | `/health/live` | API süreci canlılık kontrolü |
| `GET` | `/health/ready` | PostgreSQL `SELECT 1` hazır olma kontrolü |
| `POST` | `/api/v1/auth/register` | Öğretim elemanı kaydı ve token üretimi |
| `POST` | `/api/v1/auth/login` | Kurum + e-posta + parola ile giriş |
| `POST` | `/api/v1/auth/refresh` | Refresh JWT ile yeni token çifti |
| `GET` | `/api/v1/users/me` | Bearer access JWT gerektiren profil |

API ilerleyen sprintlerde akademik bağlam, sınav/soru tanımı, asenkron tarama işi,
sonuç onayı, PÇ analizi ve Excel dışa aktarmadan sorumludur. OCR/ML işi istek
süresi içinde değil worker üzerinden çalıştırılır. Uygulama başladığında üretilen
OpenAPI belgesi iki mobil istemci için sözleşmenin kaynağı olacaktır.
