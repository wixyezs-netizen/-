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

# Копируем код
COPY main.py .

# Создаем папку для базы данных
RUN mkdir -p data

# Открываем порт
EXPOSE 8080

# Запускаем
CMD ["python", "main.py"]
