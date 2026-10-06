# استخدام بيئة بايثون خفيفة ومستقرة
FROM python:3.11-slim

# ضبط المتغيرات لمنع التخزين المؤقت لمخرجات الطرفية في بايثون
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# تثبيت متطلبات النظام الأساسية ومكتبات التجميع
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# نسخ ملفات التثبيت أولاً للاستفادة من الـ Docker Layer Caching
COPY requirements.txt .

# تثبيت حزم بايثون
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود المصدري للمشروع وملفات البناء
COPY src/ ./src/
COPY build/ ./build/

# إنشاء مجلد دائم لقاعدة البيانات داخل الحاوية
RUN mkdir -p /app/data

# المنفذ الافتراضي للـ API
EXPOSE 8000

# تشغيل الخادم عبر Uvicorn مع خيوط معالجة إنتاجية
CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
