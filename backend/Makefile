migrate:
	uv run alembic revision --autogenerate
	uv run alembic upgrade head

worker:
	uv run celery -A ytkb.worker worker --loglevel=info