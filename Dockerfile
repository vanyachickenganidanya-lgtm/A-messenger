FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    ngircd \
    curl \
    tar \
    ca-certificates \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем библиотеку для Discord
RUN pip3 install discord.py

RUN curl -sSL https://github.com/ekzhang/bore/releases/download/v0.5.2/bore-v0.5.2-x86_64-unknown-linux-musl.tar.gz | tar -C /usr/local/bin -xz

COPY bridge.py /bridge.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
