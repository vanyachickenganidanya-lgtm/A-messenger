#!/bin/bash

# Создаем надежный и простой конфиг ngircd
mkdir -p /etc/ngircd
cat <<EOF > /etc/ngircd/ngircd.conf
[Global]
  Name = irc.messenger.local
  Info = Server
  Ports = 6667

[Limits]
  MaxConnections = 1000
  MaxConnectionsIP = 20
  MaxNickLength = 20
EOF

echo "=== Запуск ngIRCd ==="
ngircd -f /etc/ngircd/ngircd.conf

echo "=== Запуск веб-сервера ==="
python3 /web_server.py &

echo "=== Запуск Discord-Моста ==="
if [ -n "$DISCORD_BOT_TOKEN" ]; then
  python3 /bridge.py &
else
  echo "DISCORD_BOT_TOKEN не задан. Мост отключен."
fi

echo "=== Запуск туннеля Bore ==="
bore local 6667 --to bore.pub 2>&1 | while read -r line; do
    echo "$line"
    if [[ "$line" =~ "listening at bore.pub:" ]]; then
        PORT_NUM=$(echo "$line" | sed -E 's/.*listening at bore.pub:([0-9]+).*/\1/')
        echo "$PORT_NUM" > /tmp/bore_port
        
        # Отправляем красивый отчет в Discord через вебхук
        if [ -n "$DISCORD_WEBHOOK_URL" ]; then
            PAYLOAD=$(cat <<EOF
{
  "username": "IRC Server",
  "avatar_url": "https://i.imgur.com/vHpxTq3.png",
  "embeds": [{
    "title": "🚀 IRC-Сервер запущен и готов к работе!",
    "color": 3066993,
    "description": "Сервер успешно запущен. Клиенты теперь подключаются автоматически без ручного ввода портов!",
    "fields": [
      { "name": "📍 Host", "value": "\`bore.pub\`", "inline": true },
      { "name": "🔑 Port", "value": "\`$PORT_NUM\`", "inline": true }
    ]
  }]
}
EOF
)
            curl -H "Content-Type: application/json" -X POST -d "$PAYLOAD" "$DISCORD_WEBHOOK_URL"
        fi
    fi
done
