FROM python:3.11-slim

# системные зависимости для build (asyncpg, psycopg, и т.д.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# скопировать только requirements сначала для кеша
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

# копируем проект
COPY . /app

# запуск от не-root (опционально)
RUN useradd -m botuser || true
USER botuser

CMD ["python", "-m", "app.main"]


