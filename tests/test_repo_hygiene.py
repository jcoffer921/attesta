import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def test_makemigrations_check_reports_no_pending_changes():
    result = subprocess.run(
        [sys.executable, 'manage.py', 'makemigrations', '--check', '--dry-run'],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_env_file_is_not_tracked_by_git():
    result = subprocess.run(
        ['git', 'ls-files'],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    tracked_files = result.stdout.splitlines()
    assert '.env' not in tracked_files
