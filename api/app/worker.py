from app.database import SessionLocal
from app.models import ScanStatus
from app.processing import process_next_scan
from app.storage import get_object_storage


def main() -> int:
    with SessionLocal() as db:
        scan = process_next_scan(db, get_object_storage())
    if scan is None:
        return 0
    return 0 if scan.status != ScanStatus.failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
