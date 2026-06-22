import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
import database


def test_auth_required(client):
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]


def test_auth_success(auth_client):
    resp = auth_client.get("/dashboard")
    assert resp.status_code == 200
    assert "Мониторинг рабочего дня" in resp.text


def test_dashboard_shows_all_employees(auth_client):
    database.upsert_employee("shilov", "2026-06-17")
    database.upsert_employee("ivanov", "2026-06-17")
    database.upsert_metrics("shilov", "2026-06-17", {
        "work_start": "08:30:00", "work_end": "17:00:00",
        "duration": 30600, "active_time": 25000,
        "bitrix_time": 3600, "onec_time": 1800,
        "browser_time": 2400, "achievements": "Test",
    })

    resp = auth_client.get("/dashboard?date=2026-06-17")
    assert resp.status_code == 200
    assert "shilov" in resp.text
    assert "ivanov" in resp.text


def test_dashboard_no_data_row(auth_client):
    database.upsert_employee("ivanov", "2026-06-16")
    resp = auth_client.get("/dashboard?date=2026-06-17")
    assert resp.status_code == 200
    assert "no-data" in resp.text


def test_date_navigation(auth_client):
    resp = auth_client.get("/dashboard?date=2026-06-17")
    assert "2026-06-16" in resp.text  # prev workday link
    assert "2026-06-18" in resp.text  # next workday link


def test_download_link_active(auth_client, tmp_dirs):
    database.upsert_employee("shilov", "2026-06-17")
    database.upsert_metrics("shilov", "2026-06-17", {
        "work_start": "08:30:00", "work_end": "17:00:00",
        "duration": 30600, "active_time": 25000,
        "bitrix_time": 3600, "onec_time": 1800,
        "browser_time": 2400, "achievements": None,
    })
    login_dir = Path(config.UPLOADS_DIR) / "shilov"
    login_dir.mkdir(parents=True, exist_ok=True)
    (login_dir / "2026-06-17.xlsx").write_bytes(b"fake excel")

    resp = auth_client.get("/download/shilov/2026-06-17")
    assert resp.status_code == 200


def test_download_link_inactive(auth_client):
    resp = auth_client.get("/download/shilov/2026-06-17")
    assert resp.status_code == 404
