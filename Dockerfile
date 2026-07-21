FROM ubuntu:22.04

# Устанавливаем ngircd, curl, python3 (нужен для обмана проверок Render)
RUN apt-get update && apt-get install -y \
    ngircd \
    curl \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# Скачиваем и устанавливаем ngrok
RUN curl -s https://ngrok-agent.s3.amazonaws.com/files.bin/linux/amd64/ngrok.tgz -o ngrok.tgz \
    && tar -xf ngrok.tgz -C /usr/local/bin \
    && rm ngrok.tgz

# Копируем скрипт запуска
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
