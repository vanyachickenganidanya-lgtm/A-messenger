#!/bin/bash

echo "=== Запуск ngIRCd ==="
ngircd

echo "=== Запуск веб-заглушки для Render на порту $PORT ==="
# Render требует, чтобы приложение слушало веб-порт, иначе он посчитает запуск неудачным
python3 -m http.server $PORT &

echo "=== Запуск туннеля Ngrok ==="
if [ -z "$NGROK_AUTHTOKEN" ]; then
  echo "ОШИБКА: Переменная NGROK_AUTHTOKEN не задана в настройках Render!"
  exit 1
fi

ngrok config add-authtoken "$NGROK_AUTHTOKEN"
# Запускаем ngrok и выводим логи прямо в консоль Render
ngrok tcp 6667 --log=stdout
