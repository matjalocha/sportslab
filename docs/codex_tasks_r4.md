# Codex Tasks — R4 Automation

| Task | Nazwa | Pliki | SPO |
|------|-------|-------|-----|
| R4-01 | Dockerfile + docker-compose | infra/Dockerfile, docker-compose.yml, .env.example | SPO-71 |
| R4-02 | Postgres support | settings.py, database.py, pyproject.toml | SPO-72 |
| R4-03 | SQLite→Postgres migration | cli/migrate_cmd.py | SPO-72 |
| R4-04 | Cron wrapper + daily pipeline | infra/daily_pipeline.py, infra/crontab.example | SPO-73 |
| R4-05 | Backup script | infra/backup.sh, infra/restore.sh | SPO-75 |
| R4-06 | Monitoring (healthchecks.io) | notification/healthcheck.py, settings.py | SPO-74 |

Prompty: `docs/codex_prompts_r4.md`
Status output: `docs/codex_status_r4.md`
