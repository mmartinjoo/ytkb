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

ingestion-download-step:
	uv run ingestion-download-step
	
ingestion-chunk-step:
	uv run ingestion-chunk-step
	
ingestion-transcribe-step:
	uv run ingestion-transcribe-step
	
ingestion-embed-step:
	uv run ingestion-embed-step
	
ingestion-index-step:
	uv run ingestion-index-step
	