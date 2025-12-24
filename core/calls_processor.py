# -*- coding: utf-8 -*-
"""
📞 Процессор звонков
Автоматическая обработка списка звонков с отправкой комментариев
"""

import time
import random
import traceback
import json
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
import pytz

# Zoiper автоматизация и StatusManager
from zoiper_automation import ZoiperAutomation
from status_manager import get_status_manager

# Telegram уведомления
try:
    from telegram_manager import send_notification_sync, is_bot_available
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    def send_notification_sync(msg): pass
    def is_bot_available(): return False

# ИСПРАВЛЕННЫЙ МОДУЛЬ АВТОРИЗАЦИИ
from core.auth_maxcredit import authorize_maxcredit


# =============================================================================
# КОНСТАНТЫ - XPATH'ы
# =============================================================================

XPATH_USERNAME_FIELD_BOT = "//*[@id='managerloginform-phone']"
XPATH_PASSWORD_FIELD_BOT = "//*[@id='managerloginform-password']"
XPATH_LOGIN_BUTTON_BOT = "//*[@id='w0']/div[3]/button"
XPATH_ALL_ROWS_TABLE_BOT = "//*[@id='w2-container']/table/tbody/tr"
MAIN_PAGE_PART_BOT = "collector-debt/work"

XPATH_DATE_UNTIL_INPUT_FIELD = "//*[@id='collectordebtsearch-wcallatto']"
XPATH_FZ230_ELEMENT = "//*[@id='collectordebtsearch-fz230']"
XPATH_FILTER_SEARCH_BUTTON = "//*[@id='w1']/div[4]/div[1]/button[1]"
XPATH_CALL_LIST_BUTTON = "//*[@id='w1']/div[4]/div[2]/a"

XPATH_MODAL_CONTENT_FOR_WAIT = "//div[@class='modal-content']"
XPATH_MODAL_TAB_COMMENTS = "//div[contains(@class,'modal-body')]//ul[contains(@class,'nav-tabs')]//a[text()='Комментарии']"
XPATH_MODAL_COMMENT_TEXT_FIELD = "//*[@id='collectorcommentform-message']"
XPATH_MODAL_SUBMIT_BUTTON = "//*[@id='js-collector-comment-form-submit']"
XPATH_MODAL_CONTINUE_BUTTON = "//a[contains(@class,'btn') and normalize-space(text())='Продолжить']"

# XPATH для закрытия окна ошибки при слетевшем звонке
XPATH_ERROR_CLOSE_BUTTON = "/html/body/div[5]/div[1]/div/div[2]/div[2]/button"

# XPATH для работы с часовыми поясами
XPATH_TIMEZONE_SELECT = "/html/body/div[1]/div/div[2]/form/div[1]/div[4]/div/select"
XPATH_EMPTY_LIST_MESSAGE = "/html/body/div[5]/div[1]/div/div[2]/div[1]"

# XPATH для отслеживания клиентов в повторном режиме
XPATH_CLIENT_NAME = "/html/body/div[5]/div[1]/div/div[2]/div[1]/div[1]/table/tbody/tr[5]/td/a"
XPATH_CLOSE_MODAL_BUTTON = "/html/body/div[5]/div[1]/div/div[1]/button"
XPATH_CLIENT_COUNT = "/html/body/div[1]/div/div[2]/div[2]/div/div[2]/b[2]"  # b[2] = общее количество клиентов, b[1] = текущая страница

# XPATH для вкладки Звонки и неконтактного статуса
XPATH_MODAL_TAB_CALLS = "/html/body/div[5]/div[1]/div/div[2]/ul/li[4]/a"
XPATH_NON_CONTACT_CHECKBOX = "/html/body/div[5]/div[1]/div/div[2]/div[1]/div[4]/form/div[2]/div/label/input[2]"
XPATH_CALLS_SAVE_BUTTON = "/html/body/div[5]/div[1]/div/div[2]/div[1]/div[4]/form/button"


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def get_available_timezones(logger_func):
    """
    Расчет доступных часовых поясов для обзвона по ФЗ-230
    
    Правила:
    - Будни: 8:00 - 22:00
    - Выходные: 9:00 - 20:00
    
    Returns:
        list: Список доступных поясов в формате "МСК+3", "МСК-2" и т.д.
              Отсортированы от большего к меньшему (МСК+6, МСК+5, ..., МСК-7)
    """
    # Получаем текущее время по Москве
    moscow_tz = pytz.timezone('Europe/Moscow')
    moscow_time = datetime.now(moscow_tz)
    current_hour = moscow_time.hour
    is_weekend = moscow_time.weekday() >= 5  # 5=суббота, 6=воскресенье
    
    # Определяем разрешенные часы
    if is_weekend:
        start_hour = 9
        end_hour = 20
        day_type = "выходной"
    else:
        start_hour = 8
        end_hour = 22
        day_type = "будний"
    
    logger_func(f"🕐 Текущее время по МСК: {moscow_time.strftime('%H:%M')}")
    logger_func(f"📅 День: {day_type}, разрешенные часы: {start_hour}:00 - {end_hour}:00")
    
    available = []
    
    # Проверяем часовые пояса от МСК+9 до МСК-1
    for offset in range(9, -2, -1):
        # Время в этом часовом поясе
        tz_hour = current_hour + offset
        
        # Нормализуем часы (24-часовой формат)
        if tz_hour >= 24:
            tz_hour -= 24
        elif tz_hour < 0:
            tz_hour += 24
        
        # Проверяем попадает ли в разрешенные часы
        if start_hour <= tz_hour < end_hour:
            # Формат: МСК+0, МСК+3, МСК-2
            tz_name = f"МСК{offset:+d}"  # :+d добавляет знак + или -
            
            available.append(tz_name)
            logger_func(f"  ✅ {tz_name}: {tz_hour:02d}:00 (разрешено)")
        else:
            tz_name = f"МСК{offset:+d}"
            logger_func(f"  ❌ {tz_name}: {tz_hour:02d}:00 (запрещено)")
    
    if not available:
        logger_func("⚠️ Нет доступных часовых поясов для обзвона!")
    else:
        logger_func(f"📞 Доступно поясов для обзвона: {len(available)}")
    
    return available


def set_timezone(driver, wait, timezone_name, logger_func):
    """
    Установка часового пояса на сайте
    
    Args:
        driver: WebDriver
        wait: WebDriverWait
        timezone_name: Название часового пояса (например, "МСК+3")
        logger_func: Функция логирования
        
    Returns:
        bool: True если успешно установлен
    """
    try:
        logger_func(f"🌍 Установка часового пояса: {timezone_name}")
        
        # Находим select элемент
        tz_select_element = wait.until(
            EC.presence_of_element_located((By.XPATH, XPATH_TIMEZONE_SELECT))
        )
        
        # Создаём Select объект
        tz_select = Select(tz_select_element)
        
        # Выбираем по видимому тексту
        tz_select.select_by_visible_text(timezone_name)
        
        time.sleep(0.5)
        logger_func(f"  ✅ Часовой пояс установлен: {timezone_name}")
        return True
        
    except Exception as e:
        logger_func(f"  ❌ Ошибка установки часового пояса: {e}")
        logger_func(traceback.format_exc())
        return False


def is_empty_list_message(driver, logger_func):
    """
    Проверка, является ли окно сообщением о пустом списке клиентов
    
    Returns:
        bool: True если это сообщение "Список заявок пуст", False если это ошибка звонка
    """
    try:
        message_element = driver.find_element(By.XPATH, XPATH_EMPTY_LIST_MESSAGE)
        message_text = message_element.text
        
        if "Список заявок пуст" in message_text:
            logger_func(f"✅ Обнаружено окно 'Список заявок пуст' - пояс завершен")
            return True
        else:
            logger_func(f"⚠️ Обнаружено другое окно: {message_text[:100]}")
            return False
            
    except Exception as e:
        logger_func(f"⚠️ Не удалось прочитать текст окна: {e}")
        return False


def get_client_name(driver, logger_func):
    """
    Получение ФИО клиента из модального окна
    
    Returns:
        str: ФИО клиента или None если не удалось получить
    """
    try:
        name_element = driver.find_element(By.XPATH, XPATH_CLIENT_NAME)
        client_name = name_element.text.strip()
        return client_name
    except Exception as e:
        logger_func(f"⚠️ Не удалось получить ФИО клиента: {e}")
        return None


def switch_to_next_timezone_repeat_mode(driver, wait, zoiper, logger_func):
    """
    Подготовка к переключению на следующий часовой пояс в повторном режиме
    
    1. Закрыть окно клиента
    2. Завершить звонок в Zoiper
    3. Начать новый звонок *88 + мут
    
    Установка часового пояса и "Звонить по списку" произойдут в следующей итерации цикла по поясам
    
    Returns:
        bool: True если успешно подготовились к переключению
    """
    try:
        logger_func(f"🔄 Подготовка к переключению на новый часовой пояс...")
        
        # 1. Закрыть окно клиента
        logger_func("📴 Закрытие окна клиента...")
        close_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, XPATH_CLOSE_MODAL_BUTTON))
        )
        close_btn.click()
        time.sleep(1)
        
        # 2. Завершить текущий звонок в Zoiper и начать новый
        logger_func("📞 Перезапуск звонка в Zoiper...")
        
        # Разворачиваем и закрепляем окно на время операций
        zoiper.activate_window()  # Разворачиваем окно
        zoiper.pin_window_topmost()
        
        try:
            # Завершаем текущий звонок (нажатие кнопки, НЕ закрытие Zoiper)
            if not zoiper.end_call():
                logger_func("⚠️ Не удалось завершить звонок, продолжаем...")
            time.sleep(1)
            
            # Начинаем новый звонок на *88
            if not zoiper.dial_number("*88"):
                logger_func("❌ Не удалось набрать *88")
                return False
            
            time.sleep(2)
            zoiper.mute_call()
            logger_func("✅ Новый звонок *88 установлен")
            
        finally:
            # Открепляем окно после операций
            zoiper.unpin_window_topmost()
        
        logger_func("✅ Готов к переключению на следующий пояс")
        return True
        
    except Exception as e:
        logger_func(f"❌ Ошибка подготовки к переключению: {e}")
        logger_func(traceback.format_exc())
        return False


def _check_and_handle_error(driver, wait, zoiper, logger_func):
    """
    Универсальная проверка окна ошибки и обработка
    
    Returns:
        bool: True если окно ошибки было найдено и обработано
    """
    try:
        error_btn = driver.find_element(By.XPATH, XPATH_ERROR_CLOSE_BUTTON)
        if error_btn.is_displayed():
            logger_func("⚠️ Обнаружено окно ошибки!")
            return _handle_call_error(driver, wait, zoiper, logger_func)
    except:
        # Окна ошибки нет
        pass
    return False


def _safe_continue(driver, logger_func):
    """Пытается нажать кнопку 'Продолжить' при ошибках, чтобы перейти к следующему клиенту."""
    try:
        btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, XPATH_MODAL_CONTINUE_BUTTON))
        )
        btn.click()
        time.sleep(2)
        logger_func("Переход к следующему клиенту после ошибки.")
    except:
        logger_func("Не удалось нажать 'Продолжить' после ошибки — завершаем обработку.")


def _handle_call_error(driver, wait, zoiper, logger_func):
    """
    Обработка ошибки при слетевшем звонке
    
    1. Закрывает окно ошибки на сайте
    2. Разворачивает Zoiper и проверяет/восстанавливает звонок
    3. Нажимает "Звонить по списку" снова
    
    Returns:
        bool: True если ошибка обработана успешно
    """
    try:
        logger_func("⚠️ Обнаружена ошибка звонка, обрабатываем...")
        
        # 1. Закрываем окно ошибки
        try:
            error_close_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, XPATH_ERROR_CLOSE_BUTTON))
            )
            error_close_btn.click()
            logger_func("✅ Окно ошибки закрыто")
            time.sleep(1)
        except:
            logger_func("⚠️ Окно ошибки не найдено или уже закрыто")
        
        # 2. Разворачиваем Zoiper и проверяем/восстанавливаем звонок
        logger_func("🔄 Проверка Zoiper...")
        if not zoiper.restore_call():
            logger_func("❌ Не удалось восстановить звонок")
            return False
        
        # 3. Возвращаемся на сайт и нажимаем "Звонить по списку"
        logger_func("🔄 Нажатие 'Звонить по списку' после восстановления...")
        call_list_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, XPATH_CALL_LIST_BUTTON))
        )
        call_list_button.click()
        time.sleep(2)
        
        logger_func("✅ Ошибка обработана, продолжаем работу")
        return True
        
    except Exception as e:
        logger_func(f"❌ Ошибка при обработке слетевшего звонка: {e}")
        return False


# =============================================================================
# ОСНОВНАЯ ФУНКЦИЯ ОБРАБОТКИ ЗВОНКОВ
# =============================================================================

def process_call_list(login_url, username, password, call_comments, logger_func, stop_flag=None, progress_callback=None, repeat_mode=False,
                      use_call_duration=False, duration_min=10, duration_max=15, use_timezones=False):
    """
    Функция для обработки списка звонков на сайте.
    
    Args:
        login_url: URL страницы входа
        username: Логин (телефон)
        password: Пароль
        call_comments: Список комментариев для звонков
        logger_func: Функция для логирования
        stop_flag: Флаг остановки (threading.Event)
        progress_callback: Колбек для обновления прогресса (count)
        repeat_mode: Если True, не устанавливает дату "До" в фильтрах (для повторного обзвона)
        use_call_duration: Если True, делать паузу перед отправкой комментария
        duration_min: Минимальная длительность звонка в секундах
        duration_max: Максимальная длительность звонка в секундах
        use_timezones: Если True, учитывать часовые пояса (только для обычного режима)
    """
    logger_func("Запуск процесса обработки списка звонков...")
    
    # Логирование настроек длительности
    if use_call_duration:
        logger_func(f"⏱️ Настраиваемая длительность звонка: {duration_min}-{duration_max} секунд")
    
    # Инициализация StatusManager
    sm = get_status_manager()
    sm.update_mode_status("calls", running=True, processed=0, last_error="")
    sm.add_log("Режим звонков запущен")
    
    # ===================== ЗАПУСК ZOIPER =====================
    logger_func("🚀 Запуск Zoiper для звонков...")
    zoiper = ZoiperAutomation()
    
    if not zoiper.start_zoiper():
        error_msg = "❌ Не удалось запустить Zoiper"
        logger_func(error_msg)
        sm.update_mode_status("calls", last_error=error_msg)
        sm.add_log(error_msg)
        
        # 📱 Критическое уведомление
        if TELEGRAM_AVAILABLE and is_bot_available():
            send_notification_sync(
                f"🚨 <b>ЗВОНКИ УПАЛИ</b>\n\n"
                f"❌ Не удалось запустить Zoiper\n\n"
                f"Проверьте установку Zoiper"
            )
        return
    
    # Звоним на *88 (без завершения звонка)
    logger_func("📞 Звоним на *88...")
    
    # Окно уже закреплено после start_zoiper()
    
    try:
        if not zoiper.dial_number("*88"):
            error_msg = "❌ Не удалось набрать *88"
            logger_func(error_msg)
            zoiper.hangup()  # Закрываем Zoiper
            sm.update_mode_status("calls", last_error=error_msg)
            sm.add_log(error_msg)
            
            # 📱 Критическое уведомление
            if TELEGRAM_AVAILABLE and is_bot_available():
                send_notification_sync(
                    f"🚨 <b>ЗВОНКИ УПАЛИ</b>\n\n"
                    f"❌ Не удалось набрать *88 в Zoiper\n\n"
                    f"Проверьте настройки Zoiper"
                )
            return
        
        # Включаем мут через 2 секунды
        time.sleep(2)
        zoiper.mute_call()
        logger_func("✅ Zoiper готов (*88 на муте)")
        sm.add_log("Zoiper запущен, линия *88 открыта")
        
    finally:
        # Открепляем окно после завершения операций с *88
        zoiper.unpin_window_topmost()
    # =========================================================
    
    # Подготовка комментариев
    if isinstance(call_comments, str):
        # Разбиваем текст комментариев по строкам
        if "\r\n" in call_comments:
            call_comments_list = call_comments.split("\r\n")
        elif "\n" in call_comments:
            call_comments_list = call_comments.split("\n")
        elif "\r" in call_comments:
            call_comments_list = call_comments.split("\r")
        else:
            call_comments_list = [call_comments]
        
        call_comments_list = [line.strip() for line in call_comments_list if line.strip()]
    else:
        call_comments_list = [str(c).strip() for c in call_comments if str(c).strip()]
    
    if not call_comments_list:
        call_comments_list = ["мт но"]
    
    logger_func(f"Подготовлено комментариев для звонков: {len(call_comments_list)}")
    logger_func(f"Список комментариев: {call_comments_list}")

    random.seed()

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        driver.maximize_window()
        wait = WebDriverWait(driver, 20)

        # =====================================================
        # ИСПРАВЛЕННАЯ АВТОРИЗАЦИЯ - ОДНА СТРОКА!
        # =====================================================
        if not authorize_maxcredit(driver, wait, login_url,
                                   username, password, logger_func):
            logger_func("❌ Авторизация не удалась!")
            zoiper.hangup()
            
            # 📱 Критическое уведомление
            if TELEGRAM_AVAILABLE and is_bot_available():
                send_notification_sync(
                    f"🚨 <b>ЗВОНКИ УПАЛИ</b>\n\n"
                    f"❌ Не удалось авторизоваться на сайте\n\n"
                    f"Проверьте логин и пароль"
                )
            return
        
        logger_func("✅ Авторизация успешна! Готов к работе.")
        
        # 📱 Уведомление о запуске
        if TELEGRAM_AVAILABLE and is_bot_available():
            mode_text = "Повторный обзвон" if repeat_mode else "Обзвон"
            tz_text = " с часовыми поясами" if use_timezones and not repeat_mode else ""
            send_notification_sync(
                f"📞 <b>ЗВОНКИ ЗАПУЩЕНЫ</b>\n\n"
                f"🔹 Режим: {mode_text}{tz_text}\n"
                f"💬 Комментариев: {len(call_comments_list)}\n"
                f"⏱️ Длительность: {'Вкл (' + str(duration_min) + '-' + str(duration_max) + ' сек)' if use_call_duration else 'Выкл'}"
            )
        
        # Проверка остановки
        if stop_flag and stop_flag.is_set():
            logger_func("Получена команда остановки после авторизации.")
            
            # 📱 Уведомление об остановке
            if TELEGRAM_AVAILABLE and is_bot_available():
                send_notification_sync(
                    f"⏹️ <b>ЗВОНКИ ОСТАНОВЛЕНЫ</b>\n\n"
                    f"Остановлено вручную пользователем"
                )
            return
        # =====================================================

        # ===================== РАБОТА С ЧАСОВЫМИ ПОЯСАМИ =====================
        # Определяем список часовых поясов для обработки
        timezones_to_process = []
        
        if use_timezones:
            # Часовые пояса работают для обоих режимов
            mode_text = "ПОВТОРНЫЙ РЕЖИМ" if repeat_mode else "ОБЫЧНЫЙ РЕЖИМ"
            logger_func(f"\n🌍 РЕЖИМ С УЧЕТОМ ЧАСОВЫХ ПОЯСОВ ({mode_text})")
            logger_func("=" * 60)
            timezones_to_process = get_available_timezones(logger_func)
            
            if not timezones_to_process:
                logger_func("⚠️ Нет доступных часовых поясов для обзвона!")
                logger_func("Завершение работы.")
                return
            
            logger_func(f"\n📋 Будет обработано поясов: {len(timezones_to_process)}")
            logger_func(f"Порядок обработки: {' → '.join(timezones_to_process)}")
            
            if repeat_mode:
                logger_func("🔄 Повторный режим: при завершении круга клиентов → переход к следующему поясу")
            
            logger_func("=" * 60 + "\n")
        else:
            # Обычный режим без учета поясов - обрабатываем как один "пояс"
            timezones_to_process = [None]
        
        # Общий счетчик обработанных клиентов
        total_processed = 0
        
        # ===================== ЦИКЛ ПО ЧАСОВЫМ ПОЯСАМ =====================
        for tz_index, current_timezone in enumerate(timezones_to_process, 1):
            if stop_flag and stop_flag.is_set():
                logger_func("Получена команда остановки.")
                break
            
            if current_timezone:
                logger_func(f"\n{'='*60}")
                logger_func(f"🌍 ОБРАБОТКА ЧАСОВОГО ПОЯСА {tz_index}/{len(timezones_to_process)}: {current_timezone}")
                logger_func(f"{'='*60}\n")
            
            processed_clients_count = 0

            # ===================== УСТАНОВКА ФИЛЬТРОВ =====================
            logger_func("Установка фильтров...")
            
            # Установка часового пояса (если режим с поясами включен)
            if current_timezone:
                if not set_timezone(driver, wait, current_timezone, logger_func):
                    logger_func(f"❌ Не удалось установить часовой пояс {current_timezone}, пропускаем")
                    continue

            # Установка даты ДО (только для обычного режима, не для повторного)
            if not repeat_mode:
                try:
                    yesterday = datetime.now() - timedelta(days=1)
                    yesterday_str = yesterday.strftime("%d.%m.%Y")
                    logger_func(f"Попытка установить 'Дата звонка ДО': {yesterday_str}")
    
                    date_until_field = wait.until(
                        EC.visibility_of_element_located((By.XPATH, XPATH_DATE_UNTIL_INPUT_FIELD))
                    )
                    driver.execute_script("arguments[0].value = '';", date_until_field)
                    time.sleep(0.3)
                    date_until_field.send_keys(yesterday_str)
                    logger_func(f"    Значение в поле: {date_until_field.get_attribute('value')}")
                    driver.find_element(By.TAG_NAME, "body").click()
                    time.sleep(0.5)
    
                except Exception as e_date:
                    logger_func(f"Ошибка установки даты: {e_date}")
                    logger_func(traceback.format_exc())
    
                if stop_flag and stop_flag.is_set():
                    logger_func("Остановка после фильтра даты.")
                    return
            else:
                logger_func("ПОВТОРНЫЙ РЕЖИМ - фильтр по дате НЕ устанавливается")
    
            # Выбор ФЗ-230
            try:
                logger_func("Выбор ФЗ-230...")
                fz230 = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_FZ230_ELEMENT)))
                if not fz230.is_selected():
                    fz230.click()
                    logger_func("    'ФЗ-230' выбран.")
                else:
                    logger_func("    'ФЗ-230' уже выбран.")
                time.sleep(0.5)
    
            except Exception as e_fz:
                logger_func(f"Ошибка выбора ФЗ-230: {e_fz}")
                logger_func(traceback.format_exc())
    
            if stop_flag and stop_flag.is_set():
                logger_func("Остановка после выбора ФЗ-230.")
                return
    
            # Нажатие кнопки Поиск
            try:
                logger_func("Нажатие кнопки 'Поиск'...")
                wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_FILTER_SEARCH_BUTTON))).click()
                logger_func("Фильтры применены, ожидание 5 секунд...")
                time.sleep(5)
            except Exception as e_search:
                logger_func(f"Ошибка нажатия Поиск: {e_search}")
                logger_func(traceback.format_exc())
                return
    
            if stop_flag and stop_flag.is_set():
                logger_func("Остановка после применения фильтров.")
                return
    
            # ===================== ЧТЕНИЕ КОЛИЧЕСТВА КЛИЕНТОВ (ПОВТОРНЫЙ РЕЖИМ) =====================
            max_clients_in_timezone = None
            if repeat_mode and use_timezones and current_timezone:
                try:
                    count_element = driver.find_element(By.XPATH, XPATH_CLIENT_COUNT)
                    count_text = count_element.text.strip()
                    
                    # Парсим формат "1-6" (диапазон) или просто "6" (число)
                    if '-' in count_text:
                        # Формат "1-6" → берем второе число (6)
                        max_clients_in_timezone = int(count_text.split('-')[1])
                    else:
                        # Формат "6" → просто число
                        max_clients_in_timezone = int(count_text)
                    
                    logger_func(f"📊 В поясе {current_timezone}: {max_clients_in_timezone} клиентов")
                except Exception as e_count:
                    logger_func(f"⚠️ Не удалось прочитать количество клиентов: {e_count}")
                    # Продолжаем без счетчика
                    max_clients_in_timezone = None
    
            # ===================== КНОПКА ЗВОНИТЬ ПО СПИСКУ =====================
            try:
                logger_func("Ожидание кнопки 'Звонить по списку'...")
                call_list_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, XPATH_CALL_LIST_BUTTON))
                )
                logger_func("Кнопка найдена, кликаем...")
                call_list_button.click()
                time.sleep(2)
                
                # Проверяем не появилось ли окно после запуска звонков
                try:
                    error_btn = driver.find_element(By.XPATH, XPATH_ERROR_CLOSE_BUTTON)
                    if error_btn.is_displayed():
                        # Есть окно - проверяем что это
                        if is_empty_list_message(driver, logger_func):
                            # Список пуст для этого часового пояса - это нормально
                            error_btn.click()
                            time.sleep(1)
                            # Пропускаем цикл обработки клиентов для этого пояса
                            logger_func(f"✅ Часовой пояс {current_timezone if current_timezone else 'обзвон'} пропущен (нет клиентов)")
                            continue  # Переходим к следующему часовому поясу
                        else:
                            # Это реальная ошибка звонка
                            logger_func("⚠️ Обнаружено окно ошибки при запуске звонков!")
                            if not _handle_call_error(driver, wait, zoiper, logger_func):
                                logger_func("❌ Не удалось обработать ошибку звонка")
                                return
                except:
                    # Окна нет - это нормально
                    pass
                    
            except Exception as e_btn:
                logger_func(f"Ошибка кнопки 'Звонить по списку': {e_btn}")
                logger_func(traceback.format_exc())
                return
    
            # ===================== ОСНОВНОЙ ЦИКЛ ОБРАБОТКИ =====================
            while True:
                if stop_flag and stop_flag.is_set():
                    logger_func("Остановка обработки клиентов.")
                    break
                
                # ====== ПРОВЕРКА СЧЕТЧИКА В ПОВТОРНОМ РЕЖИМЕ ======
                if repeat_mode and use_timezones and current_timezone and max_clients_in_timezone:
                    if processed_clients_count >= max_clients_in_timezone:
                        logger_func(f"✅ Обработаны все клиенты в поясе {current_timezone} ({max_clients_in_timezone})")
                        
                        # Переключаемся на следующий часовой пояс
                        if not switch_to_next_timezone_repeat_mode(driver, wait, zoiper, logger_func):
                            logger_func("❌ Не удалось подготовиться к переключению часового пояса")
                            break
                        
                        # Выходим из цикла обработки текущего пояса
                        break
                # ==================================================
    
                logger_func(f"\n--- Клиент #{processed_clients_count + 1} ---")
    
                # Появление модального окна
                try:
                    WebDriverWait(driver, 15).until(
                        EC.visibility_of_element_located((By.XPATH, XPATH_MODAL_CONTENT_FOR_WAIT))
                    )
                    time.sleep(1)
                    
                except Exception as e_modal:
                    # Проверяем не появилось ли окно вместо модального окна с клиентом
                    try:
                        error_btn = driver.find_element(By.XPATH, XPATH_ERROR_CLOSE_BUTTON)
                        if error_btn.is_displayed():
                            # Есть окно с кнопкой закрытия - проверяем что это
                            if is_empty_list_message(driver, logger_func):
                                # Это окно "Список заявок пуст" - часовой пояс закончен
                                if current_timezone:
                                    logger_func(f"✅ Часовой пояс {current_timezone} завершен")
                                else:
                                    logger_func("✅ Список клиентов завершен")
                                
                                # Закрываем окно
                                error_btn.click()
                                time.sleep(1)
                                break  # Выходим из цикла обработки клиентов
                            else:
                                # Это окно ошибки звонка
                                logger_func("⚠️ Обнаружено окно ошибки вместо клиента!")
                                if _handle_call_error(driver, wait, zoiper, logger_func):
                                    # Ошибка обработана, продолжаем с начала цикла
                                    continue
                                else:
                                    logger_func("❌ Не удалось обработать ошибку")
                                    break
                    except:
                        # Окна с кнопкой закрытия нет - просто список закончился
                        logger_func("Модальное окно не появилось — возможно список закончился.")
                        logger_func(traceback.format_exc())
                        break
    
                if stop_flag and stop_flag.is_set():
                    break
    
                # ========== РАБОТА С ВКЛАДКОЙ ЗВОНКИ ==========
                try:
                    logger_func("📞 Переход на вкладку 'Звонки'...")
                    calls_tab = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, XPATH_MODAL_TAB_CALLS))
                    )
                    calls_tab.click()
                    time.sleep(0.5)
                    logger_func("  ✅ Вкладка 'Звонки' открыта")
                    
                    # Включаем неконтактный статус
                    logger_func("📵 Включение неконтактного статуса...")
                    non_contact_checkbox = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, XPATH_NON_CONTACT_CHECKBOX))
                    )
                    # Проверяем, не включен ли уже
                    if not non_contact_checkbox.is_selected():
                        non_contact_checkbox.click()
                        time.sleep(0.3)
                        logger_func("  ✅ Неконтактный статус включен")
                    else:
                        logger_func("  ℹ️ Неконтактный статус уже был включен")
                    
                    # Сохраняем настройки
                    logger_func("💾 Сохранение настроек...")
                    save_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, XPATH_CALLS_SAVE_BUTTON))
                    )
                    save_button.click()
                    time.sleep(1)
                    logger_func("  ✅ Настройки сохранены")
                    
                except Exception as e_calls:
                    logger_func(f"⚠️ Ошибка при работе с вкладкой 'Звонки': {e_calls}")
                    logger_func(traceback.format_exc())
                    # Продолжаем работу, даже если что-то пошло не так
                # ==============================================
    
                # Переключение на вкладку Комментарии
                try:
                    logger_func("💬 Переключение на вкладку 'Комментарии'...")
                    comments_tab = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, XPATH_MODAL_TAB_COMMENTS))
                    )
                    li = comments_tab.find_element(By.XPATH, "./..")
                    if "active" not in li.get_attribute("class"):
                        comments_tab.click()
                        time.sleep(0.5)
                except Exception as e_tab:
                    logger_func(f"Ошибка вкладки 'Комментарии': {e_tab}")
                    logger_func(traceback.format_exc())
                    
                    # Проверяем сначала не закончился ли список клиентов
                    try:
                        error_btn = driver.find_element(By.XPATH, XPATH_ERROR_CLOSE_BUTTON)
                        if error_btn.is_displayed() and is_empty_list_message(driver, logger_func):
                            # Список клиентов закончился для этого часового пояса
                            error_btn.click()
                            time.sleep(1)
                            break  # Выходим из цикла обработки клиентов
                    except:
                        pass
                    
                    # Проверяем не окно ли ошибки вызвало проблему
                    if _check_and_handle_error(driver, wait, zoiper, logger_func):
                        # Ошибка обработана, продолжаем цикл заново
                        continue
                    
                    _safe_continue(driver, logger_func)
                    continue
    
                # Поле для комментария
                try:
                    comment_field = WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.XPATH, XPATH_MODAL_COMMENT_TEXT_FIELD))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", comment_field)
                    time.sleep(0.5)
    
                    # Выбираем случайный комментарий
                    idx = random.randint(0, len(call_comments_list) - 1)
                    selected_comment = call_comments_list[idx]
                    logger_func(f"Выбран комментарий: {selected_comment}")
    
                    comment_field.clear()
                    comment_field.send_keys(selected_comment)
                    time.sleep(0.5)
                    
                    # ========== ПАУЗА ДЛИТЕЛЬНОСТИ ЗВОНКА ==========
                    if use_call_duration:
                        # Случайная длительность между min и max
                        call_duration = random.randint(duration_min, duration_max)
                        logger_func(f"⏱️ Держим звонок активным: {call_duration} секунд...")
                        time.sleep(call_duration)
                        logger_func(f"✅ Звонок завершен ({call_duration} сек)")
                    # ===============================================
    
                except Exception as e_comm:
                    logger_func(f"Ошибка поля комментария: {e_comm}")
                    logger_func(traceback.format_exc())
                    
                    # Проверяем сначала не закончился ли список клиентов
                    try:
                        error_btn = driver.find_element(By.XPATH, XPATH_ERROR_CLOSE_BUTTON)
                        if error_btn.is_displayed() and is_empty_list_message(driver, logger_func):
                            # Список клиентов закончился для этого часового пояса
                            error_btn.click()
                            time.sleep(1)
                            break  # Выходим из цикла обработки клиентов
                    except:
                        pass
                    
                    # Проверяем не окно ли ошибки вызвало проблему
                    if _check_and_handle_error(driver, wait, zoiper, logger_func):
                        # Ошибка обработана, продолжаем цикл заново
                        continue
                    
                    _safe_continue(driver, logger_func)
                    continue
    
                if stop_flag and stop_flag.is_set():
                    break
    
                # Отправка комментария
                try:
                    logger_func("Нажатие 'Отправить'...")
                    WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, XPATH_MODAL_SUBMIT_BUTTON))
                    ).click()
                    time.sleep(2.5)
                except Exception as e_submit:
                    logger_func(f"Ошибка отправки: {e_submit}")
                    logger_func(traceback.format_exc())
                    
                    # Проверяем сначала не закончился ли список клиентов
                    try:
                        error_btn = driver.find_element(By.XPATH, XPATH_ERROR_CLOSE_BUTTON)
                        if error_btn.is_displayed() and is_empty_list_message(driver, logger_func):
                            # Список клиентов закончился для этого часового пояса
                            error_btn.click()
                            time.sleep(1)
                            break  # Выходим из цикла обработки клиентов
                    except:
                        pass
                    
                    # Проверяем не окно ли ошибки вызвало проблему
                    if _check_and_handle_error(driver, wait, zoiper, logger_func):
                        # Ошибка обработана, продолжаем цикл заново
                        continue
                    
                    _safe_continue(driver, logger_func)
                    break
    
                if stop_flag and stop_flag.is_set():
                    break
    
                # Продолжить
                try:
                    logger_func("Нажатие 'Продолжить'...")
                    continue_btn = WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((By.XPATH, XPATH_MODAL_CONTINUE_BUTTON))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", continue_btn)
                    time.sleep(0.5)
                    continue_btn.click()
    
                    processed_clients_count += 1
                    logger_func(f"Клиент #{processed_clients_count} обработан.")
                    
                    # Обновляем StatusManager
                    sm.increment_processed("calls")
                    
                    # Обновление прогресса
                    if progress_callback:
                        progress_callback(processed_clients_count)
                    
                    time.sleep(3)
    
                except Exception as e_cont:
                    logger_func(f"Ошибка 'Продолжить': {e_cont}")
                    logger_func(traceback.format_exc())
                    
                    # Проверяем сначала не закончился ли список клиентов
                    try:
                        error_btn = driver.find_element(By.XPATH, XPATH_ERROR_CLOSE_BUTTON)
                        if error_btn.is_displayed() and is_empty_list_message(driver, logger_func):
                            # Список клиентов закончился для этого часового пояса
                            error_btn.click()
                            time.sleep(1)
                            break  # Выходим из цикла обработки клиентов
                    except:
                        pass
                    
                    # Проверяем не окно ли ошибки вызвало проблему
                    if _check_and_handle_error(driver, wait, zoiper, logger_func):
                        # Ошибка обработана, продолжаем цикл заново
                        continue
                    
                    break
    
            logger_func(f"\n{'='*60}")
            if current_timezone:
                logger_func(f"✅ Часовой пояс {current_timezone} завершен")
            logger_func(f"Обработано клиентов в этом поясе: {processed_clients_count}")
            logger_func(f"{'='*60}\n")
            
            # Обновляем общий счетчик
            total_processed += processed_clients_count
            
        # Конец цикла по часовым поясам
        
        # ===================== ИТОГОВАЯ СТАТИСТИКА =====================
        logger_func(f"\n{'#'*60}")
        logger_func(f"ОБЗВОН ЗАВЕРШЕН")
        logger_func(f"{'#'*60}")
        if use_timezones:
            logger_func(f"Обработано часовых поясов: {len(timezones_to_process)}")
        logger_func(f"Всего обработано клиентов: {total_processed}")
        logger_func(f"{'#'*60}\n")
        
        # 📱 Уведомление об успешном завершении
        if TELEGRAM_AVAILABLE and is_bot_available():
            mode_text = "Повторный обзвон" if repeat_mode else "Обзвон"
            send_notification_sync(
                f"✅ <b>ЗВОНКИ ЗАВЕРШЕНЫ</b>\n\n"
                f"🔹 Режим: {mode_text}\n"
                f"👥 Обработано клиентов: <b>{total_processed}</b>\n"
                + (f"🌍 Часовых поясов: {len(timezones_to_process)}\n" if use_timezones else "")
            )

    except Exception as e:
        error_msg = f"Глобальная ошибка: {e}"
        logger_func(error_msg)
        logger_func(traceback.format_exc())
        
        # Записываем ошибку в StatusManager
        sm.update_mode_status("calls", last_error=error_msg)
        sm.add_log(error_msg)
        
        # 📱 Критическое уведомление
        if TELEGRAM_AVAILABLE and is_bot_available():
            send_notification_sync(
                f"🚨 <b>ЗВОНКИ УПАЛИ</b>\n\n"
                f"❌ Критическая ошибка: {str(e)[:100]}\n\n"
                f"Проверьте логи программы"
            )
        
    finally:
        # Завершаем режим в StatusManager
        sm.update_mode_status("calls", running=False)
        total = sm.get_status()["calls"]["processed"]
        sm.add_log(f"Звонки завершены. Обработано: {total}")
        
        # Закрываем браузер
        if driver:
            logger_func("Браузер закроется через 3 секунды...")
            time.sleep(3)
            driver.quit()
            logger_func("Браузер закрыт.")
        
        # Закрываем Zoiper (убиваем процесс)
        logger_func("📴 Закрываем Zoiper...")
        zoiper.hangup()
        logger_func("✅ Zoiper закрыт")