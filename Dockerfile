FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml LICENSE ./
COPY api ./api
COPY ml ./ml
COPY database ./database
RUN python -m pip install --upgrade pip && python -m pip install '.[ml]'

RUN useradd --create-home --uid 10001 hca && chown -R hca:hca /app
USER hca

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; r=urllib.request.Request('http://127.0.0.1:8000/health/live', headers={'X-Forwarded-Proto':'https'}); urllib.request.urlopen(r, timeout=3)"

CMD ["uvicorn", "app.main:app", "--app-dir", "api", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
