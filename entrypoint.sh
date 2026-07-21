#!/bin/bash

echo "=== Запуск ngIRCd ==="
ngircd

echo "=== Запуск веб-заглушки для Render на порту $PORT ==="
python3 -m http.server $PORT &

echo "=== Запуск туннеля Serveo ==="
# Автоматически принимаем ключи сервера и пробрасываем порт 6667 наружу
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -R 0:127.0.0.1:6667 serveo.net
