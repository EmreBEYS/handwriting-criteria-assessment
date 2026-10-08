from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
from PIL import Image, ImageOps
from torch import nn
from torchvision.transforms import functional as vision

from handwriting_ml.recognition import OCRPrediction

MODEL_VERSION = "emnist-digits-v1"


class DigitCNN(nn.Module):
    """Compact classifier for a single 28x28 handwritten digit."""

    def __init__(self) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 7 * 7, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 10),
        )

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(image))


def prepare_digit(image: Image.Image) -> torch.Tensor:
    """Normalize a dark-on-light digit crop to the EMNIST tensor convention."""

    gray = ImageOps.grayscale(image)
    inverted = ImageOps.invert(gray)
    bounds = inverted.point(lambda pixel: 255 if pixel >= 24 else 0).getbbox()
    if bounds is None:
        raise ValueError("Digit crop contains no foreground ink")
    glyph = inverted.crop(bounds)
    glyph.thumbnail((20, 20), Image.Resampling.LANCZOS)
    canvas = Image.new("L", (28, 28), color=0)
    left = (28 - glyph.width) // 2
    top = (28 - glyph.height) // 2
    canvas.paste(glyph, (left, top))
    tensor = vision.pil_to_tensor(canvas).float().div(255)
    tensor = vision.normalize(tensor, mean=(0.1736,), std=(0.3317,))
    return tensor.unsqueeze(0)


@dataclass
class TorchDigitRecognizer:
    model: nn.Module
    model_version: str = MODEL_VERSION

    @classmethod
    def load(cls, path: str | Path) -> TorchDigitRecognizer:
        checkpoint = torch.load(Path(path), map_location="cpu", weights_only=True)
        model = DigitCNN()
        model.load_state_dict(checkpoint["model_state"])
        model.eval()
        return cls(model=model, model_version=str(checkpoint["model_version"]))

    @torch.inference_mode()
    def predict_digit(self, image: Image.Image) -> OCRPrediction:
        probabilities = self.model(prepare_digit(image)).softmax(dim=1)[0]
        confidence, label = probabilities.max(dim=0)
        return OCRPrediction(text=str(label.item()), confidence=confidence.item())
