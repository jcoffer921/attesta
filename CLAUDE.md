@AGENTS.md

# Claude Code notes

- Project skills live in `.claude/skills/` (`run-tests`, `add-permit-rule`,
  `django-migration-check`, `npdes-dmr-compliance`,
  `evaluate-dmr-data`). Use them when the task matches.
- Shell is PowerShell/Git Bash on Windows; use `uv run ...` for Python.
- Before saying work is done, run `uv run pytest` and `raco test dsl/` and
  report real output.
- Don't touch `.env`; reference `.env.example` for new settings and update it.
- The working tree has many uncommitted changes; don't commit or revert
  unrelated files unless asked.
