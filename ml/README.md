# OCR / Machine Learning Workspace

Bu alan; görüntü kalite kontrolü, sayfa hizalama, öğrenci numarası ve dinamik
soru bölgelerinin çıkarımı, el yazısı/rakam tanıma, puan tahmini ve güven skoru
üretimi içindir.

The package is installable as `handwriting_ml`. Sprint 00-10 adds versioned
paper-layout extraction for course, student identity, question–outcome headers
and dynamic handwritten score cells. It intentionally does not claim a trained
handwriting model before an approved dataset and evaluated weights exist.

Sprint 00-11 adds the recognizer boundary and a strict JSON Lines dataset
manifest validator. Writer identities may not cross dataset splits. Dataset
collection and model evaluation requirements are documented in
[`../docs/handwriting-dataset-protocol.md`](../docs/handwriting-dataset-protocol.md).

The first real training pipeline uses NIST EMNIST Digits for score cells and
student numbers. Install `.[ml]`, then run
`python -m handwriting_ml.train_digits --epochs 3`. Dataset selection and
limitations are documented in
[`../docs/handwriting-model-sources.md`](../docs/handwriting-model-sources.md).

Tekrar kullanılabilir üretim kodu `src/`, deney ayarları `configs/`, yalnızca
keşif çalışmaları `notebooks/` altında tutulur. Her çıkarım model sürümünü
kaydeder. Eğitim/değerlendirme veri ayrımı öğrenci bazında yapılmalı; düşük
güvenli sonuçlar otomatik kesin puana dönüşmemelidir.
