# Handwriting Criteria Assessment

A mobile and machine-learning system that analyzes handwriting images and
returns calibrated probability distributions for explicitly defined assessment
criteria.

## Overview

The project covers the complete path from consented image collection and
annotation to model training, API-based inference, and presentation of results
in a mobile application. The initial implementation remains framework-neutral
until the dataset, criteria, annotation protocol, and deployment constraints are
approved.

The system is designed to report uncertainty. It should return probabilities
and clear limitations rather than presenting a prediction as a definitive fact.

## Intended System Flow

```text
Consented handwriting image
        -> image quality and preprocessing checks
        -> trained model
        -> probability distribution per approved criterion
        -> API response
        -> understandable mobile result screen
```

## First Milestones

1. Define each criterion operationally and state what must not be inferred.
2. Write a consent, privacy, retention, and deletion protocol.
3. Create an annotation guide and measure agreement between annotators.
4. Build a versioned, participant-aware dataset split.
5. Train and calibrate a simple baseline model.
6. Expose a versioned inference contract through the API.
7. Connect the mobile capture/upload flow and test on-device usability.

## Repository Structure

```text
handwriting-criteria-assessment/
├── api/                    # Inference service and API tests
├── contracts/              # Versioned request/response schemas
├── data/
│   ├── processed/          # Prepared datasets (not committed)
│   └── raw/                # Original consented images (not committed)
├── docs/                   # Criteria, ethics, annotation, and architecture
├── ml/
│   ├── configs/            # Training and evaluation configuration
│   ├── notebooks/          # Exploration only; production logic belongs in src
│   ├── src/                # Data, training, calibration, and inference code
│   └── tests/              # Model-pipeline tests
├── mobile/                 # Mobile application, framework to be selected
├── models/                 # Local model artifacts (not committed)
└── tests/                  # End-to-end and contract tests
```

## Getting Started

The repository is intentionally a framework-neutral scaffold. Before coding,
complete these documents:

- `docs/criteria-definition.md`
- `docs/ethics-and-privacy.md`
- `docs/annotation-guidelines.md`

For the Python model and API workspace, Python 3.11 or later is recommended:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Add framework-specific dependencies only after the architecture decision is
recorded. Mobile setup instructions should then be added under `mobile/`.

## Evaluation Principles

- Split data by participant, never merely by image, to reduce identity leakage.
- Report per-criterion metrics and calibration, not only aggregate accuracy.
- Compare against transparent baselines and document dataset imbalance.
- Test performance across capture devices and image-quality conditions.
- Keep a human-review path for low-confidence or out-of-distribution inputs.

## Ethics and Scope

Handwriting can be sensitive biometric-like data. Collection requires informed
consent, data minimization, controlled access, and an explicit deletion policy.
The application must not claim to diagnose health, personality, intelligence,
honesty, or other unsupported traits. Criteria and labels must have a defensible
ground truth and an approved academic purpose.

## License

MIT is recommended for the original source code; see [LICENSE](LICENSE). Training
data, annotations, third-party libraries, pretrained weights, and app assets may
have different licenses or access restrictions and must be tracked separately.

