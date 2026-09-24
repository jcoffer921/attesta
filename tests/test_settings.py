import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def test_missing_secret_key_fails_loudly(no_env_file, clean_env):
    """With no .env and no SECRET_KEY in the environment, Django must refuse
    to start rather than silently falling back to an insecure default."""
    result = subprocess.run(
        [sys.executable, 'manage.py', 'check'],
        cwd=BASE_DIR,
        env=clean_env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert 'SECRET_KEY' in result.stderr or 'ImproperlyConfigured' in result.stderr


def test_debug_defaults_to_false_when_unset(no_env_file, clean_env):
    """DEBUG must default to False when the DEBUG env var is absent."""
    clean_env['SECRET_KEY'] = 'test-only-secret-key'
    result = subprocess.run(
        [
            sys.executable,
            '-c',
            'import django; django.setup(); from django.conf import settings; print(settings.DEBUG)',
        ],
        cwd=BASE_DIR,
        env={**clean_env, 'DJANGO_SETTINGS_MODULE': 'config.settings'},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'False'
