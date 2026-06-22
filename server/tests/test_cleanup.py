import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from cleanup import cleanup_old_files, count_working_days


def _create_file(uploads_dir, login, filename):
    d = Path(uploads_dir) / login
    d.mkdir(parents=True, exist_ok=True)
    f = d / filename
    f.write_text("test")
    return f


def test_delete_old_files(tmp_dirs):
    old_date = date(2026, 4, 1)
    today = date(2026, 6, 17)
    _create_file(config.UPLOADS_DIR, "shilov", f"{old_date.isoformat()}.xlsx")

    deleted = cleanup_old_files(config.UPLOADS_DIR, today)
    assert deleted == 1
    assert not (Path(config.UPLOADS_DIR) / "shilov" / f"{old_date.isoformat()}.xlsx").exists()


def test_archived_not_deleted(tmp_dirs):
    old_date = date(2026, 4, 1)
    today = date(2026, 6, 17)
    f = _create_file(config.UPLOADS_DIR, "shilov", f"{old_date.isoformat()}.archived.xlsx")

    deleted = cleanup_old_files(config.UPLOADS_DIR, today)
    assert deleted == 0
    assert f.exists()


def test_recent_files_kept(tmp_dirs):
    recent_date = date(2026, 6, 15)
    today = date(2026, 6, 17)
    f = _create_file(config.UPLOADS_DIR, "shilov", f"{recent_date.isoformat()}.xlsx")

    deleted = cleanup_old_files(config.UPLOADS_DIR, today)
    assert deleted == 0
    assert f.exists()
