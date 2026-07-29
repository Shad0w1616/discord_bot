FROM python:3.11-slim


WORKDIR /app


ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1


# Системные зависимости:
# ffmpeg  - проигрывание аудио
# libopus - Discord voice
# ca-certificates - HTTPS
# curl - диагностика

RUN apt-get update && \
    apt-get install -y \
    ffmpeg \
    libopus0 \
    ca-certificates \
    curl && \
    rm -rf /var/lib/apt/lists/*



COPY requirements.txt .


RUN pip install --no-cache-dir \
    -r requirements.txt



COPY . .


CMD ["python","app.py"]