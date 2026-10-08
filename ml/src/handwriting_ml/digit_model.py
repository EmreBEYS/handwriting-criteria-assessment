from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import torch
from PIL import Image, ImageOps
from torch import nn
from torchvision.transforms import functional as vision

from handwriting_ml.recognition import OCRPrediction

MODEL_VERSION = "emnist-digits-v1"


@dataclass(frozen=True)
class NumberToken:
    kind: Literal["digit", "decimal"]
    image: Image.Image | None
    box: tuple[int, int, int, int]


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


def _otsu_threshold(pixels: np.ndarray) -> int:
    histogram = np.bincount(pixels.ravel(), minlength=256).astype(np.float64)
    total = pixels.size
    weighted_sum = np.dot(np.arange(256), histogram)
    background_weight = 0.0
    background_sum = 0.0
    best_variance = -1.0
    best_threshold = 127
    for threshold in range(256):
        background_weight += histogram[threshold]
        if background_weight == 0:
            continue
        foreground_weight = total - background_weight
        if foreground_weight == 0:
            break
        background_sum += threshold * histogram[threshold]
        background_mean = background_sum / background_weight
        foreground_mean = (weighted_sum - background_sum) / foreground_weight
        variance = background_weight * foreground_weight * (background_mean - foreground_mean) ** 2
        if variance > best_variance:
            best_variance = variance
            best_threshold = threshold
    return best_threshold


def _components(mask: np.ndarray) -> list[tuple[int, int, int, int, int]]:
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    components: list[tuple[int, int, int, int, int]] = []
    for start_y, start_x in np.argwhere(mask):
        if visited[start_y, start_x]:
            continue
        stack = [(int(start_y), int(start_x))]
        visited[start_y, start_x] = True
        left = right = int(start_x)
        top = bottom = int(start_y)
        area = 0
        while stack:
            y, x = stack.pop()
            area += 1
            left = min(left, x)
            right = max(right, x)
            top = min(top, y)
            bottom = max(bottom, y)
            for next_y in range(max(0, y - 1), min(height, y + 2)):
                for next_x in range(max(0, x - 1), min(width, x + 2)):
                    if mask[next_y, next_x] and not visited[next_y, next_x]:
                        visited[next_y, next_x] = True
                        stack.append((next_y, next_x))
        components.append((left, top, right + 1, bottom + 1, area))
    return components


def _merge_horizontal_fragments(
    components: list[tuple[int, int, int, int, int]], gap: int
) -> list[tuple[int, int, int, int, int]]:
    merged: list[tuple[int, int, int, int, int]] = []
    for component in sorted(components):
        if not merged or component[0] > merged[-1][2] + gap:
            merged.append(component)
            continue
        left, top, right, bottom, area = merged[-1]
        merged[-1] = (
            min(left, component[0]),
            min(top, component[1]),
            max(right, component[2]),
            max(bottom, component[3]),
            area + component[4],
        )
    return merged


def segment_number(image: Image.Image, *, allow_decimal: bool = False) -> list[NumberToken]:
    """Split separated handwritten digits while suppressing form borders and specks."""

    gray = np.asarray(ImageOps.grayscale(image))
    threshold = min(245, _otsu_threshold(gray) + 12)
    ink = gray < threshold
    if not ink.any():
        raise ValueError("Number crop contains no foreground ink")

    # Form borders are long, nearly solid rows or columns and must not become digits.
    ink[ink.mean(axis=1) > 0.82, :] = False
    ink[:, ink.mean(axis=0) > 0.82] = False
    raw_components = _components(ink)
    height, width = ink.shape
    minimum_area = max(4, round(height * width * 0.0004))
    candidates = _merge_horizontal_fragments(
        [
            component
            for component in raw_components
            if component[4] >= minimum_area
            and component[2] - component[0] < width * 0.85
            and component[3] - component[1] < height * 0.95
        ],
        gap=max(1, round(height * 0.02)),
    )
    if not candidates:
        raise ValueError("Number crop contains no usable glyphs")

    tall = [box for box in candidates if box[3] - box[1] >= max(6, height * 0.18)]
    if not tall:
        raise ValueError("Number crop contains no digit-sized glyphs")
    median_height = float(np.median([box[3] - box[1] for box in tall]))
    baseline = float(np.median([box[3] for box in tall]))

    tokens: list[NumberToken] = []
    source = ImageOps.grayscale(image)
    for left, top, right, bottom, area in sorted(candidates):
        component_height = bottom - top
        is_decimal = (
            allow_decimal
            and component_height <= median_height * 0.38
            and (top + bottom) / 2 >= baseline - median_height * 0.2
            and area <= max(box[4] for box in tall) * 0.2
        )
        if is_decimal:
            tokens.append(NumberToken("decimal", None, (left, top, right, bottom)))
            continue
        if component_height < median_height * 0.48:
            continue
        padding = max(1, round(median_height * 0.08))
        crop_box = (
            max(0, left - padding),
            max(0, top - padding),
            min(width, right + padding),
            min(height, bottom + padding),
        )
        tokens.append(NumberToken("digit", source.crop(crop_box), crop_box))
    if not any(token.kind == "digit" for token in tokens):
        raise ValueError("Number crop contains no digit-sized glyphs")
    return tokens


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

    def predict_number(self, image: Image.Image, *, allow_decimal: bool = False) -> OCRPrediction:
        text: list[str] = []
        confidences: list[float] = []
        for token in segment_number(image, allow_decimal=allow_decimal):
            if token.kind == "decimal":
                if text and text[-1] != ".":
                    text.append(".")
                continue
            prediction = self.predict_digit(token.image)
            text.append(prediction.text)
            confidences.append(prediction.confidence)
        value = "".join(text).strip(".")
        if not value:
            raise ValueError("Number crop could not be recognized")
        return OCRPrediction(text=value, confidence=min(confidences))

    def predict(self, image: Image.Image, field: str) -> OCRPrediction:
        if field == "student_number":
            return self.predict_number(image)
        if field == "score":
            return self.predict_number(image, allow_decimal=True)
        raise ValueError(f"Digit recognizer does not support field: {field}")
