# API

iOS ve Android istemcilerinin kullandığı ortak, sürümlü backend burada yer
alacaktır. Mevcut FastAPI iskeleti `api/app` altındadır; sağlık kontrolü,
görsel yükleme doğrulaması, request ID içeren hata zarfı ve OpenAPI sunar.

Model henüz bağlı olmadığı için mevcut analiz ucu bilinçli olarak
`MODEL_NOT_CONFIGURED` döndürür. Hedef teknoloji Python 3.11+, FastAPI,
Pydantic, SQLAlchemy ve Alembic; hedef API tabanı `/api/v1` olacaktır.

API; kimlik doğrulama, akademik bağlam, sınav/soru tanımı, asenkron tarama işi,
sonuç onayı, PÇ analizi ve Excel dışa aktarmadan sorumludur. OCR/ML işi istek
süresi içinde değil worker üzerinden çalıştırılır. Uygulama başladığında üretilen
OpenAPI belgesi iki mobil istemci için sözleşmenin kaynağı olacaktır.
