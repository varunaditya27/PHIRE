Alembic migration scripts.

Initialized. `env.py` reads `DATABASE_URL` via `app.config.get_settings()`
and targets `Base.metadata` from `app.database.schemas`.

- New migration after a schema change: `alembic revision --autogenerate -m "..."`
- Apply: `alembic upgrade head`
- Run from `backend/` (alembic.ini lives there).
