web: poetry run gunicorn "notifico:create_app()" --workers=4
bots: poetry run notifico bots start
worker: poetry run celery -A notifico.worker worker
release: poetry run alembic upgrade head