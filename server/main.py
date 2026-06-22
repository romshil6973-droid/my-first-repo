import logging
import os
import re
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import config
import database
from cleanup import cleanup_old_files
from parser import extract_date_from_filename, parse_excel

logger = logging.getLogger("workday")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Система Порядка")
app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


@app.on_event("startup")
async def startup():
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    database.init_db()
    cleanup_old_files()


# --- Auth helpers ---

def require_auth(request: Request):
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Not authenticated")


def require_api_token(x_api_token: str | None = Header(None)):
    if x_api_token != config.API_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid API token")


# --- Existing endpoints (kept as-is) ---

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/upload/{login}")
async def upload_report(
    login: str,
    file: UploadFile = File(...),
    x_api_token: str | None = Header(None),
):
    require_api_token(x_api_token)

    login_dir = Path(config.UPLOADS_DIR) / login
    login_dir.mkdir(parents=True, exist_ok=True)

    report_date = extract_date_from_filename(file.filename or "")
    if not report_date:
        report_date = date.today().isoformat()

    save_name = f"{report_date}.xlsx"
    save_path = login_dir / save_name

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    database.upsert_employee(login, report_date)

    try:
        metrics = parse_excel(str(save_path))
        database.upsert_metrics(login, report_date, metrics)
    except Exception:
        logger.exception("Failed to parse %s/%s", login, report_date)

    return {"status": "ok", "login": login, "date": report_date}


# --- Auth endpoints ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    password = form.get("password", "")
    if password == config.DASHBOARD_PASSWORD:
        request.session["authenticated"] = True
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": "Неверный пароль"})


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


# --- Dashboard ---

def fmt_seconds(seconds: int | None) -> str:
    if seconds is None or seconds == 0:
        return "—"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h}:{m:02d}"


def fmt_time(time_str: str | None) -> str:
    if not time_str:
        return "—"
    parts = time_str.split(":")
    if len(parts) >= 2:
        h, m = int(parts[0]), int(parts[1])
        return f"{h}:{m:02d}"
    return time_str


def prev_workday(d: date) -> date:
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def next_workday(d: date) -> date:
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, date: str | None = None):
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/login", status_code=303)

    today = datetime.now().date()
    if date:
        try:
            selected = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            selected = today
    else:
        selected = today

    employees = database.get_all_employees()
    metrics_map = database.get_metrics_for_date(selected.isoformat())

    rows = []
    for login in employees:
        m = metrics_map.get(login)
        if m:
            file_path = Path(config.UPLOADS_DIR) / login / f"{selected.isoformat()}.xlsx"
            archived_path = Path(config.UPLOADS_DIR) / login / f"{selected.isoformat()}.archived.xlsx"
            file_exists = file_path.exists() or archived_path.exists()
            is_archived = archived_path.exists()
            rows.append({
                "login": login,
                "has_data": True,
                "work_start": fmt_time(m.get("work_start")),
                "work_end": fmt_time(m.get("work_end")),
                "duration": fmt_seconds(m.get("duration")),
                "active_time": fmt_seconds(m.get("active_time")),
                "bitrix_time": fmt_seconds(m.get("bitrix_time")),
                "onec_time": fmt_seconds(m.get("onec_time")),
                "browser_time": fmt_seconds(m.get("browser_time")),
                "achievements": m.get("achievements") or "—",
                "file_exists": file_exists,
                "is_archived": is_archived,
            })
        else:
            rows.append({
                "login": login,
                "has_data": False,
                "work_start": "—", "work_end": "—", "duration": "—",
                "active_time": "—", "bitrix_time": "—", "onec_time": "—",
                "browser_time": "—", "achievements": "—",
                "file_exists": False, "is_archived": False,
            })

    rows.sort(key=lambda r: (not r["has_data"], r["login"]))

    total_employees = len(employees)
    reports_count = sum(1 for r in rows if r["has_data"])

    return templates.TemplateResponse(request, "dashboard.html", {
        "date": selected.isoformat(),
        "date_display": selected.strftime("%d.%m.%Y"),
        "prev_date": prev_workday(selected).isoformat(),
        "next_date": next_workday(selected).isoformat(),
        "rows": rows,
        "total_employees": total_employees,
        "reports_count": reports_count,
        "updated_at": datetime.now().strftime("%H:%M"),
        "is_export": False,
    })


# --- Download / Archive ---

@app.get("/download/{login}/{date}")
async def download_file(request: Request, login: str, date: str):
    require_auth(request)
    login = re.sub(r"[^a-zA-Z0-9_\-]", "", login)

    file_path = Path(config.UPLOADS_DIR) / login / f"{date}.xlsx"
    archived_path = Path(config.UPLOADS_DIR) / login / f"{date}.archived.xlsx"

    if archived_path.exists():
        return FileResponse(str(archived_path), filename=f"{login}_{date}.xlsx")
    if file_path.exists():
        return FileResponse(str(file_path), filename=f"{login}_{date}.xlsx")

    raise HTTPException(status_code=404, detail="Файл удалён")


@app.post("/archive/{login}/{date}")
async def archive_file(request: Request, login: str, date: str):
    require_auth(request)
    login = re.sub(r"[^a-zA-Z0-9_\-]", "", login)

    file_path = Path(config.UPLOADS_DIR) / login / f"{date}.xlsx"
    archived_path = Path(config.UPLOADS_DIR) / login / f"{date}.archived.xlsx"

    if archived_path.exists():
        return {"status": "already_archived"}
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")

    file_path.rename(archived_path)
    return {"status": "archived"}


# --- Export dashboard as self-contained HTML ---

@app.get("/dashboard/export", response_class=HTMLResponse)
async def export_dashboard(request: Request, date: str | None = None):
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401)

    today = datetime.now().date()
    if date:
        try:
            selected = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            selected = today
    else:
        selected = today

    employees = database.get_all_employees()
    metrics_map = database.get_metrics_for_date(selected.isoformat())

    rows = []
    for login in employees:
        m = metrics_map.get(login)
        if m:
            rows.append({
                "login": login, "has_data": True,
                "work_start": fmt_time(m.get("work_start")),
                "work_end": fmt_time(m.get("work_end")),
                "duration": fmt_seconds(m.get("duration")),
                "active_time": fmt_seconds(m.get("active_time")),
                "bitrix_time": fmt_seconds(m.get("bitrix_time")),
                "onec_time": fmt_seconds(m.get("onec_time")),
                "browser_time": fmt_seconds(m.get("browser_time")),
                "achievements": m.get("achievements") or "—",
                "file_exists": False, "is_archived": False,
            })
        else:
            rows.append({
                "login": login, "has_data": False,
                "work_start": "—", "work_end": "—", "duration": "—",
                "active_time": "—", "bitrix_time": "—", "onec_time": "—",
                "browser_time": "—", "achievements": "—",
                "file_exists": False, "is_archived": False,
            })

    rows.sort(key=lambda r: (not r["has_data"], r["login"]))
    total_employees = len(employees)
    reports_count = sum(1 for r in rows if r["has_data"])

    return templates.TemplateResponse(request, "dashboard.html", {
        "date": selected.isoformat(),
        "date_display": selected.strftime("%d.%m.%Y"),
        "prev_date": "",
        "next_date": "",
        "rows": rows,
        "total_employees": total_employees,
        "reports_count": reports_count,
        "updated_at": datetime.now().strftime("%H:%M"),
        "is_export": True,
    }, headers={
        "Content-Disposition": f'attachment; filename="dashboard_{selected.isoformat()}.html"'
    })


# --- Files listing (for parent app compatibility) ---

@app.get("/files")
async def list_files(
    date: str | None = None,
    x_api_token: str | None = Header(None),
):
    require_api_token(x_api_token)
    if not date:
        date = datetime.now().date().isoformat()

    base = Path(config.UPLOADS_DIR)
    result = []
    if base.exists():
        for login_dir in sorted(base.iterdir()):
            if not login_dir.is_dir():
                continue
            for f in login_dir.iterdir():
                if date in f.name and f.suffix == ".xlsx":
                    result.append({
                        "login": login_dir.name,
                        "filename": f.name,
                    })
    return result


@app.get("/download/{login}/{filename:path}")
async def download_by_filename(
    login: str,
    filename: str,
    x_api_token: str | None = Header(None),
):
    require_api_token(x_api_token)
    login = re.sub(r"[^a-zA-Z0-9_\-]", "", login)
    filename = re.sub(r"[^a-zA-Z0-9_\-\.]", "", filename)
    file_path = Path(config.UPLOADS_DIR) / login / filename
    if not file_path.exists():
        raise HTTPException(status_code=404)
    return FileResponse(str(file_path), filename=filename)
