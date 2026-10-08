import pytest
from PIL import Image, ImageDraw

torch = pytest.importorskip("torch")

from handwriting_ml.digit_model import (  # noqa: E402
    DigitCNN,
    TorchDigitRecognizer,
    prepare_digit,
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
