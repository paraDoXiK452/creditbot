#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Bot Control App - v2.0 Modern Edition
Точка входа в приложение
"""

import sys
import os
import threading

# Установка кодировки для Windows
if sys.platform == 'win32':
    import locale
    locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QFontDatabase
from PyQt6.QtCore import Qt
# ===== FIX PYTHON PATH (CRITICAL) =====
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# =====================================
from ui.main_window import MainWindow

# Импорты для Telegram бота и StatusManager
try:
    from telegram_bot.tg_bot import TelegramBot
    from status_manager import get_status_manager
    from settings_manager import get_settings_manager
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️ Telegram модули не найдены - бот не будет запущен")


def check_dependencies():
    """Быстрая проверка критических зависимостей"""
    missing = []
    
    try:
        import selenium
    except ImportError:
        missing.append("selenium")
    
    try:
        import easyocr
    except ImportError:
        missing.append("easyocr")
    
    try:
        import openpyxl
    except ImportError:
        missing.append("openpyxl")
    
    if missing:
        print("\n❌ КРИТИЧЕСКИЕ МОДУЛИ НЕ НАЙДЕНЫ:")
        print(f"   {', '.join(missing)}")
        print("\nУстановите их командой:")
        print(f"   pip install {' '.join(missing)}")
        print("\nИли установите все зависимости:")
        print("   pip install -r requirements.txt\n")
        return False
    
    return True


def start_telegram_bot_thread():
    """Запуск Telegram бота в отдельном потоке"""
    if not TELEGRAM_AVAILABLE:
        return
    
    settings = get_settings_manager()
    token = settings.get_telegram_token()
    chat_id = settings.get_telegram_chat_id()
    
    if not token or not chat_id:
        print("⚠️  Telegram настройки не заполнены. Бот не запущен.")
        print("   Заполните токен и chat_id в настройках аккаунта.\n")
        return
    
    print("🤖 Запуск Telegram бота...")
    
    def run_bot():
        """Функция для запуска в потоке"""
        import asyncio
        
        # Создаём новый event loop для этого потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Создаём экземпляр бота
        bot_instance = TelegramBot(token, chat_id)
        
        # ВЫЗЫВАЕМ start_bot() - там вся логика регистрации и настройки!
        try:
            loop.run_until_complete(bot_instance.start_bot())
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"❌ Ошибка TG бота: {e}")
            import traceback
            traceback.print_exc()
        finally:
            loop.close()
    
    # Запускаем в daemon потоке
    tg_thread = threading.Thread(target=run_bot, daemon=True)
    tg_thread.start()
    
    print("✅ Telegram бот запущен в фоне\n")


def start_status_manager():
    """Запуск StatusManager для чтения команд"""
    if not TELEGRAM_AVAILABLE:
        return
    
    sm = get_status_manager()
    sm.start_command_checker(interval=2.0)
    print("✅ StatusManager запущен (чтение команд каждые 2 сек)\n")


def main():
    """Главная функция запуска"""
    
    # Фиксим кодировку для Windows
    if sys.platform == 'win32':
        import locale
        try:
            locale.setlocale(locale.LC_ALL, 'Russian_Russia.1251')
        except:
            pass
    
    print("="*60)
    print("🤖 Bot Control App - v2.0 Modern Edition")
    print("="*60)
    
    # Проверка зависимостей
    if not check_dependencies():
        print("\n⚠️  Приложение не может запуститься без необходимых зависимостей.")
        sys.exit(1)
    
    print("✅ Все зависимости найдены")
    print("🚀 Запуск приложения...\n")
    
    # Запуск Telegram бота (если настроен)
    start_telegram_bot_thread()
    
    # Запуск StatusManager (чтение команд из TG)
    start_status_manager()
    
    # Создание приложения
    app = QApplication(sys.argv)
    app.setApplicationName("Bot Control App")
    app.setOrganizationName("BotControl")
    
    # Настройка стиля
    app.setStyle("Fusion")
    
    # Создание главного окна
    window = MainWindow()
    window.show()
    
    print("✅ Приложение запущено успешно!")
    print("📋 Логи будут отображаться в окне приложения\n")
    
    # Запуск event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()