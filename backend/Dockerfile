# Build context: ./backend   (docker build -t tokyo-planner ./backend)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

# Pinned runtime dependencies only (tests need requirements-dev.txt, which is not installed here)
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
USER appuser

# Hosts such as Render set PORT (default 10000 there). Our own client-IP logic reads X-Forwarded-For,
# so uvicorn's proxy-header rewriting is switched off, and its access log (which can contain query strings) is off.
ENV PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8000'), timeout=4)"
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-access-log --no-proxy-headers"]
