import os

DASHBOARD_PASSWORD = os.environ.get("SP_DASHBOARD_PASSWORD", "порядок2026")

RETENTION_WORKING_DAYS = 30

UPLOADS_DIR = os.environ.get("SP_UPLOADS_DIR", "/opt/workday/uploads")
DB_PATH = os.environ.get("SP_DB_PATH", "/opt/workday/metrics.db")

TIMEZONE = "Europe/Moscow"

API_TOKEN = "SP2026secure"

SESSION_SECRET = os.environ.get("SP_SESSION_SECRET", "sp-secret-key-change-in-production")
SESSION_MAX_AGE = 86400  # 24 hours
