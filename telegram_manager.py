# -*- coding: utf-8 -*-
"""
🤖 Telegram Manager - глобальный менеджер доступа к Telegram боту
Решает проблему передачи экземпляра бота между модулями
Расположение: C:\\Users\\Самурай\\Desktop\\AutoComment\\bot_control_app\\telegram_manager.py
"""

import threading
import asyncio
import requests  # ← ДОБАВИЛ для синхронной отправки
from typing import Optional

# Глобальные переменные
_telegram_bot_instance = None


def set_telegram_bot(bot_instance):
    """
    Устанавливает глобальный экземпляр Telegram бота
    Вызывается из telegram_bot/tg_bot.py при запуске
    """
    global _telegram_bot_instance
    _telegram_bot_instance = bot_instance
    print("✅ Telegram bot зарегистрирован в TelegramManager")


def get_telegram_bot():
    """Возвращает глобальный экземпляр Telegram бота"""
    return _telegram_bot_instance


async def send_notification_async(message: str):
    """
    Асинхронная отправка уведомлений в Telegram
    Используется в online_statistics.py
    
    Args:
        message: Текст сообщения (поддерживает HTML разметку)
    """
    bot = get_telegram_bot()
    if not bot:
        print("⚠️ Telegram bot недоступен, уведомление не отправлено")
        return
    
    try:
        await bot.send_notification(message)
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления: {e}")


def is_bot_available() -> bool:
    """
    Проверяет доступность Telegram бота
    Возвращает True если бот запущен и готов к работе
    """
    bot = get_telegram_bot()
    return bot is not None and hasattr(bot, 'app') and bot.app is not None


def send_notification_sync(message: str):
    """
    Синхронная отправка уведомлений (для использования вне async функций)
    Использует HTTP API напрямую - работает из любого потока без проблем с asyncio
    
    Args:
        message: Текст сообщения (поддерживает HTML разметку)
    """
    bot = get_telegram_bot()
    if not bot:
        # Молча пропускаем если бот недоступен
        return
    
    try:
        # Получаем токен и chat_id из бота
        if not hasattr(bot, 'bot') or not hasattr(bot, 'user_id'):
            return
        
        # Формируем URL для Telegram API
        token = bot.bot.token
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        
        # Данные для отправки
        data = {
            "chat_id": bot.user_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        # Отправляем через HTTP POST (работает из любого потока!)
        response = requests.post(url, json=data, timeout=10)
        
        # Проверяем ответ
        if response.status_code != 200:
            print(f"⚠️ Telegram API error: {response.status_code} - {response.text}")
            
    except requests.exceptions.Timeout:
        print("⚠️ Timeout при отправке уведомления в Telegram")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Ошибка HTTP запроса к Telegram: {e}")
    except Exception as e:
        print(f"⚠️ Ошибка отправки уведомления: {e}")