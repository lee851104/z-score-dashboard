FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd --create-home --uid 1000 appuser
WORKDIR /app

RUN pip install uv==0.12.17
COPY pyproject.toml uv.lock ./
COPY configs/ ./configs/
COPY src/ ./src/
RUN uv sync --frozen --no-dev --extra serve --no-editable

COPY --chown=appuser:appuser server.py ./

USER appuser
EXPOSE 7860
CMD ["/app/.venv/bin/gunicorn", "--bind", "0.0.0.0:7860", "--workers", "1", "--threads", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "zscore_dashboard.serving.app:create_app()"]
