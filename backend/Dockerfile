FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Faqat ishlash uchun kerak bo'lgan paketlar (test paketlarisiz).
RUN pip install --no-cache-dir "fastapi>=0.110" "uvicorn>=0.29" "pydantic>=2.6" "PyJWT>=2.8" "psycopg[binary,pool]>=3.1" "cryptography>=42"

COPY app ./app

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# DIQQAT: bitta jarayon (--workers 1). Ma'lumot hozircha xotirada, ko'p jarayonda foydalanuvchilar yo'qoladi.
# $PORT — Render va shunga o'xshash xostlar beradi; bo'lmasa 8000.
CMD ["sh", "-c", "exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
