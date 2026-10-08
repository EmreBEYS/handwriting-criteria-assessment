# OCR / Machine Learning Workspace

Bu alan; görüntü kalite kontrolü, sayfa hizalama, öğrenci numarası ve dinamik
soru bölgelerinin çıkarımı, el yazısı/rakam tanıma, puan tahmini ve güven skoru
üretimi içindir.

The package is installable as `handwriting_ml`. Sprint 00-10 adds versioned
paper-layout extraction for course, student identity, question–outcome headers
and dynamic handwritten score cells. It intentionally does not claim a trained
handwriting model before an approved dataset and evaluated weights exist.

Tekrar kullanılabilir üretim kodu `src/`, deney ayarları `configs/`, yalnızca
keşif çalışmaları `notebooks/` altında tutulur. Her çıkarım model sürümünü
kaydeder. Eğitim/değerlendirme veri ayrımı öğrenci bazında yapılmalı; düşük
güvenli sonuçlar otomatik kesin puana dönüşmemelidir.
