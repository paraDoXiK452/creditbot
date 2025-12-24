# -*- coding: utf-8 -*-
"""
🔐 Модуль авторизации Max.Credit
ИСПРАВЛЕНА логика: при устаревших cookies - агрессивная очистка или требование перезапуска
"""

import json
import os
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# =============================================================================
# КОНСТАНТЫ
# =============================================================================

XPATH_USERNAME_FIELD = "//*[@id='managerloginform-phone']"
XPATH_PASSWORD_FIELD = "//*[@id='managerloginform-password']"
XPATH_LOGIN_BUTTON = "//*[@id='w0']/div[3]/button"
XPATH_MAIN_TABLE = "//*[@id='w2-container']/table/tbody/tr"
MAIN_PAGE_PART = "collector-debt/work"


# =============================================================================
# РАБОТА С COOKIES
# =============================================================================

def save_cookies(driver, path="cookies.json"):
    """
    Сохранение cookies в файл
    
    Args:
        driver: WebDriver
        path: Путь к файлу cookies
    
    Returns:
        bool: Успешность сохранения
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


def aggressive_browser_cleanup(driver, logger_func):
    """
    АГРЕССИВНАЯ очистка состояния браузера
    Удаляет cookies, localStorage, sessionStorage, cache
    """
    try:
        logger_func("🧹 Выполняю агрессивную очистку браузера...")
        
        # Удаляем все cookies
        driver.delete_all_cookies()
        time.sleep(0.5)
        
        # Очищаем localStorage и sessionStorage через JavaScript
        try:
            driver.execute_script("""
                window.localStorage.clear();
                window.sessionStorage.clear();
            """)
            logger_func("  ✓ localStorage и sessionStorage очищены")
        except Exception as e:
            logger_func(f"  ⚠️ Не удалось очистить storage: {e}")
        
        # Очищаем IndexedDB
        try:
            driver.execute_script("""
                indexedDB.databases().then(dbs => {
                    dbs.forEach(db => indexedDB.deleteDatabase(db.name));
                });
            """)
            logger_func("  ✓ IndexedDB очищен")
        except:
            pass
        
        logger_func("✅ Агрессивная очистка завершена")
        return True
        
    except Exception as e:
        logger_func(f"❌ Ошибка очистки браузера: {e}")
        return False


def load_cookies_fixed(driver, login_url_with_token, path="cookies.json"):
    """
    ИСПРАВЛЕННАЯ загрузка cookies для Max.Credit
    
    ВАЖНО: После этой функции страница уже открыта, НЕ нужно повторно 
    вызывать driver.get()!
    
    Args:
        driver: WebDriver
        login_url_with_token: URL с токеном
        path: Путь к файлу cookies
    
    Returns:
        tuple: (cookies_loaded: bool, is_authorized: bool)
    """
    if not os.path.exists(path):
        print(f"⚠️ Файл cookies не найден: {path}")
        return (False, False)
    
    try:
        # 1. Открываем страницу с токеном
        print(f"📄 Открываю страницу с токеном...")
        driver.get(login_url_with_token)
        time.sleep(2)
        
        # 2. Загружаем cookies из файла
        print(f"📦 Загружаю cookies из {path}...")
        with open(path, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        
        # 3. Удаляем текущие cookies
        driver.delete_all_cookies()
        time.sleep(0.3)
        
        # 4. Добавляем сохраненные cookies
        cookies_added = 0
        for cookie in cookies:
            cookie.pop("sameSite", None)
            cookie.pop("expiry", None)
            try:
                driver.add_cookie(cookie)
                cookies_added += 1
            except:
                pass
        
        print(f"✅ Cookies добавлены: {cookies_added}/{len(cookies)}")
        
        # 5. Обновляем страницу чтобы применить cookies
        print(f"🔄 Обновляю страницу для применения cookies...")
        driver.refresh()
        time.sleep(3)
        
        # 6. Проверяем куда мы попали после refresh
        current_url = driver.current_url
        print(f"📍 Текущий URL: {current_url}")
        
        # 7. Проверяем авторизацию
        is_authorized = check_authorization(driver)
        
        if is_authorized:
            print(f"✅ Авторизация по cookies успешна!")
            return (True, True)
        else:
            print(f"⚠️ Cookies устарели или невалидны")
            
            # КРИТИЧНО: Проверяем - произошел ли redirect на страницу без токена
            if "token=" not in current_url:
                print(f"⚠️ Redirect на {current_url} - cookies мертвые, нужна агрессивная очистка!")
                # Возвращаем специальный статус - нужна очистка и перезапуск
                return (True, False)
            else:
                print(f"✅ Всё ещё на странице с токеном - можно логиниться")
            
            return (True, False)
        
    except Exception as e:
        print(f"❌ Ошибка загрузки cookies: {e}")
        return (False, False)


def check_authorization(driver, timeout=5):
    """
    Проверка авторизации (есть ли таблица заявок)
    
    Args:
        driver: WebDriver
        timeout: Таймаут проверки
    
    Returns:
        bool: True если авторизованы
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, XPATH_MAIN_TABLE))
        )
        if MAIN_PAGE_PART in driver.current_url:
            return True
        return False
    except:
        return False


# =============================================================================
# АВТОРИЗАЦИЯ
# =============================================================================

def normalize_phone_number(phone):
    """
    Нормализует номер телефона для Max.Credit
    
    Max.Credit использует маску "+7 " в поле ввода.
    Нужно отправлять только 10 цифр БЕЗ кода страны.
    
    Args:
        phone: Номер в любом формате
    
    Returns:
        str: 10 цифр без кода страны
    """
    phone_clean = ''.join(filter(str.isdigit, str(phone)))
    
    if phone_clean.startswith('7') and len(phone_clean) == 11:
        phone_clean = phone_clean[1:]
    elif phone_clean.startswith('8') and len(phone_clean) == 11:
        phone_clean = phone_clean[1:]
    
    if len(phone_clean) == 10:
        return phone_clean
    
    return phone_clean


def clear_and_fill_phone_field(field_element, driver, phone_number):
    """
    Правильная очистка и заполнение поля телефона с маской "+7 "
    """
    normalized_phone = normalize_phone_number(phone_number)
    
    # Метод 1: Очистка через JavaScript (самый надежный)
    try:
        driver.execute_script("arguments[0].value = '';", field_element)
        time.sleep(0.2)
        field_element.send_keys(normalized_phone)
        return
    except:
        pass
    
    # Метод 2: Множественное нажатие Backspace
    try:
        field_element.click()
        time.sleep(0.1)
        for _ in range(20):
            field_element.send_keys(Keys.BACKSPACE)
        time.sleep(0.1)
        field_element.send_keys(normalized_phone)
        return
    except:
        pass
    
    # Fallback
    field_element.clear()
    field_element.send_keys(normalized_phone)


def login_maxcredit(driver, wait, login_url_with_token, username, password, logger_func=print):
    """
    ИСПРАВЛЕННАЯ функция логина для Max.Credit
    """
    try:
        logger_func(f"🔐 Начинаю авторизацию на {login_url_with_token}")
        
        # Проверяем - уже на нужной странице?
        current_url = driver.current_url
        if current_url != login_url_with_token:
            logger_func(f"📄 Открываю страницу логина...")
            driver.get(login_url_with_token)
            time.sleep(2)
        else:
            logger_func(f"✅ Уже на странице логина")
        
        # Ждем поле логина
        logger_func("⏳ Ожидание поля телефона...")
        username_field = wait.until(
            EC.visibility_of_element_located((By.XPATH, XPATH_USERNAME_FIELD))
        )
        
        # Вводим телефон
        logger_func(f"📞 Ввод телефона: {username}")
        clear_and_fill_phone_field(username_field, driver, username)
        time.sleep(0.3)
        
        # Ждем поле пароля
        logger_func("⏳ Ожидание поля пароля...")
        password_field = wait.until(
            EC.visibility_of_element_located((By.XPATH, XPATH_PASSWORD_FIELD))
        )
        
        # Вводим пароль
        logger_func("🔑 Ввод пароля...")
        password_field.clear()
        password_field.send_keys(password)
        time.sleep(0.3)
        
        # Нажимаем кнопку входа
        logger_func("⏳ Ожидание кнопки 'Войти'...")
        login_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, XPATH_LOGIN_BUTTON))
        )
        logger_func("👆 Нажатие кнопки 'Войти'...")
        login_button.click()
        
        # Ждем загрузки основной страницы
        logger_func(f"⏳ Ожидание загрузки основной страницы...")
        WebDriverWait(driver, 30).until(EC.url_contains(MAIN_PAGE_PART))
        wait.until(EC.presence_of_element_located((By.XPATH, XPATH_MAIN_TABLE)))
        
        logger_func(f"✅ Вход выполнен успешно! URL: {driver.current_url}")
        
        # Сохраняем cookies
        save_cookies(driver)
        logger_func("💾 Cookies обновлены после логина")
        
        return True
        
    except Exception as e:
        logger_func(f"❌ ОШИБКА при попытке входа: {e}")
        
        # Делаем скриншот ошибки
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"login_error_{timestamp}.png"
        try:
            driver.save_screenshot(screenshot_path)
            logger_func(f"📸 Скриншот ошибки сохранен: {screenshot_path}")
        except:
            pass
        
        return False


# =============================================================================
# ОСНОВНАЯ ФУНКЦИЯ АВТОРИЗАЦИИ
# =============================================================================

def authorize_maxcredit(driver, wait, login_url_with_token, username, password, logger_func=print):
    """
    Умная авторизация: пробует cookies, при устарении - агрессивная очистка и логин
    
    Args:
        driver: WebDriver
        wait: WebDriverWait
        login_url_with_token: URL с токеном
        username: Телефон
        password: Пароль
        logger_func: Функция логирования
    
    Returns:
        bool: True если авторизация успешна
    """
    logger_func("=" * 60)
    logger_func("🚀 Начинаю процесс авторизации Max.Credit")
    logger_func("=" * 60)
    
    # 1. Пробуем загрузить cookies
    cookies_loaded, is_authorized = load_cookies_fixed(
        driver, 
        login_url_with_token
    )
    
    if is_authorized:
        logger_func("✅ Авторизация по cookies успешна! Логин не требуется.")
        logger_func("=" * 60)
        return True
    
    # 2. Cookies не помогли
    if cookies_loaded:
        logger_func("⚠️ Cookies устарели - требуется повторный вход")
        
        # КРИТИЧНО: Выполняем агрессивную очистку браузера
        # Max.Credit не дает войти заново без полной очистки состояния
        logger_func("🧹 Выполняю агрессивную очистку состояния браузера...")
        aggressive_browser_cleanup(driver, logger_func)
        
        # Открываем страницу с токеном заново (после очистки)
        logger_func(f"📄 Открываю страницу с токеном заново после очистки...")
        driver.get(login_url_with_token)
        time.sleep(2)
        
        logger_func("📝 Выполняю вход с логином и паролем...")
    else:
        logger_func("📝 Cookies не найдены - выполняю обычный логин...")
    
    # 3. Выполняем логин
    success = login_maxcredit(
        driver,
        wait,
        login_url_with_token,
        username,
        password,
        logger_func
    )
    
    logger_func("=" * 60)
    if success:
        logger_func("✅ Авторизация завершена успешно!")
    else:
        logger_func("❌ Авторизация не удалась!")
    logger_func("=" * 60)
    
    return success