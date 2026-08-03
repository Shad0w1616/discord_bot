FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Системные зависимости
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libopus0 \
        libopus-dev \
        ca-certificates \
        curl && \
    echo "precedence ::ffff:0:0/96 100" >> /etc/gai.conf && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Обновляем pip и инструменты сборки
RUN python -m pip install --upgrade \
        pip \
        setuptools \
        wheel && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]