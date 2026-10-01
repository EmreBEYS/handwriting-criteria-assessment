# OCR / Machine Learning Workspace

Bu alan; görüntü kalite kontrolü, sayfa hizalama, öğrenci numarası ve dinamik
soru bölgelerinin çıkarımı, el yazısı/rakam tanıma, puan tahmini ve güven skoru
üretimi içindir.

The package is installable as `handwriting_ml`. Sprint 00-01 includes no model,
labels, transforms, or training configuration.

Tekrar kullanılabilir üretim kodu `src/`, deney ayarları `configs/`, yalnızca
keşif çalışmaları `notebooks/` altında tutulur. Her çıkarım model sürümünü
kaydeder. Eğitim/değerlendirme veri ayrımı öğrenci bazında yapılmalı; düşük
güvenli sonuçlar otomatik kesin puana dönüşmemelidir.
