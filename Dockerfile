FROM ubuntu:22.04

# Устанавливаем ngircd, curl, tar и python3
RUN apt-get update && apt-get install -y \
    ngircd \
    curl \
    tar \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# Скачиваем и устанавливаем туннель Bore
RUN curl -sSL https://github.com/ekatech/bore/releases/download/v0.5.2/bore-v0.5.2-x86_64-unknown-linux-musl.tar.gz | tar -C /usr/local/bin -xz

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
