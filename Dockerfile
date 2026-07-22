FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    curl \
    tar \
    ca-certificates \
    python3 \
    python3-pip \
    libffi-dev \
    libopus-dev \
    libsodium-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Установка py-cord с голосовой поддержкой
RUN pip3 install --no-cache-dir --prefer-binary "py-cord[voice]>=2.4.1"

# Установка Bore туннеля
RUN curl -sSL https://github.com/ekzhang/bore/releases/download/v0.5.2/bore-v0.5.2-x86_64-unknown-linux-musl.tar.gz | tar -C /usr/local/bin -xz && chmod +x /usr/local/bin/bore

# Копируем файлы
COPY server.py /server.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Создаем временную директорию для портов
RUN mkdir -p /tmp

ENTRYPOINT ["/entrypoint.sh"]
