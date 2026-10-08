from dataclasses import dataclass
from typing import Protocol

from PIL import Image


class ModelNotConfiguredError(RuntimeError):
    """Raised when worker execution is attempted without evaluated model weights."""


@dataclass(frozen=True)
class OCRPrediction:
    text: str
    confidence: float

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("Prediction confidence must be between 0 and 1")


class HandwritingRecognizer(Protocol):
    @property
    def model_version(self) -> str: ...

    def predict(self, image: Image.Image, field: str) -> OCRPrediction: ...


class UnavailableRecognizer:
    def __init__(self, model_version: str = "untrained") -> None:
        self._model_version = model_version

    @property
    def model_version(self) -> str:
        return self._model_version

    def predict(self, image: Image.Image, field: str) -> OCRPrediction:
        raise ModelNotConfiguredError(
            "No evaluated handwriting model bundle has been configured for the worker"
        )
