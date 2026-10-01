# Database

PostgreSQL 15 veya üzeri hedeflenir. Migration dosyaları sırayla uygulanır ve
uygulandıktan sonra değiştirilmez.

## İlk Kurulum

```bash
createdb exam_assessment
psql "postgresql:///exam_assessment" -v ON_ERROR_STOP=1 \
  -f database/migrations/001_initial_schema.sql
```

`pgcrypto` ve `citext` eklentilerini oluşturma yetkisi gerekir. Yönetilen
PostgreSQL servisinde eklentiler önceden etkinleştirilebilir.

## Doğrulama

```bash
psql "$HCA_DATABASE_URL" -c '\dt'
psql "$HCA_DATABASE_URL" -c '\d+ exam_papers'
```

Production bağlantı bilgileri `.env` veya secret manager üzerinden verilir;
repoya yazılmaz. Ayrıntılı kararlar için
[`../docs/database-design.md`](../docs/database-design.md) belgesine bakın.
