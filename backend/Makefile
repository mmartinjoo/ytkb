migrate:
	uv run alembic revision --autogenerate
	uv run alembic upgrade head

makemigration:
	uv run alembic revision --autogenerate

runmigration:
	uv run alembic upgrade head

worker:
	uv run celery -A ytkb.worker worker --loglevel=info

scheduler:
	uv run celery -A ytkb.scheduler beat --loglevel=info

api:
	uv run api