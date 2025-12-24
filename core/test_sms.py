import requests

# ТВОИ ДАННЫЕ
BOT_TOKEN = "8528750312:AAHpUK46s3Tf7XKTaBRxqO0emcaX9OZyDgw"  # ← ВСТАВЬ СЮДА
CHAT_ID = "6131066491"       # ← И СЮДА

# Тестовый номер (ЗАМЕНИ на свой!)
test_phone = "9123456789"
test_message = "Тест SMS Gateway. Работает!"

# Формируем команду для Android
command = f"SMS:{test_phone}:{test_message}"

# Отправляем в Telegram
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
data = {
    "chat_id": CHAT_ID,
    "text": command
}

print("📱 Отправка команды через Telegram...")
response = requests.post(url, json=data)

if response.status_code == 200:
    print("✅ Команда отправлена!")
    print("Проверь Android приложение - должно появиться в логах")
    print("И SMS должно отправиться!")
else:
    print(f"❌ Ошибка: {response.text}")