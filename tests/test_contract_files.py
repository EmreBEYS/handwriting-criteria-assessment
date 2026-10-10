import json
import tomllib
from pathlib import Path

import handwriting_ml
from app.main import app


def test_contract_json_files_are_valid_json() -> None:
    contract_dir = Path(__file__).parents[1] / "contracts" / "v1"
    contract_files = sorted(contract_dir.glob("*.json"))

    assert contract_files
    for contract_file in contract_files:
        assert json.loads(contract_file.read_text(encoding="utf-8"))


def test_release_versions_are_consistent() -> None:
    root = Path(__file__).parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["version"] == "1.0.0"
    assert app.version == "1.0.0"
    assert handwriting_ml.__version__ == "1.0.0"


def test_release_documents_are_present() -> None:
    root = Path(__file__).parents[1]
    required = [
        "CHANGELOG.md",
        "SECURITY.md",
        "docs/academic-evaluation.md",
        "docs/demo-runbook.md",
        "docs/deployment.md",
        "docs/release-checklist.md",
        "docs/sprint-00-20.md",
        "docs/verification-2026-10-10.md",
    ]

    assert all((root / path).is_file() for path in required)
