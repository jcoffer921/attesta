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
    for key in ('SECRET_KEY', 'DEBUG', 'ALLOWED_HOSTS', 'GEMINI_API_KEY', 'DATABASE_PATH'):
        env.pop(key, None)
    return env
