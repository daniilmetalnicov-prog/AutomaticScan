# Импорт всех моделей для регистрации в SQLAlchemy
from .user import User
from .group import Group
from .host import Host
from .job import Job
from .process_run import ProcessRun
from .stage_run import StageRun
from .scan_result import ScanResult
from .process_log import ProcessLog
from .audit_log import AuditLog
from .state_history import StateHistory
from .dmn_rule import DmnRule
from .system_config import SystemConfig
from .report import Report, ReportTemplate, AnalyticsReport