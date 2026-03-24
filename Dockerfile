FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости системы
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Проверяем установку (без проверки executor)
RUN python -c "import aiogram; print(f'✅ aiogram {aiogram.__version__} установлен')" && \
    python -c "from fastapi import FastAPI; print('✅ FastAPI установлен')" && \
    python -c "import aiosqlite; print('✅ aiosqlite установлен')"

# Копируем весь проект
COPY . .

# Создаем папку для базы данных
RUN mkdir -p /app/data

# Открываем порт
EXPOSE 8080

# Запускаем приложение
CMD ["python", "main.py"]
