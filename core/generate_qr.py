from sms_processor import SMSProcessor

# ЗАМЕНИ на свои данные от Telegram бота
BOT_TOKEN = "8528750312:AAHpUK46s3Tf7XKTaBRxqO0emcaX9OZyDgw"  # Из CreditBot настроек
CHAT_ID = "6131066491"       # Твой chat_id

# Создаём процессор
sms = SMSProcessor(
    bot_token=BOT_TOKEN,
    bot_chat_id=CHAT_ID
)

# Генерируем QR код
qr_path = sms.generate_qr_code("Мой телефон")
print(f"✅ QR код создан: {qr_path}")

# Открываем картинку
import os
os.startfile(qr_path)  # Откроется автоматически