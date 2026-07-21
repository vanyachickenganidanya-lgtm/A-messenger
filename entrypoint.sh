#!/bin/bash

echo "=== Запуск ngIRCd ==="
ngircd

echo "=== Запуск веб-заглушки для Render на порту $PORT ==="
python3 -m http.server $PORT &

echo "=== Запуск туннеля Bore ==="
# Пробрасываем локальный порт 6667 на бесплатный сервер bore.pub
bore local 6667 --to bore.pub
