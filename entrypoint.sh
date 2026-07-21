#!/bin/bash

echo "=== Запуск ngIRCd ==="
# Запуск IRC-сервера в фоне
ngircd

echo "=== Запуск веб-заглушки для Render на порту $PORT ==="
python3 -m http.server $PORT &

echo "=== Запуск туннеля Pinggy ==="
# -T отключает псевдо-терминал (уберет ошибку Pseudo-terminal in logs)
# -p 443 использует безопасный SSL-порт, который никогда не блокируется
# -R0:localhost:6667 запрашивает случайный TCP-порт для проброса нашего IRC
ssh -T -o StrictHostKeyChecking=no -p 443 -R0:localhost:6667 tcp@pinggy.io
