"""
🔫 Browser Killer - Принудительное закрытие браузеров
Убивает только Chrome процессы запущенные БОТОМ (с меткой BOT_CHROME_DATA)
"""

import psutil
import os
import sys


# Уникальная метка для ботовских браузеров
BOT_MARKER = "BOT_CHROME_DATA"


def kill_all_bot_browsers():
    """Убивает только Chrome процессы запущенные ботом"""
    killed_count = 0
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                process_name = proc.info['name']
                
                # Проверяем что это Chrome/ChromeDriver
                is_chrome = any(name in process_name.lower() for name in 
                              ['chrome', 'chromedriver'])
                
                if not is_chrome:
                    continue
                
                # Проверяем командную строку на наличие метки бота
                cmdline = proc.info.get('cmdline', [])
                if not cmdline:
                    continue
                
                # Ищем метку бота в аргументах
                is_bot_chrome = any(BOT_MARKER in arg for arg in cmdline)
                
                if is_bot_chrome:
                    print(f"🔴 Убиваю БОТОВСКИЙ процесс: {process_name} (PID: {proc.info['pid']})")
                    proc.kill()
                    killed_count += 1
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    
    except Exception as e:
        print(f"❌ Ошибка browser_killer: {e}")
    
    if killed_count > 0:
        print(f"✅ Убито БОТОВСКИХ процессов: {killed_count}")
    else:
        print("ℹ️  Активных ботовских браузеров не найдено")
    
    return killed_count


def register_driver(driver):
    """
    Регистрация драйвера для отслеживания
    В текущей реализации не используется - определяем по метке в cmdline
    """
    pass


def unregister_driver(driver):
    """
    Снятие драйвера с отслеживания
    В текущей реализации не используется
    """
    pass


if __name__ == "__main__":
    # Тест
    print("🔫 Browser Killer - Тест")
    print("=" * 60)
    kill_all_bot_browsers()