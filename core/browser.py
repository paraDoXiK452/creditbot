"""
🌐 Модуль работы с браузером
Selenium, cookies, stealth режим
"""

import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
import undetected_chromedriver as uc

from config import *
# Импорт browser_killer для принудительного закрытия браузеров
try:
    from browser_killer import register_driver, unregister_driver
except ImportError:
    def register_driver(driver): pass
    def unregister_driver(driver): pass



class BrowserManager:
    """Менеджер браузера с поддержкой stealth режима"""
    
    def __init__(self, headless=False, undetected=False):
        """
        Args:
            headless: Запустить в невидимом режиме
            undetected: Использовать undetected_chromedriver
        """
        self.headless = headless
        self.undetected = undetected
        self.driver = None
    
    def start(self):
        """Запуск браузера"""
        if self.undetected:
            return self._start_undetected()
        else:
            return self._start_regular()
    
    def _start_regular(self):
        """Обычный Chrome с stealth"""
        options = Options()
        
        if self.headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'--window-size={BROWSER_WINDOW_SIZE}')
        options.add_argument(f'user-agent={BROWSER_USER_AGENT}')
        
        # Отключаем уведомления
        options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.notifications": 2
        })
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        register_driver(self.driver)  # Регистрируем для принудительного закрытия
        
        # Применяем stealth
        stealth(self.driver,
                languages=["ru-RU", "ru"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True)
        
        return self.driver
    
    def _start_undetected(self):
        """Undetected Chrome для обхода детекта"""
        options = uc.ChromeOptions()
        
        if self.headless:
            options.add_argument('--headless')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        self.driver = uc.Chrome(options=options)
        register_driver(self.driver)  # Регистрируем для принудительного закрытия
        return self.driver
    
    def quit(self):
        """Закрытие браузера"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None


class CookieManager:
    """Менеджер cookies для сохранения сессий"""
    
    @staticmethod
    def save(driver, path=COOKIES_FILE):
        """
        Сохранение cookies в файл
        
        Args:
            driver: WebDriver
            path: Путь к файлу
        """
        try:
            cookies = driver.get_cookies()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2)
            print(f"✅ Cookies сохранены: {path}")
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения cookies: {e}")
            return False
    
    @staticmethod
    def load(driver, url, path=COOKIES_FILE):
        """
        Загрузка cookies перед логином
        
        Args:
            driver: WebDriver
            url: URL для загрузки (нужен для домена)
            path: Путь к файлу cookies
            
        Returns:
            bool: Успешность загрузки
        """
        if not os.path.exists(path):
            print(f"⚠️ Файл cookies не найден: {path}")
            return False
        
        try:
            # Сначала загружаем страницу
            driver.get(url)
            time.sleep(DELAY_SHORT)
            
            # Читаем cookies
            with open(path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            
            driver.delete_all_cookies()
            time.sleep(0.5)
            
            # Добавляем cookies
            for cookie in cookies:
                # Selenium требует убрать некоторые ключи
                cookie.pop("sameSite", None)
                cookie.pop("expiry", None)
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    # Игнорируем ошибки отдельных cookies
                    pass
            
            # Обновляем страницу
            driver.refresh()
            time.sleep(DELAY_SHORT)
            print(f"✅ Cookies загружены: {path}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка загрузки cookies: {e}")
            return False
    
    @staticmethod
    def clear(path=COOKIES_FILE):
        """Удаление файла cookies"""
        try:
            if os.path.exists(path):
                os.remove(path)
                print(f"✅ Cookies удалены: {path}")
                return True
        except Exception as e:
            print(f"❌ Ошибка удаления cookies: {e}")
            return False


def play_error_sound():
    """Воспроизводит системный звук ошибки"""
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONHAND)
    except:
        print('\a')  # Fallback для не-Windows систем
