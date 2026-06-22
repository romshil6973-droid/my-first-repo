import os
import re
from datetime import date, timedelta
from pathlib import Path

from config import RETENTION_WORKING_DAYS, UPLOADS_DIR


def count_working_days(start: date, end: date) -> int:
    count = 0
    current = start + timedelta(days=1)
    while current <= end:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def cleanup_old_files(uploads_dir: str | None = None, today: date | None = None):
    base = Path(uploads_dir or UPLOADS_DIR)
    if not base.exists():
        return 0

    if today is None:
        today = date.today()

    deleted = 0
    for login_dir in base.iterdir():
        if not login_dir.is_dir():
            continue
        for f in login_dir.iterdir():
            if not f.is_file():
                continue
            if ".archived" in f.name:
                continue
            match = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
            if not match:
                continue
            try:
                file_date = date.fromisoformat(match.group(1))
            except ValueError:
                continue
            if count_working_days(file_date, today) > RETENTION_WORKING_DAYS:
                f.unlink()
                deleted += 1

    return deleted
