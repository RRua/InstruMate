"""Persistent job store backed by SQLite.

Replaces the four separate in-memory dicts that were lost on restart.
"""

import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone

from api.models import AnalysisStatus, JobStatus

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.environ.get("INSTRUMATE_OUTPUT_DIR", "./output")
DB_PATH = os.path.join(OUTPUT_DIR, "jobs.db")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id     TEXT PRIMARY KEY,
    status     TEXT NOT NULL DEFAULT 'pending',
    message    TEXT,
    app_id     TEXT,
    job_type   TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


class JobStore:
    """SQLite-backed job persistence with thread-local connections."""

    def __init__(self):
        self._local = threading.local()
        self._init_lock = threading.Lock()
        self._initialized = False

    def _get_conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        if not self._initialized:
            with self._init_lock:
                if not self._initialized:
                    conn.execute(_CREATE_TABLE)
                    conn.commit()
                    self._initialized = True
        return conn

    def create(
        self,
        job_id: str,
        status: AnalysisStatus = AnalysisStatus.PENDING,
        message: str | None = None,
        app_id: str | None = None,
        job_type: str | None = None,
    ) -> JobStatus:
        """Insert a new job and return its JobStatus."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO jobs (job_id, status, message, app_id, job_type, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (job_id, status.value, message, app_id, job_type, now, now),
        )
        conn.commit()
        return JobStatus(job_id=job_id, status=status, message=message, app_id=app_id)

    def get(self, job_id: str) -> JobStatus | None:
        """Fetch a job by ID. Returns None if not found."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT job_id, status, message, app_id FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        return JobStatus(
            job_id=row["job_id"],
            status=AnalysisStatus(row["status"]),
            message=row["message"],
            app_id=row["app_id"],
        )

    def update(
        self,
        job_id: str,
        status: AnalysisStatus | None = None,
        message: str | None = None,
        app_id: str | None = None,
    ) -> JobStatus | None:
        """Update fields on an existing job. Returns updated JobStatus or None."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT job_id, status, message, app_id FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return None

        new_status = status.value if status else row["status"]
        new_message = message if message is not None else row["message"]
        new_app_id = app_id if app_id is not None else row["app_id"]
        now = datetime.now(timezone.utc).isoformat()

        conn.execute(
            "UPDATE jobs SET status = ?, message = ?, app_id = ?, updated_at = ? WHERE job_id = ?",
            (new_status, new_message, new_app_id, now, job_id),
        )
        conn.commit()
        return JobStatus(
            job_id=job_id,
            status=AnalysisStatus(new_status),
            message=new_message,
            app_id=new_app_id,
        )


# Module-level singleton
job_store = JobStore()
