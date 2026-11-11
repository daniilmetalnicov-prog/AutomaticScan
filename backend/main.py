from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from .api import (
    auth, groups, hosts, jobs, process_runs, audit_logs,
    scan_results, process_logs, stage_runs, state_history, dmn_rules, health
)
from .core.exception_handlers import (
    integrity_error_handler,
    operational_error_handler,
    sqlalchemy_error_handler
)

app = FastAPI(title="AutomaticScan API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрация обработчиков ошибок БД
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(OperationalError, operational_error_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)


# Регистрация роутеров
app.include_router(auth.router)
app.include_router(hosts.router)
app.include_router(groups.router)
app.include_router(jobs.router)
app.include_router(process_runs.router)
app.include_router(stage_runs.router)
app.include_router(scan_results.router)
app.include_router(process_logs.router)
app.include_router(audit_logs.router)
app.include_router(state_history.router)
app.include_router(dmn_rules.router)
app.include_router(health.router)


@app.get("/health")
async def root_health_check():
    """Базовая проверка работоспособности сервера."""
    return {"status": "ok", "service": "AutomaticScan API"}