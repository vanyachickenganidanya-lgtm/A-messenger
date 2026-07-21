FROM ubuntu:22.04

# Устанавливаем ngircd, стандартный ssh-клиент и python3
RUN apt-get update && apt-get install -y \
    ngircd \
    openssh-client \
    python3 \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
