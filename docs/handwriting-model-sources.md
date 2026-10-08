# Handwriting model data sources

## Selected first model: score and student-number digits

The first trainable recognizer uses the official NIST EMNIST Digits split. It contains
280,000 balanced handwritten digit images and has an official train/test split. This is
appropriate for pretraining isolated digits in score cells and student numbers.

- Source: https://www.nist.gov/itl/products-and-services/emnist-dataset
- Download: `https://biometrics.nist.gov/cs_links/EMNIST/gzip.zip`
- Local data: `data/raw/emnist/` (ignored by Git)
- Model output: `models/emnist-digits-v1.pt` (ignored by Git)

Run training with:

```bash
python -m handwriting_ml.train_digits --epochs 3
```

EMNIST is a character pretraining set, not an end-to-end exam-paper benchmark. Before the
model is enabled in production, it must be fine-tuned and evaluated on real score-cell and
student-number crops whose writers do not cross dataset splits.

## Student name resolution

The production path does not require a general handwritten-name model. The digit model
reads the student number first, then the application resolves the canonical first and last
name from the active enrollment roster for that course. This is more reliable than open
vocabulary name recognition, preserves Turkish characters exactly and avoids collecting a
biometric handwriting dataset.

Name handwriting is only an optional review fallback when the student number does not
uniquely match an active enrollment. It must never override an exact student-number match.

## Rejected name-recognition candidates

IAM provides word and line images from 657 writers and is available for non-commercial
research after accepting the database terms. It is useful for sequence-recognition
pretraining, but it is English and therefore cannot validate Turkish names by itself.

- Source and terms: https://fki.tic.heia-fr.ch/databases/download-the-iam-handwriting-database

The T-H-E dataset includes Turkish handwritten characters, but its public repository does
not currently provide an explicit license file. It must not be copied into this project
until the authors confirm reuse terms.

- Repository: https://github.com/bartosgaye/thedataset

These sources are therefore not required for the normal identity path. If a future research
model uses them, it must remain a review aid and be evaluated separately on Turkish names.
