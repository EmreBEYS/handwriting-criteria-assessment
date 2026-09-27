import json
from pathlib import Path


def test_contract_json_files_are_valid_json() -> None:
    contract_dir = Path(__file__).parents[1] / "contracts" / "v1"
    contract_files = sorted(contract_dir.glob("*.json"))

    assert contract_files
    for contract_file in contract_files:
        assert json.loads(contract_file.read_text(encoding="utf-8"))
