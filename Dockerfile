FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY personalines ./personalines
RUN pip install --no-cache-dir ".[all]"

# Run unprivileged; job files are scratch space only.
RUN useradd --create-home --uid 10001 app && mkdir -p /app/Filing && chown app /app/Filing
USER app

EXPOSE 10000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"10000\")}/healthz', timeout=3)"

CMD ["python", "-m", "personalines", "webhook"]
