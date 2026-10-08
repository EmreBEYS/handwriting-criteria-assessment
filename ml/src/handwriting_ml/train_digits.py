from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision.datasets import EMNIST

from handwriting_ml.digit_model import MODEL_VERSION, DigitCNN


def emnist_transform() -> transforms.Compose:
    # NIST stores glyphs transposed. This restores normal reading orientation.
    return transforms.Compose(
        [
            transforms.Lambda(
                lambda image: image.rotate(-90).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            ),
            transforms.ToTensor(),
            transforms.Normalize((0.1736,), (0.3317,)),
        ]
    )


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def accuracy(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.inference_mode():
        for images, labels in loader:
            predictions = model(images.to(device)).argmax(dim=1).cpu()
            correct += int((predictions == labels).sum())
            total += labels.numel()
    return correct / total


def train(args: argparse.Namespace) -> dict[str, object]:
    seed_everything(args.seed)
    device = torch.device("cpu")
    transform = emnist_transform()
    train_set = EMNIST(
        root=args.data_dir, split="digits", train=True, download=True, transform=transform
    )
    test_set = EMNIST(
        root=args.data_dir, split="digits", train=False, download=True, transform=transform
    )
    train_loader = DataLoader(
        train_set, batch_size=args.batch_size, shuffle=True, num_workers=args.workers
    )
    test_loader = DataLoader(
        test_set, batch_size=args.batch_size * 2, shuffle=False, num_workers=args.workers
    )

    model = DigitCNN().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    loss_function = nn.CrossEntropyLoss()
    started_at = time.monotonic()
    history: list[dict[str, float | int]] = []

    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0
        seen = 0
        for batch, (images, labels) in enumerate(train_loader, start=1):
            images = images.to(device)
            labels = labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = loss_function(model(images), labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * labels.numel()
            seen += labels.numel()
            if batch % 200 == 0:
                print(
                    f"epoch={epoch} batch={batch}/{len(train_loader)} "
                    f"loss={running_loss / seen:.4f}"
                )
        test_accuracy = accuracy(model, test_loader, device)
        epoch_result = {
            "epoch": epoch,
            "train_loss": running_loss / seen,
            "test_accuracy": test_accuracy,
        }
        history.append(epoch_result)
        print(json.dumps(epoch_result))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state": model.cpu().state_dict(),
            "model_version": MODEL_VERSION,
            "dataset": "NIST EMNIST Digits",
            "classes": list(range(10)),
        },
        args.output,
    )
    metrics = {
        "model_version": MODEL_VERSION,
        "dataset": "NIST EMNIST Digits",
        "train_samples": len(train_set),
        "test_samples": len(test_set),
        "seed": args.seed,
        "epochs": args.epochs,
        "history": history,
        "elapsed_seconds": round(time.monotonic() - started_at, 2),
    }
    metrics_path = args.output.with_suffix(".metrics.json")
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(f"model={args.output}")
    print(f"metrics={metrics_path}")
    return metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the EMNIST handwritten digit model")
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw/emnist"))
    parser.add_argument("--output", type=Path, default=Path("models/emnist-digits-v1.pt"))
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--seed", type=int, default=2026)
    return parser


def main() -> None:
    train(build_parser().parse_args())


if __name__ == "__main__":
    main()
