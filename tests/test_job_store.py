"""Tests for the SQLite-backed JobStore."""

import os
import threading

import pytest

from api.models import AnalysisStatus


@pytest.fixture
def store(tmp_path):
    """Create a fresh JobStore pointing at a temp DB."""
    import api.job_store
    api.job_store.DB_PATH = os.path.join(str(tmp_path), "test_jobs.db")

    from api.job_store import JobStore
    s = JobStore()
    return s


def test_create_and_get(store):
    job = store.create("job-1", status=AnalysisStatus.PENDING, message="test", job_type="analysis")
    assert job.job_id == "job-1"
    assert job.status == AnalysisStatus.PENDING

    fetched = store.get("job-1")
    assert fetched is not None
    assert fetched.job_id == "job-1"
    assert fetched.message == "test"


def test_get_nonexistent(store):
    assert store.get("no-such-job") is None


def test_update(store):
    store.create("job-2", status=AnalysisStatus.PENDING)
    updated = store.update("job-2", status=AnalysisStatus.RUNNING, message="working")
    assert updated.status == AnalysisStatus.RUNNING
    assert updated.message == "working"


def test_update_partial(store):
    store.create("job-3", status=AnalysisStatus.PENDING, message="initial")
    updated = store.update("job-3", message="just message")
    assert updated.status == AnalysisStatus.PENDING  # unchanged
    assert updated.message == "just message"


def test_update_nonexistent(store):
    assert store.update("ghost-job", status=AnalysisStatus.FAILED) is None


def test_persistence_across_instances(tmp_path):
    """Verify jobs survive across JobStore instances (simulates restart)."""
    import api.job_store
    db_path = os.path.join(str(tmp_path), "persist_test.db")
    api.job_store.DB_PATH = db_path

    from api.job_store import JobStore
    store1 = JobStore()
    store1.create("persist-1", status=AnalysisStatus.COMPLETED, message="done", app_id="app-x")

    # New instance, same DB
    store2 = JobStore()
    fetched = store2.get("persist-1")
    assert fetched is not None
    assert fetched.status == AnalysisStatus.COMPLETED
    assert fetched.app_id == "app-x"


def test_thread_safety(store):
    """Verify concurrent creates don't crash."""
    errors = []

    def create_job(i):
        try:
            store.create(f"thread-job-{i}", status=AnalysisStatus.PENDING)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=create_job, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    for i in range(10):
        assert store.get(f"thread-job-{i}") is not None
