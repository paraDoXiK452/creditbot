# -*- coding: utf-8 -*-
"""
💬 Процессор комментариев
Вся бизнес-логика режима комментариев из старого app_gui_truly_complete.py
"""

import time
import json
import os
import random
import re
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from process_manager import register_driver

# StatusManager для обновления статуса и логов
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
# КОНСТАНТЫ - XPATH'ы и другие параметры
# =============================================================================

XPATH_USERNAME_FIELD_BOT = "//*[@id='managerloginform-phone']"
XPATH_PASSWORD_FIELD_BOT = "//*[@id='managerloginform-password']"
XPATH_LOGIN_BUTTON_BOT = "//*[@id='w0']/div[3]/button"
XPATH_COMMENT_FIELD_BOT = "//*[@id='collectorcommentform-message']"
XPATH_SUBMIT_BUTTON_BOT = "//*[@id='js-collector-comment-form-submit']"
XPATH_ALL_ROWS_TABLE_BOT = "//*[@id='w2-container']/table/tbody/tr"
XPATH_LI_NEXT_PAGINATION_BOT = "//*[@id='w2']/ul/li[contains(@class,'next')]"
MAIN_PAGE_PART_BOT = "collector-debt/work"
XPATH_HISTORY_ALL_ROWS_CLIENT_PAGE = "//div[@id='w1-container']//table/tbody/tr"
XPATH_HISTORY_COMMENT_TEXT_RELATIVE = ".//td[2]"

JUNK_COMMENT_PHRASES = [
    "звонок: время:",
    "сообщение клиенту: ссылка для оплаты",
    "заявка назначена пользователю:",
    "просрочка:",
    "заявка перенесена в свободные"
]


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def is_junk_comment(text, junk_list):
    """Проверка, является ли комментарий мусорным"""
    text_lower = text.lower()
    for phrase in junk_list:
        if phrase.lower() in text_lower:
            return True
    return False


def is_detailed_info(text):
    """Проверка на детальную информацию о клиенте"""
    keywords = [
        "фамилия:", "имя:", "отчество:", "дата рождения:",
        "телефон:", "паспорт рф:", "место_работы:",
        "должность:", "сумма_дохода:"
    ]
    found_count = 0
    text_lower = text.lower()
    for kw in keywords:
        if kw in text_lower:
            found_count += 1
    return found_count >= 4


def is_fio_and_dob(text):
    """Проверка на ФИО + дату рождения"""
    match = re.search(
        r"([А-ЯA-яЁё]{2,}\s+[А-ЯA-яЁё]{2,}(\s+[А-ЯA-яЁё]{2,})?)\s+(\d{2}\.\d{2}\.\d{4})",
        text,
        re.IGNORECASE
    )
    return bool(match)


def is_social_links(text):
    """Проверка на социальные сети"""
    text_lower = text.lower()
    return (
        "https://vk.com/" in text_lower or
        "https://ok.ru/" in text_lower or
        "https://onli-vk.ru/" in text_lower
    )


def find_column_indices(driver, logger_func):
    """
    Динамическое определение индексов столбцов по заголовкам таблицы
    
    Returns:
        tuple: (fio_column_index, date_column_index) - индексы начинаются с 1 для XPath
               Или (3, 7) по умолчанию если не удалось определить
    """
    try:
        logger_func("🔍 Автопоиск столбцов по заголовкам таблицы...")
        
        # Находим все заголовки таблицы
        headers = driver.find_elements(By.XPATH, "//*[@id='w2-container']/table/thead/tr/th")
        
        fio_index = None
        date_index = None
        
        for idx, header in enumerate(headers, start=1):  # XPath индексы с 1
            header_text = header.text.strip().lower()
            logger_func(f"  Столбец {idx}: '{header.text.strip()}'")
            
            # Ищем столбец с ФИО (разные варианты названия)
            if fio_index is None and any(keyword in header_text for keyword in ['фио', 'клиент', 'ф.и.о', 'должник']):
                fio_index = idx
                logger_func(f"    ✅ ФИО найден в столбце {idx}")
            
            # Ищем столбец с датой отработки (разные варианты)
            if date_index is None and any(keyword in header_text for keyword in ['дата', 'отработк', 'контакт', 'последн']):
                date_index = idx
                logger_func(f"    ✅ Дата отработки найдена в столбце {idx}")
        
        if fio_index and date_index:
            logger_func(f"✅ Столбцы определены: ФИО={fio_index}, Дата={date_index}")
            return fio_index, date_index
        else:
            logger_func(f"⚠️ Не все столбцы найдены: ФИО={fio_index}, Дата={date_index}")
            logger_func("   Использую значения по умолчанию: ФИО=3, Дата=7")
            return 3, 7  # Значения по умолчанию
            
    except Exception as e:
        logger_func(f"❌ Ошибка при определении столбцов: {e}")
        logger_func(traceback.format_exc())
        logger_func("   Использую значения по умолчанию: ФИО=3, Дата=7")
        return 3, 7  # Значения по умолчанию


def process_comments(gui_login_url, gui_username, gui_password, gui_possible_comments,
                    gui_min_delay_sec, gui_max_delay_sec, stop_flag, logger_func, **kwargs):
    """
    Основная функция обработки комментариев (бывшая run_actual_bot_logic)
    
    Args:
        gui_login_url: URL страницы входа
        gui_username: Логин (телефон)
        gui_password: Пароль
        gui_possible_comments: Список шаблонных комментариев
        gui_min_delay_sec: Минимальная задержка между отправками
        gui_max_delay_sec: Максимальная задержка между отправками
        stop_flag: Флаг остановки (threading.Event)
        logger_func: Функция для логирования
        **kwargs: Дополнительные параметры (use_delay_search, delay_from, delay_to)
    """
    logger_func("--- Начало работы Selenium бота (режим комментариев) ---")
    
    # Инициализация StatusManager
    sm = get_status_manager()
    sm.update_mode_status("comments", running=True, processed=0, last_error="")
    sm.add_log("Режим комментариев запущен")
    
    driver = None
    try:
        logger_func("Инициализация драйвера Chrome для бота...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        register_driver(driver)
        driver.maximize_window()
        wait = WebDriverWait(driver, 20)
        logger_func("Драйвер инициализирован.")

        # =====================================================
        # ИСПРАВЛЕННАЯ АВТОРИЗАЦИЯ - ОДНА СТРОКА!
        # =====================================================
        if not authorize_maxcredit(driver, wait, gui_login_url,
                                   gui_username, gui_password, logger_func):
            logger_func("❌ Авторизация не удалась!")
            
            # 📱 Критическое уведомление
            if TELEGRAM_AVAILABLE and is_bot_available():
                send_notification_sync(
                    f"🚨 <b>КОММЕНТЫ УПАЛИ</b>\n\n"
                    f"❌ Не удалось авторизоваться на сайте\n\n"
                    f"Проверьте логин и пароль"
                )
            return
        
        logger_func("✅ Авторизация успешна! Готов к работе.")
        
        # 📱 Уведомление о запуске
        if TELEGRAM_AVAILABLE and is_bot_available():
            filter_text = ""
            use_delay_search_flag = kwargs.get("use_delay_search", False)
            search_delay_from_flag = kwargs.get("search_delay_from", "")
            search_delay_to_flag = kwargs.get("search_delay_to", "")
            
            if use_delay_search_flag and (search_delay_from_flag or search_delay_to_flag):
                filter_text = "\n🔍 Фильтр: "
                if search_delay_from_flag and search_delay_to_flag:
                    filter_text += f"{search_delay_from_flag}-{search_delay_to_flag} дней"
                elif search_delay_from_flag:
                    filter_text += f"от {search_delay_from_flag} дней"
                elif search_delay_to_flag:
                    filter_text += f"до {search_delay_to_flag} дней"
            
            send_notification_sync(
                f"💬 <b>КОММЕНТЫ ЗАПУЩЕНЫ</b>\n\n"
                f"📝 Шаблонов: {len(gui_possible_comments) if isinstance(gui_possible_comments, list) else 1}\n"
                f"⏱️ Задержка: {gui_min_delay_sec}-{gui_max_delay_sec} сек{filter_text}"
            )
        
        # =====================================================
        # Выполняем поиск по дням просрочки, если эта опция включена
        use_delay_search = kwargs.get("use_delay_search", False)
        search_delay_from = kwargs.get("search_delay_from", "")
        search_delay_to = kwargs.get("search_delay_to", "")
        
        # Использовать ли старые ценные комментарии из истории
        use_old_comments = kwargs.get("use_old_comments", False)
        
        # Пропускать ли клиентов с комментами сегодня
        skip_commented = kwargs.get("skip_commented", True)  # По умолчанию True
        
        logger_func(f"⚙️ Настройки: skip_commented={skip_commented}, use_old_comments={use_old_comments}")

        if use_delay_search and (search_delay_from or search_delay_to):
            logger_func("Активирован поиск по дням просрочки")
            try:
                delay_from_field_xpath = '//*[@id="collectordebtsearch-delayfrom"]'
                delay_to_field_xpath = '//*[@id="collectordebtsearch-delayto"]'

                if search_delay_from:
                    try:
                        delay_from_field = wait.until(EC.presence_of_element_located((By.XPATH, delay_from_field_xpath)))
                        delay_from_field.clear()
                        delay_from_field.send_keys(search_delay_from)
                        time.sleep(0.5)
                        logger_func(f"Установлено дней просрочки 'от': {search_delay_from}")
                    except Exception as e_from:
                        logger_func(f"Поле 'от' не найдено: {e_from}")

                if search_delay_to:
                    try:
                        delay_to_field = wait.until(EC.presence_of_element_located((By.XPATH, delay_to_field_xpath)))
                        delay_to_field.clear()
                        delay_to_field.send_keys(search_delay_to)
                        time.sleep(0.5)
                        logger_func(f"Установлено дней просрочки 'до': {search_delay_to}")
                    except Exception as e_to:
                        logger_func(f"Поле 'до' не найдено: {e_to}")

                # Нажимаем поиск
                search_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="w1"]/div[4]/div[1]/button[1]')))
                search_button.click()
                time.sleep(3)
                wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE_BOT)))
                logger_func("Поиск выполнен")

            except Exception as e_search:
                logger_func(f"Ошибка поиска по дням: {e_search}")
                logger_func("Продолжаем без поиска")
        else:
            logger_func("Поиск по дням просрочки отключен или параметры не заданы.")

        protocol_domain_gui = gui_login_url.split('/')[0] + '//' + gui_login_url.split('/')[2]
        expected_list_url_base_gui = f"{protocol_domain_gui}/{MAIN_PAGE_PART_BOT}"
        logger_func(f"Проверка URL в потоке бота: Текущий URL = '{driver.current_url}'")
        if not driver.current_url.startswith(expected_list_url_base_gui):
            logger_func(f"ПРЕДУПРЕЖДЕНИЕ: URL ({driver.current_url}) не начинается с ожидаемого ({expected_list_url_base_gui}).")
        else:
            logger_func(f"Находимся на ожидаемой странице: {driver.current_url}")

        try:
            wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE_BOT)))
            
            # 🔍 АВТООПРЕДЕЛЕНИЕ ИНДЕКСОВ СТОЛБЦОВ
            fio_col_idx, date_col_idx = find_column_indices(driver, logger_func)
            logger_func(f"📊 Используем столбцы: ФИО={fio_col_idx}, Дата={date_col_idx}")
            
        except Exception as e_tbl_main:
            logger_func(f"ОШИБКА: Таблица не найдена после логина: {e_tbl_main}")
            
            # 📱 Критическое уведомление
            if TELEGRAM_AVAILABLE and is_bot_available():
                send_notification_sync(
                    f"🚨 <b>КОММЕНТЫ УПАЛИ</b>\n\n"
                    f"❌ Таблица клиентов не найдена\n\n"
                    f"Проверьте доступ к сайту"
                )
            return
        logger_func("  Таблица на текущей странице после логина подтверждена.")

        current_page_number = 1
        total_comments_sent_this_session = 0

        while True:
            if stop_flag.is_set():
                logger_func("Остановка (начало цикла страниц).")
                
                # 📱 Уведомление об остановке
                if TELEGRAM_AVAILABLE and is_bot_available():
                    send_notification_sync(
                        f"⏹️ <b>КОММЕНТЫ ОСТАНОВЛЕНЫ</b>\n\n"
                        f"Остановлено вручную пользователем\n"
                        f"📊 Отправлено комментариев: {total_comments_sent_this_session}"
                    )
                break
            logger_func(f"\n--- Обработка СТРАНИЦЫ {current_page_number} ---")
            logger_func(f"Текущий URL: {driver.current_url}")
            today_date_str = datetime.now().strftime("%d.%m.%Y")

            try:
                logger_func(f"Ожидание таблицы на странице {current_page_number}...")
                wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE_BOT)))
                time.sleep(1.5)
                all_rows_on_page_elements = driver.find_elements(By.XPATH, XPATH_ALL_ROWS_TABLE_BOT)
                rows_count_on_page = len(all_rows_on_page_elements)
                if rows_count_on_page == 0 and current_page_number > 1:
                    logger_func(f"Строки не найдены на стр. {current_page_number}. Конец.")
                    break
                elif rows_count_on_page == 0 and current_page_number == 1:
                    logger_func(f"Строки не найдены на ПЕРВОЙ стр. Проверьте.")
                    break
                logger_func(f"Найдено строк на странице {current_page_number}: {rows_count_on_page}")
                logger_func("-" * 30)

                i = 0
                while i < rows_count_on_page:
                    if stop_flag.is_set():
                        logger_func("Остановка (цикл по строкам).")
                        break
                    logger_func(f"--- Обработка строки {i+1}/{rows_count_on_page} (страница {current_page_number}) ---")

                    try:
                        current_all_rows_fresh = wait.until(EC.presence_of_all_elements_located((By.XPATH, XPATH_ALL_ROWS_TABLE_BOT)))
                        if i >= len(current_all_rows_fresh):
                            logger_func("  Кол-во строк изменилось.")
                            break
                        row_element = current_all_rows_fresh[i]
                    except Exception as e_frl:
                        logger_func(f"  Ошибка при получении строки {i+1}: {e_frl}")
                        i += 1
                        continue

                    try:
                        date_otrabotki_text = row_element.find_element(By.XPATH, f".//td[{date_col_idx}]").text.strip()
                        fio_link_element_candidate = row_element.find_element(By.XPATH, f".//td[{fio_col_idx}]/a")
                        fio_text = fio_link_element_candidate.text.strip()
                        logger_func(f"  Дата отработки: '{date_otrabotki_text}', ФИО: '{fio_text}'")
                    except Exception as e_ed:
                        logger_func(f"  Не удалось извлечь данные из строки {i+1}: {e_ed}")
                        logger_func("-" * 30)
                        i += 1
                        continue

                    # Логика: обрабатывать если (НЕ пропускаем комментированных) ИЛИ (дата != сегодня)
                    should_process = not skip_commented or date_otrabotki_text != today_date_str
                    
                    if should_process:
                        logger_func(f"  >>> НУЖНО ОБРАБОТАТЬ: '{fio_text}' <<<")
                        if total_comments_sent_this_session > 0:
                            delay = random.randint(gui_min_delay_sec, gui_max_delay_sec)
                            logger_func(f"  Ожидание {delay} секунд перед отправкой след. комментария...")
                            start_delay_time = time.time()
                            while time.time() - start_delay_time < delay:
                                if stop_flag.is_set():
                                    logger_func("Остановка во время ожидания.")
                                    break
                                time.sleep(0.5)
                            if stop_flag.is_set():
                                break
                        else:
                            logger_func("  Это первый подходящий клиент в сессии, ставим комментарий сразу.")

                        list_page_url_for_return = driver.current_url
                        main_window_handle = driver.current_window_handle
                        logger_func(f"  Основное окно: {main_window_handle}, URL: {list_page_url_for_return}")
                        new_window_handle = None
                        logger_func(f"  Кликаем на ФИО: '{fio_text}' (ожидаем новую вкладку)...")

                        try:
                            fio_link_to_click = wait.until(EC.element_to_be_clickable(fio_link_element_candidate))
                            handles_before_click = driver.window_handles
                            fio_link_to_click.click()
                            logger_func(f"  Клик по ФИО '{fio_text}' выполнен.")
                            WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(len(handles_before_click) + 1))
                            all_window_handles = driver.window_handles
                            for handle in all_window_handles:
                                if handle != main_window_handle:
                                    new_window_handle = handle
                                    break
                            if new_window_handle:
                                logger_func(f"  Найдена новая вкладка: {new_window_handle}. Переключаемся...")
                                driver.switch_to.window(new_window_handle)
                                logger_func(f"  Переключились. URL: {driver.current_url}")
                            else:
                                logger_func("  ОШИБКА: Новая вкладка не открылась.")
                                raise Exception("Новая вкладка не найдена")
                        except Exception as e_cos:
                            logger_func(f"  Ошибка при клике/переключении: {e_cos}")
                            if driver.current_window_handle != main_window_handle:
                                try:
                                    driver.switch_to.window(main_window_handle)
                                except:
                                    pass
                            driver.get(list_page_url_for_return)
                            wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE_BOT)))
                            logger_func("-" * 30)
                            i += 1
                            continue

                        if new_window_handle:
                            comment_to_send_final = None
                            try:
                                expected_client_page_url_part = "collector-comment/view"
                                logger_func(f"  На нов.вкл: Ожидание URL с '{expected_client_page_url_part}'...")
                                WebDriverWait(driver, 15).until(EC.url_contains(expected_client_page_url_part))
                                logger_func(f"  Успех: URL нов.вкл '{driver.current_url}'.")
                                
                                # Константа - сколько последних записей проверять на дубликаты
                                RECENT_COMMENTS_TO_CHECK = 5
                                
                                history_rows_elements = []

                                try:
                                    logger_func(f"  Поиск истории по XPath: {XPATH_HISTORY_ALL_ROWS_CLIENT_PAGE}")
                                    history_rows_elements = WebDriverWait(driver, 10).until(
                                        EC.presence_of_all_elements_located((By.XPATH, XPATH_HISTORY_ALL_ROWS_CLIENT_PAGE))
                                    )
                                    logger_func(f"    Найдено записей в истории: {len(history_rows_elements)}")
                                except Exception as e_hf:
                                    logger_func(f"    Не удалось загрузить историю: {e_hf}")
                                
                                # ========== ПРОВЕРКА skip_commented ==========
                                # Проверяем - есть ли УЖЕ комментарий сегодня от нас
                                if skip_commented and history_rows_elements:
                                    has_today_comment = False
                                    today_str = datetime.now().strftime("%d.%m.%Y")
                                    
                                    # Проверяем последние 3 записи
                                    for idx in range(min(3, len(history_rows_elements))):
                                        try:
                                            row = history_rows_elements[idx]
                                            # Ищем дату в строке истории (обычно в td[1])
                                            date_cell = row.find_element(By.XPATH, ".//td[1]")
                                            date_text = date_cell.text.strip()
                                            
                                            # Проверяем есть ли сегодняшняя дата
                                            if today_str in date_text:
                                                # Проверяем - не мусорный ли это комментарий
                                                comment_cell = row.find_element(By.XPATH, ".//td[2]")
                                                comment_text = comment_cell.text.strip()
                                                
                                                if not is_junk_comment(comment_text, JUNK_COMMENT_PHRASES):
                                                    has_today_comment = True
                                                    logger_func(f"  ⏭ ПРОПУСК: Уже есть комментарий сегодня ({today_str})")
                                                    logger_func(f"     Комментарий: '{comment_text[:50]}...'")
                                                    break
                                        except Exception as e:
                                            # Не критично, продолжаем
                                            pass
                                    
                                    if has_today_comment:
                                        # Закрываем вкладку и переходим к следующему клиенту
                                        try:
                                            driver.close()
                                        except:
                                            pass
                                        driver.switch_to.window(main_window_handle)
                                        driver.get(list_page_url_for_return)
                                        wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE_BOT)))
                                        logger_func("-" * 30)
                                        i += 1
                                        continue
                                # =============================================

                                found_valuable_for_copy = None
                                
                                # Если опция использования старых комментов включена
                                if use_old_comments and history_rows_elements:
                                    # Собираем текст последних N комментов для проверки на дубликаты
                                    recent_comments_texts = []
                                    for idx in range(min(RECENT_COMMENTS_TO_CHECK, len(history_rows_elements))):
                                        try:
                                            text = history_rows_elements[idx].find_element(
                                                By.XPATH, XPATH_HISTORY_COMMENT_TEXT_RELATIVE
                                            ).text.strip()
                                            recent_comments_texts.append(text)
                                        except:
                                            pass
                                    
                                    logger_func(f"  Собрано последних комментов для проверки дубликатов: {len(recent_comments_texts)}")
                                    
                                    # Теперь ищем ценный коммент
                                    for idx, hist_row_el in enumerate(history_rows_elements):
                                        if stop_flag.is_set():
                                            logger_func("Остановка (анализ истории).")
                                            break
                                        try:
                                            current_hist_text = hist_row_el.find_element(
                                                By.XPATH, XPATH_HISTORY_COMMENT_TEXT_RELATIVE
                                            ).text.strip()
                                            log_hist_text_short = current_hist_text[:60].replace('\n', ' ')
                                            logger_func(f"    История[{idx}]: '{log_hist_text_short}...'")

                                            # Пропускаем мусорные
                                            if is_junk_comment(current_hist_text, JUNK_COMMENT_PHRASES):
                                                logger_func(f"      -> Пропускаем (мусорный)")
                                                continue

                                            # Проверяем ценность
                                            is_valuable = False
                                            value_reason = ""
                                            
                                            if is_detailed_info(current_hist_text):
                                                is_valuable = True
                                                value_reason = "детальная информация"
                                            elif is_fio_and_dob(current_hist_text):
                                                is_valuable = True
                                                value_reason = "ФИО + дата рождения"
                                            elif is_social_links(current_hist_text):
                                                is_valuable = True
                                                value_reason = "соцсети"
                                            
                                            if is_valuable:
                                                # Проверяем - не был ли этот коммент в последних N записях
                                                if current_hist_text in recent_comments_texts:
                                                    logger_func(f"      -> ЦЕННЫЙ ({value_reason}), но УЖЕ ИСПОЛЬЗОВАЛСЯ в последних {RECENT_COMMENTS_TO_CHECK} записях. Пропускаем.")
                                                    continue
                                                else:
                                                    logger_func(f"      -> ЦЕННЫЙ! ({value_reason}) и НЕ повторяется")
                                                    found_valuable_for_copy = current_hist_text
                                                    break
                                            else:
                                                logger_func(f"      -> Не ценный")

                                        except Exception as e_hist_row:
                                            logger_func(f"    Ошибка обработки строки истории {idx}: {e_hist_row}")
                                            continue

                                if found_valuable_for_copy:
                                    comment_to_send_final = found_valuable_for_copy
                                    logger_func(f"  БУДЕМ КОПИРОВАТЬ СТАРЫЙ КОММЕНТАРИЙ: '{comment_to_send_final[:80]}...'")
                                else:
                                    if gui_possible_comments:
                                        comment_to_send_final = random.choice(gui_possible_comments)
                                        logger_func(f"  Ценный комментарий не найден. Берем случайный из шаблонных: '{comment_to_send_final}'")
                                    else:
                                        logger_func(f"  Ценный комментарий не найден И шаблонных нет. Пропускаем клиента.")
                                        comment_to_send_final = None

                                if comment_to_send_final:
                                    logger_func("  Прокрутка к полю комментария...")
                                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                    time.sleep(1)

                                    comment_field = wait.until(EC.visibility_of_element_located((By.XPATH, XPATH_COMMENT_FIELD_BOT)))
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comment_field)
                                    time.sleep(0.5)

                                    logger_func("  Вводим комментарий...")
                                    comment_field.clear()
                                    comment_field.send_keys(comment_to_send_final)
                                    time.sleep(0.5)

                                    submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_SUBMIT_BUTTON_BOT)))
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
                                    time.sleep(0.5)

                                    logger_func("  Нажимаем 'Отправить'...")
                                    submit_button.click()
                                    total_comments_sent_this_session += 1
                                    logger_func(f"  Комментарий отправлен! Всего в сессии: {total_comments_sent_this_session}")
                                    
                                    # Обновляем счётчик в StatusManager
                                    sm.increment_processed("comments")
                                    
                                    time.sleep(2)

                            except Exception as e_comment:
                                logger_func(f"  ОШИБКА на НОВОЙ вкладке для '{fio_text}': {e_comment}")
                                logger_func(traceback.format_exc())
                            finally:
                                if driver.current_window_handle != main_window_handle and new_window_handle:
                                    logger_func(f"  Закрываем новую ({driver.current_window_handle})...")
                                    driver.close()

                                if main_window_handle in driver.window_handles:
                                    logger_func(f"  Возврат на основную ({main_window_handle})...")
                                    driver.switch_to.window(main_window_handle)
                                    logger_func(f"  Вернулись. URL: {driver.current_url}")
                                elif driver.window_handles:
                                    logger_func("  Основное окно не найдено. На первое доступное.")
                                    driver.switch_to.window(driver.window_handles[0])
                                else:
                                    logger_func("  Все окна закрыты.")
                                    stop_flag.set()
                                    return

                                # Обновление страницы списка
                                max_retry = 3
                                retry_count = 0
                                logger_func(f"  Обновление страницы списка: {list_page_url_for_return}")

                                while retry_count < max_retry:
                                    try:
                                        driver.get(list_page_url_for_return)
                                        time.sleep(2)
                                        logger_func("  Ожидание таблицы...")
                                        wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE_BOT)))
                                        logger_func("  Таблица загружена.")
                                        break
                                    except Exception as e_reload:
                                        retry_count += 1
                                        logger_func(f"  Попытка {retry_count}: Ошибка обновления страницы: {e_reload}")
                                        time.sleep(3)

                                if retry_count == max_retry:
                                    logger_func("  Не удалось обновить страницу списка после 3 попыток. Пропускаем клиента.")
                                    i += 1
                                    continue
                                
                                # Успешно обработали клиента, переходим к следующему
                                logger_func("  Клиент обработан. Переход к следующему.")
                                i += 1
                                continue
                        else:
                            logger_func("  Пропуск (новая вкладка не открыта).")
                            if driver.current_url != list_page_url_for_return:
                                driver.get(list_page_url_for_return)
                            wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE_BOT)))
                            i += 1
                            continue
                    else:
                        if skip_commented:
                            logger_func(f"  Дата отработки = сегодня ({today_date_str}). Пропускаем (skip_commented=True).")
                        else:
                            logger_func(f"  Условие не выполнено. Пропускаем.")

                    logger_func("-" * 30)
                    i += 1
                # Конец while по строкам

                if stop_flag and stop_flag.is_set():
                    logger_func("Остановка (конец цикла по строкам).")
                    break

                logger_func(f"Обработка строк на стр. {current_page_number} завершена.")

                # ПАГИНАЦИЯ
                if stop_flag and stop_flag.is_set():
                    logger_func("Остановка (перед пагинацией).")
                    break

                try:
                    logger_func(f"Поиск 'li.next': {XPATH_LI_NEXT_PAGINATION_BOT}")
                    li_next_btn_els = driver.find_elements(By.XPATH, XPATH_LI_NEXT_PAGINATION_BOT)
                    if not li_next_btn_els:
                        logger_func("'li.next' не найден. Конец.")
                        break

                    li_next_btn = li_next_btn_els[0]
                    if "disabled" in li_next_btn.get_attribute("class").split():
                        logger_func("Кнопка 'Далее' неактивна. Конец.")
                        break
                    else:
                        try:
                            active_link = li_next_btn.find_element(By.XPATH, ".//a")
                            logger_func("Найдена активная кнопка 'Далее'. Кликаем...")

                            try:
                                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", active_link)
                                time.sleep(0.5)
                            except Exception as e_sp:
                                logger_func(f"  Ошибка прокрутки к пагинации: {e_sp}")

                            active_link_click = wait.until(EC.element_to_be_clickable(active_link))
                            url_b4_pag_click = driver.current_url
                            active_link_click.click()
                            cur_pg_num_exp_url = current_page_number + 1
                            current_page_number += 1

                            logger_func(f"Ожидание загрузки стр. {current_page_number}...")
                            exp_new_pg_url_part_pag = f"page={cur_pg_num_exp_url}"
                            logger_func(f"  Ожидаем URL с '{exp_new_pg_url_part_pag}' (был: {url_b4_pag_click})...")

                            WebDriverWait(driver, 20).until(
                                lambda d: exp_new_pg_url_part_pag in d.current_url and d.current_url != url_b4_pag_click
                            )
                            logger_func(f"Перешли на стр. {current_page_number}. URL: {driver.current_url}")
                            wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE_BOT)))
                            logger_func(f"Таблица на стр. {current_page_number} загружена.")

                        except Exception as e_falp:
                            logger_func(f"Ссылка <a> в 'li.next' не найдена/клик: {e_falp}. Завершаем.")
                            break

                except Exception as e_pb:
                    logger_func(f"Ошибка в пагинации: {e_pb}. Завершаем.")
                    break

            except Exception as e_ppo:
                logger_func(f"Крит. ошибка при обработке стр. {current_page_number}: {e_ppo}")
                logger_func(traceback.format_exc())
                break
        # Конец while True

        logger_func(f"\nОбработка страниц завершена. Комментариев отправлено: {total_comments_sent_this_session}")
        
        # 📱 Уведомление об успешном завершении
        if TELEGRAM_AVAILABLE and is_bot_available():
            send_notification_sync(
                f"✅ <b>КОММЕНТЫ ЗАВЕРШЕНЫ</b>\n\n"
                f"📝 Отправлено комментариев: <b>{total_comments_sent_this_session}</b>"
            )

    except Exception as e:
        error_msg = f"КРИТИЧЕСКАЯ ОШИБКА: {e}"
        logger_func(error_msg)
        logger_func(traceback.format_exc())
        
        # Записываем ошибку в StatusManager
        sm.update_mode_status("comments", last_error=error_msg)
        sm.add_log(error_msg)
        
        # 📱 Критическое уведомление
        if TELEGRAM_AVAILABLE and is_bot_available():
            send_notification_sync(
                f"🚨 <b>КОММЕНТЫ УПАЛИ</b>\n\n"
                f"❌ Критическая ошибка: {str(e)[:100]}\n\n"
                f"Проверьте логи программы"
            )
    finally:
        # Завершаем режим в StatusManager
        sm.update_mode_status("comments", running=False)
        total = sm.get_status()["comments"]["processed"]
        sm.add_log(f"Комментарии завершены. Обработано: {total}")
        
        if driver:
            try:
                logger_func("Закрытие драйвера...")
                driver.quit()
                logger_func("Драйвер закрыт.")
            except Exception as e_quit:
                logger_func(f"Ошибка при закрытии драйвера: {e_quit}")