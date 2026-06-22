"""
Скрипт автоматической отправки отчётов на сервер.
Устанавливается через Планировщик задач Windows с тремя триггерами:
  1. При входе пользователя в систему (отправка неотправленных за прошлые дни)
  2. Каждый день в 16:30 (промежуточный срез)
  3. Каждый день в 23:00 (полный отчёт за день)

Логика:
  - Находит все Excel-отчёты в папке отчётов приложения
  - Определяет какие ещё не отправлены (по файлу-маркеру .sent)
  - Отправляет на сервер
  - Помечает отправленные
"""

import glob
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SERVER_URL = "http://46.149.68.148"
API_TOKEN = "SP2026secure"

LOG_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "WorkdayMonitor" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "send_reports.log"


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def get_login() -> str | None:
    config_path = Path(os.environ.get("LOCALAPPDATA", "")) / "WorkdayMonitor" / "config.json"
    if not config_path.exists():
        return None
    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("login")
    except Exception:
        return None


def find_reports_dir() -> Path | None:
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "WorkdayMonitor" / "reports"
    if base.exists():
        return base
    docs = Path.home() / "Documents" / "WorkdayMonitor"
    if docs.exists():
        return docs
    return None


def find_unsent_reports(reports_dir: Path) -> list[Path]:
    unsent = []
    for xlsx in sorted(reports_dir.rglob("*.xlsx")):
        sent_marker = xlsx.with_suffix(".xlsx.sent")
        if not sent_marker.exists():
            unsent.append(xlsx)
    return unsent


def upload_report(filepath: Path, login: str) -> bool:
    try:
        with open(filepath, "rb") as f:
            resp = requests.post(
                f"{SERVER_URL}/upload/{login}",
                headers={"X-API-Token": API_TOKEN},
                files={"file": (filepath.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                timeout=30,
                verify=False,
            )
        if resp.status_code == 200:
            marker = filepath.with_suffix(".xlsx.sent")
            marker.write_text(datetime.now().isoformat(), encoding="utf-8")
            log(f"OK: {filepath.name} -> server")
            return True
        else:
            log(f"FAIL: {filepath.name} -> HTTP {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        log(f"ERROR: {filepath.name} -> {type(e).__name__}: {e}")
        return False


def main():
    log("=== send_reports started ===")

    login = get_login()
    if not login:
        log("No login found in config. Exiting.")
        return

    log(f"Login: {login}")

    reports_dir = find_reports_dir()
    if not reports_dir:
        log("Reports directory not found. Exiting.")
        return

    log(f"Reports dir: {reports_dir}")

    unsent = find_unsent_reports(reports_dir)
    if not unsent:
        log("No unsent reports found.")
        return

    log(f"Found {len(unsent)} unsent report(s)")

    sent = 0
    failed = 0
    for report in unsent:
        if upload_report(report, login):
            sent += 1
        else:
            failed += 1
        time.sleep(1)

    log(f"Done: {sent} sent, {failed} failed")


if __name__ == "__main__":
    main()
