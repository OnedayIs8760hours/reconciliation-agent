FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY agent ./agent
COPY backend ./backend
COPY tools ./tools
COPY scripts ./scripts
COPY pyproject.toml README.md ./

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/backend/storage/tasks /app/outputs \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
