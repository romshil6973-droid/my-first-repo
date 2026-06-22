import os
import sys

import pytest
from openpyxl import Workbook

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parser import parse_excel


def make_workbook(sheet2_rows, sheet1_rows=None):
    """Helper: create a test Excel with two sheets."""
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Фото рабочего дня"

    ws1.append(["Дата", "17.06.2026"])
    ws1.append(["Сотрудник", "testuser"])
    ws1.append(["Начало рабочего дня:", "08:30:00"])
    ws1.append(["№", "Время", "Продолж.", "Операция"])
    if sheet1_rows:
        for row in sheet1_rows:
            ws1.append(row)

    ws2 = wb.create_sheet("Мониторинг активности")
    ws2.append(["№", "Начало", "Конец", "Продолжительность", "Приложение / Операция", "URL"])
    for row in sheet2_rows:
        ws2.append(row)

    return wb


def save_wb(wb, tmp_path, name="test.xlsx"):
    path = os.path.join(str(tmp_path), name)
    wb.save(path)
    return path


def test_parse_sheet2_active_time(tmp_path):
    wb = make_workbook([
        [1, "08:30:00", "09:00:00", "0:30:00", "Bitrix24", ""],
        [2, "09:00:00", "09:15:00", "0:15:00", "Режим ожидания", ""],
        [3, "09:15:00", "10:00:00", "0:45:00", "1cv8.exe", ""],
    ])
    path = save_wb(wb, tmp_path)
    m = parse_excel(path)
    assert m["active_time"] == 30 * 60 + 45 * 60  # 4500 seconds
    assert m["duration"] == 30 * 60 + 15 * 60 + 45 * 60


def test_parse_sheet2_bitrix(tmp_path):
    wb = make_workbook([
        [1, "08:00:00", "08:30:00", "0:30:00", "Bitrix24 - CRM", ""],
        [2, "08:30:00", "09:00:00", "0:30:00", "Битрикс24", ""],
        [3, "09:00:00", "09:30:00", "0:30:00", "Word", ""],
    ])
    path = save_wb(wb, tmp_path)
    m = parse_excel(path)
    assert m["bitrix_time"] == 60 * 60


def test_parse_sheet2_onec(tmp_path):
    wb = make_workbook([
        [1, "08:00:00", "08:30:00", "0:30:00", "1cv8.exe - Бухгалтерия", ""],
        [2, "08:30:00", "09:00:00", "0:30:00", "1С Предприятие", ""],
        [3, "09:00:00", "09:15:00", "0:15:00", "Word", ""],
    ])
    path = save_wb(wb, tmp_path)
    m = parse_excel(path)
    assert m["onec_time"] == 60 * 60


def test_parse_sheet2_browsers(tmp_path):
    wb = make_workbook([
        [1, "08:00:00", "08:30:00", "0:30:00", "chrome.exe - Google", ""],
        [2, "08:30:00", "09:00:00", "0:30:00", "firefox.exe", ""],
        [3, "09:00:00", "09:15:00", "0:15:00", "yandex.exe", ""],
        [4, "09:15:00", "09:30:00", "0:15:00", "Word", ""],
    ])
    path = save_wb(wb, tmp_path)
    m = parse_excel(path)
    assert m["browser_time"] == 75 * 60


def test_parse_sheet1_achievements(tmp_path):
    wb = make_workbook(
        [[1, "08:00:00", "09:00:00", "1:00:00", "Work", ""]],
        sheet1_rows=[
            [1, "08:00", "1:00", "Зарплата начислена"],
            [2, "09:00", "0:30", "Отчёт сдан"],
        ]
    )
    path = save_wb(wb, tmp_path)
    m = parse_excel(path)
    assert m["achievements"] == "Зарплата начислена; Отчёт сдан"


def test_parse_sheet1_empty(tmp_path):
    wb = make_workbook(
        [[1, "08:00:00", "09:00:00", "1:00:00", "Work", ""]],
    )
    path = save_wb(wb, tmp_path)
    m = parse_excel(path)
    assert m["achievements"] is None


def test_parse_idle_excluded(tmp_path):
    wb = make_workbook([
        [1, "08:00:00", "08:30:00", "0:30:00", "Work", ""],
        [2, "08:30:00", "09:00:00", "0:30:00", "Простой системы", ""],
        [3, "09:00:00", "09:30:00", "0:30:00", "Режим ожидания", ""],
    ])
    path = save_wb(wb, tmp_path)
    m = parse_excel(path)
    assert m["active_time"] == 30 * 60
    assert m["duration"] == 90 * 60


def test_parse_late_report_updates_db(tmp_path):
    import database
    wb = make_workbook([
        [1, "08:00:00", "09:00:00", "1:00:00", "Work", ""],
    ])
    path = save_wb(wb, tmp_path, "report.xlsx")
    m = parse_excel(path)
    database.upsert_metrics("testuser", "2026-06-10", m)
    database.upsert_employee("testuser", "2026-06-10")

    wb2 = make_workbook([
        [1, "08:00:00", "10:00:00", "2:00:00", "Work", ""],
    ])
    path2 = save_wb(wb2, tmp_path, "report2.xlsx")
    m2 = parse_excel(path2)
    database.upsert_metrics("testuser", "2026-06-10", m2)

    data = database.get_metrics_for_date("2026-06-10")
    assert data["testuser"]["active_time"] == 7200
