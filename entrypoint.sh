#!/bin/bash

echo "=== Запуск ngIRCd ==="
# Запускаем ngircd со стандартным, гарантированно рабочим конфигом Ubuntu
ngircd

echo "=== Запуск веб-заглушки для Render на порту $PORT ==="
python3 -m http.server $PORT &

echo "=== Запуск Discord-Моста ==="
if [ -n "$DISCORD_BOT_TOKEN" ]; then
  python3 /bridge.py &
else
  echo "DISCORD_BOT_TOKEN не задан. Мост Discord отключен."
fi

echo "=== Запуск туннеля Bore и отправка порта в Discord ==="
# Запускаем bore и перенаправляем вывод
bore local 6667 --to bore.pub 2>&1 | while read -r line; do
    echo "$line"
    if [[ "$line" =~ "listening at bore.pub:" ]]; then
        PORT_NUM=$(echo "$line" | sed -E 's/.*listening at bore.pub:([0-9]+).*/\1/')
        echo "🎉 Обнаружен новый порт: $PORT_NUM!"
        
        if [ -n "$DISCORD_WEBHOOK_URL" ]; then
            PAYLOAD=$(cat <<EOF
{
  "username": "IRC Server",
  "avatar_url": "https://i.imgur.com/vHpxTq3.png",
  "embeds": [
    {
      "title": "🚀 IRC-Сервер запущен и готов к работе!",
      "color": 3066993,
      "description": "Сервер успешно проснулся. Подключайтесь с друзьями!",
      "fields": [
        { "name": "📍 Host", "value": "\`bore.pub\`", "inline": true },
        { "name": "🔑 Port", "value": "\`$PORT_NUM\`", "inline": true },
        { "name": "💻 Команда запуска", "value": "\`./messenger.exe ВашеИмя bore.pub $PORT_NUM #secret\`" }
      ],
      "footer": { "text": "🎤 Голосовая связь: введите /voice в клиенте!" }
    }
  ]
}
EOF
)
            curl -H "Content-Type: application/json" -X POST -d "$PAYLOAD" "$DISCORD_WEBHOOK_URL"
        fi
    fi
done
