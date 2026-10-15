import os
import shutil
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / '.env'


@pytest.fixture
def no_env_file():
    """Temporarily move the real .env aside so subprocess settings tests
    exercise the environment-variable-only code path, then restore it."""
    backup = None
    if ENV_FILE.exists():
        backup = ENV_FILE.with_suffix('.bak-test')
        shutil.move(ENV_FILE, backup)
    try:
        yield
    finally:
        if backup is not None:
            shutil.move(backup, ENV_FILE)


@pytest.fixture
def clean_env():
    """A copy of the process environment stripped of Attesta's settings vars."""
    env = os.environ.copy()
    for key in ('SECRET_KEY', 'DEBUG', 'ALLOWED_HOSTS', 'GEMINI_API_KEY', 'ANTHROPIC_API_KEY', 'DATABASE_PATH'):
        env.pop(key, None)
    return env


@pytest.fixture
def admin_user(db):
    from apps.accounts.models import User

    return User.objects.create_user(username='admin-fixture', password='pw', role=User.Role.ADMIN)


@pytest.fixture
def org_user(db):
    from apps.accounts.models import User
    from apps.facilities.models import Organization

    org = Organization.objects.create(name='Acme Water', slug='acme-water')
    return User.objects.create_user(username='org-fixture', password='pw', role=User.Role.ORG, organization=org)


@pytest.fixture
def admin_client(client, admin_user):
    client.force_login(admin_user)
    return client


@pytest.fixture
def org_client(client, org_user):
    client.force_login(org_user)
    return client


@pytest.fixture(autouse=True)
def no_background_review(monkeypatch):
    """Never spawn the real Claude review thread from tests."""
    from apps.ingestion import review_jobs

    monkeypatch.setattr(review_jobs, "enqueue", lambda evidence_id, run: None)
