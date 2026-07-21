#!/bin/bash

echo "=== Запуск ngIRCd ==="
ngircd

echo "=== Запуск веб-заглушки для Render на порту $PORT ==="
python3 -m http.server $PORT &

echo "=== Запуск туннеля Bore и отправка порта в Discord ==="

# Запускаем bore и читаем его вывод построчно
bore local 6667 --to bore.pub 2>&1 | while read -r line; do
    # Выводим строку в логи Render, чтобы вы видели их на сайте
    echo "$line"
    
    # Ищем строку "listening at bore.pub:"
    if [[ "$line" =~ "listening at bore.pub:" ]]; then
        # Вырезаем порт с помощью sed
        PORT_NUM=$(echo "$line" | sed -E 's/.*listening at bore.pub:([0-9]+).*/\1/')
        
        echo "🎉 Обнаружен новый порт: $PORT_NUM!"
        
        # Если переменная с вебхуком задана в Render, отправляем сообщение
        if [ -n "$DISCORD_WEBHOOK_URL" ]; then
            echo "Отправка уведомления в Discord..."
            
            # Красивое JSON-сообщение для Discord с разметкой
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
        {
          "name": "📍 Адрес (Host)",
          "value": "\`bore.pub\`",
          "inline": true
        },
        {
          "name": "🔑 Порт (Port)",
          "value": "\`$PORT_NUM\`",
          "inline": true
        },
        {
          "name": "💻 Команда для запуска",
          "value": "\`./messenger.exe ВашеИмя bore.pub $PORT_NUM #secret\`"
        }
      ],
      "footer": {
        "text": "Разработано специально для парковок 🚗"
      }
    }
  ]
}
EOF
)
            # Отправляем POST-запрос в Discord
            curl -H "Content-Type: application/json" -X POST -d "$PAYLOAD" "$DISCORD_WEBHOOK_URL"
        else
            echo "Предупреждение: Переменная DISCORD_WEBHOOK_URL не настроена."
        fi
    fi
done
