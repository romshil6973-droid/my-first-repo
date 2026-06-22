import io
import os
import sys
from pathlib import Path

import pytest
from openpyxl import Workbook

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
import database


def _make_test_excel():
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Фото рабочего дня"
    ws1.append(["Дата", "17.06.2026"])
    ws1.append(["Сотрудник", "testuser"])
    ws1.append(["Начало рабочего дня:", "08:30:00"])
    ws1.append(["№", "Время", "Продолж.", "Операция"])

    ws2 = wb.create_sheet("Мониторинг активности")
    ws2.append(["№", "Начало", "Конец", "Продолжительность", "Приложение / Операция", "URL"])
    ws2.append([1, "08:30:00", "09:30:00", "1:00:00", "Bitrix24", ""])
    ws2.append([2, "09:30:00", "10:00:00", "0:30:00", "chrome.exe", ""])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def test_upload_creates_metrics(client):
    excel_buf = _make_test_excel()
    resp = client.post(
        "/upload/testuser",
        files={"file": ("2026-06-17.xlsx", excel_buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers={"X-API-Token": config.API_TOKEN},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["login"] == "testuser"
    assert data["date"] == "2026-06-17"

    metrics = database.get_metrics_for_date("2026-06-17")
    assert "testuser" in metrics
    assert metrics["testuser"]["bitrix_time"] > 0


def test_upload_registers_employee(client):
    excel_buf = _make_test_excel()
    client.post(
        "/upload/newuser",
        files={"file": ("2026-06-17.xlsx", excel_buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers={"X-API-Token": config.API_TOKEN},
    )
    employees = database.get_all_employees()
    assert "newuser" in employees


def test_archive_endpoint(auth_client, tmp_dirs):
    login_dir = Path(config.UPLOADS_DIR) / "shilov"
    login_dir.mkdir(parents=True, exist_ok=True)
    (login_dir / "2026-06-17.xlsx").write_bytes(b"fake excel")

    resp = auth_client.post("/archive/shilov/2026-06-17")
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"
    assert (login_dir / "2026-06-17.archived.xlsx").exists()
    assert not (login_dir / "2026-06-17.xlsx").exists()
