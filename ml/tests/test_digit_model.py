import pytest
from PIL import Image, ImageDraw

torch = pytest.importorskip("torch")

from handwriting_ml.digit_model import (  # noqa: E402
    DigitCNN,
    NumberToken,
    TorchDigitRecognizer,
    prepare_digit,
    segment_number,
)


def test_prepare_digit_centers_ink() -> None:
    image = Image.new("L", (80, 50), color=255)
    ImageDraw.Draw(image).rectangle((35, 5, 44, 44), fill=0)

    tensor = prepare_digit(image)

    assert tensor.shape == (1, 1, 28, 28)
    assert tensor.max().item() > 2


def test_prepare_digit_rejects_blank_crop() -> None:
    with pytest.raises(ValueError, match="no foreground ink"):
        prepare_digit(Image.new("L", (28, 28), color=255))


def test_checkpoint_round_trip(tmp_path) -> None:
    checkpoint = tmp_path / "digits.pt"
    torch.save(
        {
            "model_state": DigitCNN().state_dict(),
            "model_version": "test-digits",
        },
        checkpoint,
    )

    recognizer = TorchDigitRecognizer.load(checkpoint)

    assert recognizer.model_version == "test-digits"


def test_segment_number_ignores_cell_border_and_keeps_decimal() -> None:
    image = Image.new("L", (140, 60), color=255)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 139, 59), outline=0, width=1)
    draw.rectangle((20, 10, 31, 49), fill=0)
    draw.rectangle((58, 10, 71, 49), fill=0)
    draw.ellipse((82, 43, 87, 48), fill=0)
    draw.rectangle((100, 10, 113, 49), fill=0)

    tokens = segment_number(image, allow_decimal=True)

    assert [token.kind for token in tokens] == ["digit", "digit", "decimal", "digit"]


def test_predict_number_combines_digit_predictions(monkeypatch) -> None:
    recognizer = TorchDigitRecognizer(DigitCNN())
    tokens = [
        NumberToken("digit", Image.new("L", (10, 20)), (0, 0, 10, 20)),
        NumberToken("digit", Image.new("L", (10, 20)), (12, 0, 22, 20)),
    ]
    predictions = iter([("2", 0.98), ("5", 0.91)])
    monkeypatch.setattr(
        "handwriting_ml.digit_model.segment_number", lambda image, allow_decimal: tokens
    )
    monkeypatch.setattr(
        recognizer,
        "predict_digit",
        lambda image: __import__("handwriting_ml.recognition", fromlist=["OCRPrediction"])
        .OCRPrediction(*next(predictions)),
    )

    prediction = recognizer.predict_number(Image.new("L", (30, 20)), allow_decimal=True)

    assert prediction.text == "25"
    assert prediction.confidence == 0.91
