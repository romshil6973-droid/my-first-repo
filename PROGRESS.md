# Система Порядка — Прогресс реализации

## Статус: код готов, ожидает push на GitHub

### Что сделано
- Полная реализация серверного дашборда по спецификации TZ_Server_Dashboard_v1.0.md
- 21 тест — все проходят
- 2 коммита на ветке `claude/brave-franklin-xtgrz9` (локально)

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
│   ├── login.html     # Страница входа
│   └── dashboard.html # Дашборд
└── tests/
    ├── conftest.py    # Фикстуры
    ├── test_parser.py # 8 тестов парсера
    ├── test_api.py    # 3 теста API
    ├── test_dashboard.py # 7 тестов дашборда
    └── test_cleanup.py   # 3 теста очистки
```

### Блокер
GitHub интеграция Claude Code не имеет прав `contents: write` на репозиторий.
Все попытки push (git push, MCP push_files, create_branch, create_or_update_file) возвращают 403.

### Что нужно сделать
1. Предоставить интеграции Claude Code права на запись:
   - GitHub Settings > Applications > Claude Code > Configure
   - Добавить `my-first-repo` и дать `Contents: Read & Write`
2. После этого: `git push -u origin claude/brave-franklin-xtgrz9`
3. Деплой на VPS 46.149.68.148

### Запуск тестов
```bash
cd server && python -m pytest tests/ -v
```

### Запуск сервера
```bash
cd server && uvicorn main:app --host 0.0.0.0 --port 8443
```
