# Система Порядка — Прогресс реализации

## Статус: Сервер развёрнут и работает на VPS ✅

### Дата последнего обновления: 22 июня 2026

### Что сделано
- ✅ Полная реализация серверного дашборда (FastAPI + SQLite + Jinja2)
- ✅ 21 тест — все проходят
- ✅ GitHub push работает (права настроены)
- ✅ PR создан и смержен в main
- ✅ Дизайн дашборда — тёмная премиум-тема по брендбуку (Manrope, #0B1321, #355C8A, #D4AF7A)
- ✅ Деплой на VPS 46.149.68.148 (HTTP, порт 80, nginx → uvicorn:8001)
- ✅ Загрузка отчётов работает (POST /upload/{login})
- ✅ Парсинг Excel-отчётов работает (исправлен баг с silent exception)
- ✅ Дашборд отображает данные сотрудников
- ✅ Скачивание отчётов работает

### VPS: Как устроен сервер
- **IP:** 46.149.68.148 (Timeweb)
- **OS:** Ubuntu 24.04.4 LTS, hostname msk-1-vm-5gcp
- **nginx:** порт 80 (HTTP) → proxy_pass 127.0.0.1:8001
- **systemd:** `workday.service` → `/opt/workday/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001`
- **Python venv:** `/opt/workday/venv/`
- **Код:** `/opt/workday/` (main.py, parser.py, database.py, config.py, cleanup.py, templates/)
- **Uploads:** `/opt/workday/uploads/{login}/{date}.xlsx`
- **БД:** `/opt/workday/metrics.db`
- **Дашборд:** http://46.149.68.148/login (пароль: порядок2026)
- **API токен:** X-API-Token: SP2026secure

### Исправления 22.06.2026
1. `except Exception: pass` → `logger.exception(...)` — ошибки парсера теперь логируются
2. `upsert_employee` вынесен из try/except — сотрудник регистрируется всегда
3. Парсер обрабатывает Excel с 1 листом (раньше возвращал пустые данные)
4. Пересоздана таблица `daily_metrics` с UNIQUE(login, date) constraint на VPS

### Структура
```
server/
├── config.py          # Конфигурация
├── database.py        # SQLite (daily_metrics, known_employees)
├── parser.py          # Парсинг Excel-отчётов
├── main.py            # FastAPI приложение
├── cleanup.py         # Автоочистка старых файлов
├── requirements.txt   # Зависимости
├── templates/
│   ├── login.html     # Страница входа (тёмная тема)
│   └── dashboard.html # Дашборд (тёмная тема)
└── tests/
    ├── conftest.py    # Фикстуры
    ├── test_parser.py # 8 тестов парсера
    ├── test_api.py    # 3 теста API
    ├── test_dashboard.py # 7 тестов дашборда
    └── test_cleanup.py   # 3 теста очистки
```

### Как обновить код на VPS
```bash
cd /opt/workday
curl -sL "https://raw.githubusercontent.com/romshil6973-droid/my-first-repo/claude/brave-franklin-xtgrz9/server/main.py" -o main.py
curl -sL "https://raw.githubusercontent.com/romshil6973-droid/my-first-repo/claude/brave-franklin-xtgrz9/server/parser.py" -o parser.py
systemctl restart workday
```

### Что осталось сделать
- [ ] Настроить WorkdayMonitor (приложение на ПК) для автоматической отправки отчётов на сервер
      (сейчас приложение v1.x отправляет на Google Drive, нужно обновить до v2.0 с серверной отправкой)
      Код v2.0 уже написан в репозитории romshil6973-droid/- но не установлен на ПК сотрудников
- [ ] PyInstaller: упаковать WorkdayMonitor в .exe (Этап 7 из ТЗ)
- [ ] Inno Setup: создать установщик WorkdayMonitor_Setup.exe (Этап 7 из ТЗ)
- [ ] Добавить HTTPS на VPS (сейчас HTTP)
- [ ] Материнское приложение v2.1 (агрегирование отчётов через сервер)

### Запуск тестов
```bash
cd server && python -m pytest tests/ -v
```
