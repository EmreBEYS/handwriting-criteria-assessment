"""Reusable exam-paper layout and handwriting inference components."""

from handwriting_ml.layout import ExamPaperLayout, LayoutExtraction, NormalizedBox
from handwriting_ml.recognition import (
    HandwritingRecognizer,
    ModelNotConfiguredError,
    OCRPrediction,
    UnavailableRecognizer,
)

__version__ = "1.0.0"

__all__ = [
    "ExamPaperLayout",
    "HandwritingRecognizer",
    "LayoutExtraction",
    "ModelNotConfiguredError",
    "NormalizedBox",
    "OCRPrediction",
    "UnavailableRecognizer",
    "__version__",
]
