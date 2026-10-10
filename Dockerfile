FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Cài phụ thuộc trước để tận dụng cache layer của Docker.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Chỉ copy mã nguồn; không copy .env, DB, MP3 (đã loại trong .dockerignore).
COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY scripts ./scripts

# Chạy bằng user không phải root; thư mục dữ liệu thuộc user này để named volume kế thừa quyền.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data /app/audio_files \
    && chown -R appuser:appuser /app
USER appuser

ENV DATABASE_URL=sqlite:////app/data/app.db \
    AUDIO_DIR=/app/audio_files

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

# Áp migration (chạy lặp an toàn) rồi mở service ở 0.0.0.0:8000.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
