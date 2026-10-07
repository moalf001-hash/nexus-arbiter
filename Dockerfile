# ==========================================
# المرحلة 1: بيئة البناء وتجميع الحزم (Builder)
# ==========================================
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# نسخ ملفات التبعيات وحزمة البروتوكول للتجميع
COPY requirements.txt pyproject.toml ./
COPY nexus_arbiter/ ./nexus_arbiter/

# تجميع عجلات التثبيت (Wheels) مع حزمة nexus_arbiter
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels .

# ==========================================
# المرحلة 2: صورة التشغيل الإنتاجية المعزولة (Runner)
# ==========================================
FROM python:3.11-slim AS runner

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# تثبيت sqlite3 فقط للتشغيل بدون أدوات ترجمة الكود
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# إنشاء مستخدم ومجموعة غير جذرية (Non-Root User) لتقييد الصلاحيات
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup --no-create-home appuser

WORKDIR /app

# تثبيت الحزم الجاهزة من مرحلة البناء
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# نسخ كود الخادم والقوالب وحزمة البروتوكول
COPY src/ ./src/
COPY templates/ ./templates/
COPY nexus_arbiter/ ./nexus_arbiter/

# تجهيز مجلد دائم لقاعدة بيانات SQLite-WAL ومنح ملكيته للمستخدم المقيد
RUN mkdir -p /app/data && chown -R appuser:appgroup /app

# تفعيل المستخدم المقيد أمنياً
USER appuser

EXPOSE 8000

# فحص دوري لجاهزية الخادم (Docker Healthcheck)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]