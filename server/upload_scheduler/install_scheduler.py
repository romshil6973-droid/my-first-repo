"""
Установка send_reports.py в Планировщик задач Windows.
Создаёт задачу "WorkdayMonitor_SendReports" с тремя триггерами:
  1. При входе пользователя (отправка за прошлые дни)
  2. Каждый день в 16:30 (промежуточный срез)
  3. Каждый день в 23:00 (полный отчёт)

Запуск: python install_scheduler.py
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

TASK_NAME = "WorkdayMonitor_SendReports"


def find_python() -> str:
    return sys.executable


def install():
    install_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "WorkdayMonitor"
    install_dir.mkdir(parents=True, exist_ok=True)

    script_src = Path(__file__).parent / "send_reports.py"
    script_dst = install_dir / "send_reports.py"
    shutil.copy2(script_src, script_dst)
    print(f"Скрипт скопирован: {script_dst}")

    python = find_python()

    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Автоотправка отчётов WorkdayMonitor на сервер</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <Delay>PT2M</Delay>
    </LogonTrigger>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T16:30:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T23:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
  </Settings>
  <Actions>
    <Exec>
      <Command>{python}</Command>
      <Arguments>"{script_dst}"</Arguments>
    </Exec>
  </Actions>
</Task>"""

    xml_path = install_dir / "task.xml"
    xml_path.write_text(xml, encoding="utf-16")

    subprocess.run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
                    capture_output=True)

    result = subprocess.run(
        ["schtasks", "/Create", "/TN", TASK_NAME, "/XML", str(xml_path)],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        print(f"\nГотово! Задача '{TASK_NAME}' создана.")
        print("Триггеры:")
        print("  - При входе в систему (через 2 мин)")
        print("  - Каждый день в 16:30")
        print("  - Каждый день в 23:00")
        print(f"\nЛог: {install_dir / 'logs' / 'send_reports.log'}")
    else:
        print(f"\nОшибка: {result.stderr}")
        print("Попробуйте запустить CMD от имени администратора")


if __name__ == "__main__":
    install()
