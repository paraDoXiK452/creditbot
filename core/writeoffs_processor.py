# -*- coding: utf-8 -*-
"""
💰 Процессор автоматических списаний
Автоматическое списание средств с карт клиентов
"""

import time
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

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


# XPath константы
XPATH_USERNAME_FIELD = "//*[@id='managerloginform-phone']"
XPATH_PASSWORD_FIELD = "//*[@id='managerloginform-password']"
XPATH_LOGIN_BUTTON = "//*[@id='w0']/div[3]/button"
XPATH_ALL_ROWS_TABLE = "//*[@id='w2-container']/table/tbody/tr"
XPATH_LI_NEXT_PAGINATION = "//*[@id='w2']/ul/li[contains(@class,'next')]"
MAIN_PAGE_PART = "collector-debt/work"

# XPath для списаний
XPATH_WRITEOFFS_TAB = "//a[contains(text(), 'Списания')]"
XPATH_NEW_WRITEOFF_BUTTON = "//a[contains(text(), 'Новое списание')]"
XPATH_ADD_BUTTON = "//button[contains(text(), 'Добавить')]"


def process_auto_writeoffs(login_url_proc, username_proc, password_proc, logger_func, stop_flag=None,
                          use_delay_search=False, delay_from="", delay_to=""):
    """Функция для автоматических списаний средств с карт клиентов."""
    
    logger_func("Запуск процесса автоматических списаний...")
    
    # Инициализация StatusManager
    sm = get_status_manager()
    sm.update_mode_status("writeoffs", running=True, processed=0, last_error="")
    sm.add_log("Режим списаний запущен")
    
    driver = None
    total_writeoffs_this_session = 0
    
    try:
        # Headless режим
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        logger_func("Браузер запущен (невидимый режим)")
        wait = WebDriverWait(driver, 20)

        # =====================================================
        # ИСПРАВЛЕННАЯ АВТОРИЗАЦИЯ - ОДНА СТРОКА!
        # =====================================================
        if not authorize_maxcredit(driver, wait, login_url_proc,
                                   username_proc, password_proc, logger_func):
            logger_func("❌ Авторизация не удалась!")
            
            # 📱 Критическое уведомление
            if TELEGRAM_AVAILABLE and is_bot_available():
                send_notification_sync(
                    f"🚨 <b>СПИСАНИЯ УПАЛИ</b>\n\n"
                    f"❌ Не удалось авторизоваться на сайте\n\n"
                    f"Проверьте логин и пароль"
                )
            return
        
        logger_func("✅ Авторизация успешна! Готов к работе.")
        
        # 📱 Уведомление о запуске
        if TELEGRAM_AVAILABLE and is_bot_available():
            filter_text = ""
            if use_delay_search and (delay_from or delay_to):
                filter_text = f"\n🔍 Фильтр: "
                if delay_from and delay_to:
                    filter_text += f"{delay_from}-{delay_to} дней"
                elif delay_from:
                    filter_text += f"от {delay_from} дней"
                elif delay_to:
                    filter_text += f"до {delay_to} дней"
            
            send_notification_sync(
                f"💰 <b>СПИСАНИЯ ЗАПУЩЕНЫ</b>\n\n"
                f"🔹 Автоматические списания средств{filter_text}\n"
                f"🤖 Режим: Headless (невидимый браузер)"
            )
        
        # =====================================================
        logger_func("Пауза после логина...")
        time.sleep(2)

        if stop_flag and stop_flag.is_set():
            logger_func("Получена команда остановки после логина.")
            
            # 📱 Уведомление об остановке
            if TELEGRAM_AVAILABLE and is_bot_available():
                send_notification_sync(
                    f"⏹️ <b>СПИСАНИЯ ОСТАНОВЛЕНЫ</b>\n\n"
                    f"Остановлено вручную пользователем"
                )
            return

        # ============================================================
        # Применяем фильтры по дням просрочки
        # ============================================================

        if use_delay_search and (delay_from or delay_to):
            logger_func("Активирован поиск по дням просрочки")
            try:
                if delay_from:
                    try:
                        delay_from_field = wait.until(EC.presence_of_element_located(
                            (By.XPATH, '//*[@id="collectordebtsearch-delayfrom"]')
                        ))
                        delay_from_field.clear()
                        delay_from_field.send_keys(delay_from)
                        time.sleep(0.5)
                        logger_func(f"Установлено 'дней просрочки от': {delay_from}")
                    except Exception as e_from:
                        logger_func(f"Поле 'от' не найдено: {e_from}")
                
                if delay_to:
                    try:
                        delay_to_field = wait.until(EC.presence_of_element_located(
                            (By.XPATH, '//*[@id="collectordebtsearch-delayto"]')
                        ))
                        delay_to_field.clear()
                        delay_to_field.send_keys(delay_to)
                        time.sleep(0.5)
                        logger_func(f"Установлено 'дней просрочки до': {delay_to}")
                    except Exception as e_to:
                        logger_func(f"Поле 'до' не найдено: {e_to}")
                
                search_button = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="w1"]/div[4]/div[1]/button[1]')
                ))
                search_button.click()
                time.sleep(3)
                wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE)))
                logger_func("Поиск выполнен successfully")
                
            except Exception as e_search:
                logger_func(f"Ошибка поиска: {e_search}")
        else:
            logger_func("Поиск по дням отключен.")

        if stop_flag and stop_flag.is_set():
            logger_func("Остановка после фильтров.")
            return

        # ============================================================
        # Проверка таблицы и дальнейшая логика списаний
        # ============================================================

        try:
            wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE)))
        except Exception as e_tbl:
            logger_func(f"Таблица не найдена: {e_tbl}")
            
            # 📱 Критическое уведомление
            if TELEGRAM_AVAILABLE and is_bot_available():
                send_notification_sync(
                    f"🚨 <b>СПИСАНИЯ УПАЛИ</b>\n\n"
                    f"❌ Таблица клиентов не найдена\n\n"
                    f"Проверьте доступ к сайту"
                )
            return
        
        logger_func("Таблица подтверждена.")

        current_page_number = 1

        # цикл страниц списаний
        while True:
            if stop_flag and stop_flag.is_set():
                logger_func("Остановка процесса.")
                break

            logger_func(f"\n--- СТРАНИЦА {current_page_number} (списания) ---")
            
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE)))
                time.sleep(1.5)
                
                all_rows = driver.find_elements(By.XPATH, XPATH_ALL_ROWS_TABLE)
                rows_count = len(all_rows)

                if rows_count == 0 and current_page_number > 1:
                    logger_func("Строк не найдено. Конец.")
                    break
                elif rows_count == 0 and current_page_number == 1:
                    logger_func("Пустая таблица на первой странице.")
                    break

                logger_func(f"Найдено строк: {rows_count}")

                i = 0
                while i < rows_count:
                    if stop_flag and stop_flag.is_set():
                        logger_func("Остановка.")
                        break

                    logger_func(f"--- Списание {i+1}/{rows_count} ---")

                    try:
                        current_rows = wait.until(EC.presence_of_all_elements_located(
                            (By.XPATH, XPATH_ALL_ROWS_TABLE)
                        ))
                        if i >= len(current_rows):
                            logger_func("Количество строк изменилось.")
                            break
                        row_element = current_rows[i]
                    except Exception as e_r:
                        logger_func(f"Ошибка получения строки: {e_r}")
                        i += 1
                        continue

                    try:
                        contract_link = row_element.find_element(By.XPATH, ".//td[2]/a")
                        contract_number = contract_link.text.strip()
                        logger_func(f"  Договор: {contract_number}")
                    except Exception as e_contract:
                        # DEBUG - смотрим структуру строки
                        try:
                            all_tds = row_element.find_elements(By.XPATH, ".//td")
                            logger_func(f"  DEBUG: В строке {len(all_tds)} столбцов:")
                            for idx, td in enumerate(all_tds, 1):
                                text = td.text[:50] if td.text else "(пусто)"
                                has_link = len(td.find_elements(By.XPATH, ".//a")) > 0
                                logger_func(f"    td[{idx}]: '{text}' | Ссылка: {has_link}")
                        except:
                            pass
                        
                        logger_func(f"  Не удалось взять номер договора: {e_contract}")
                        i += 1
                        continue

                    list_page_url = driver.current_url
                    main_handle = driver.current_window_handle
                    new_handle = None

                    # Открытие договора
                    logger_func(f"  Кликаем на договор {contract_number}...")
                    try:
                        contract_clickable = wait.until(EC.element_to_be_clickable(contract_link))
                        handles_before = driver.window_handles
                        contract_clickable.click()

                        WebDriverWait(driver, 10).until(
                            EC.number_of_windows_to_be(len(handles_before) + 1)
                        )

                        for h in driver.window_handles:
                            if h != main_handle:
                                new_handle = h
                                break

                        if new_handle:
                            driver.switch_to.window(new_handle)
                            logger_func("  Перешли на вкладку договора")
                        else:
                            raise Exception("Новая вкладка не найдена")

                    except Exception as e_click:
                        logger_func(f"  Ошибка клика: {e_click}")
                        if driver.current_window_handle != main_handle:
                            try:
                                driver.switch_to.window(main_handle)
                            except:
                                pass
                        driver.get(list_page_url)
                        wait.until(EC.presence_of_element_located(
                            (By.XPATH, XPATH_ALL_ROWS_TABLE)
                        ))
                        i += 1
                        continue

                    if new_handle:
                        try:
                            WebDriverWait(driver, 15).until(
                                EC.url_contains("client-loan/view")
                            )
                            logger_func(f"  URL: {driver.current_url}")
                            time.sleep(2)

                            # вкладка "Списания"
                            logger_func("  Открываем вкладку 'Списания'...")
                            writeoffs_tab = wait.until(
                                EC.element_to_be_clickable((By.XPATH, XPATH_WRITEOFFS_TAB))
                            )
                            writeoffs_tab.click()
                            time.sleep(2)
                            logger_func("  На вкладке 'Списания'")

                            # кнопка "Новое списание"
                            try:
                                new_writeoff_btn = wait.until(
                                    EC.element_to_be_clickable((By.XPATH, XPATH_NEW_WRITEOFF_BUTTON))
                                )
                                logger_func("  Кнопка 'Новое списание' найдена")
                                new_writeoff_btn.click()
                                time.sleep(2)
                                logger_func("  Форма нового списания открыта")

                                add_button = wait.until(
                                    EC.element_to_be_clickable((By.XPATH, XPATH_ADD_BUTTON))
                                )
                                add_button.click()
                                time.sleep(2)
                                logger_func(f"  Списание добавлено ({contract_number})")
                                total_writeoffs_this_session += 1
                                
                                # Обновляем счётчик в StatusManager
                                sm.increment_processed("writeoffs")
                                
                                # ⏱️ ЗАДЕРЖКА 10 СЕКУНД ПОСЛЕ СПИСАНИЯ
                                logger_func("  ⏱️ Ждем 10 секунд перед переходом к следующему клиенту...")
                                time.sleep(10)

                            except TimeoutException:
                                logger_func("  Кнопка 'Новое списание' не найдена (возможно уже есть списание)")
                            except Exception as e_btn:
                                logger_func(f"  Ошибка при нажатии кнопки: {e_btn}")

                        except Exception as e_write:
                            logger_func(f"  Ошибка на странице клиента: {e_write}")
                            logger_func(traceback.format_exc())

                        finally:
                            # Закрываем вкладку договора
                            if driver.current_window_handle != main_handle and new_handle:
                                driver.close()

                            # Возвращаемся на главную вкладку
                            if main_handle in driver.window_handles:
                                driver.switch_to.window(main_handle)
                            elif driver.window_handles:
                                driver.switch_to.window(driver.window_handles[0])
                            else:
                                if stop_flag:
                                    stop_flag.set()
                                return

                            driver.get(list_page_url)
                            time.sleep(2)
                            wait.until(EC.presence_of_element_located(
                                (By.XPATH, XPATH_ALL_ROWS_TABLE)
                            ))

                    i += 1

                if stop_flag and stop_flag.is_set():
                    break

                logger_func(f"Страница {current_page_number} завершена.")

                # Пагинация
                try:
                    li_next = driver.find_elements(By.XPATH, XPATH_LI_NEXT_PAGINATION)
                    if not li_next:
                        logger_func("Пагинация не найдена. Конец.")
                        break

                    if "disabled" in li_next[0].get_attribute("class").split():
                        logger_func("Кнопка 'Далее' неактивна. Конец.")
                        break

                    try:
                        next_link = li_next[0].find_element(By.XPATH, ".//a")
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", next_link)
                        time.sleep(0.5)

                        next_clickable = wait.until(EC.element_to_be_clickable(next_link))
                        next_clickable.click()
                        current_page_number += 1

                        time.sleep(2)
                        wait.until(EC.presence_of_element_located(
                            (By.XPATH, XPATH_ALL_ROWS_TABLE)
                        ))

                    except Exception as e_next:
                        logger_func(f"Ошибка пагинации: {e_next}")
                        break

                except Exception as e_pag:
                    logger_func(f"Ошибка пагинации: {e_pag}")
                    break

            except Exception as e_page:
                logger_func(f"Ошибка на странице {current_page_number}: {e_page}")
                logger_func(traceback.format_exc())
                break

        logger_func(f"\nЗавершено. Списаний выполнено: {total_writeoffs_this_session}")
        
        # 📱 Уведомление об успешном завершении
        if TELEGRAM_AVAILABLE and is_bot_available():
            send_notification_sync(
                f"✅ <b>СПИСАНИЯ ЗАВЕРШЕНЫ</b>\n\n"
                f"💳 Выполнено списаний: <b>{total_writeoffs_this_session}</b>"
            )

    except Exception as e:
        error_msg = f"Глобальная ошибка: {e}"
        logger_func(error_msg)
        logger_func(traceback.format_exc())
        
        # Записываем ошибку в StatusManager
        sm.update_mode_status("writeoffs", last_error=error_msg)
        sm.add_log(error_msg)
        
        # 📱 Критическое уведомление
        if TELEGRAM_AVAILABLE and is_bot_available():
            send_notification_sync(
                f"🚨 <b>СПИСАНИЯ УПАЛИ</b>\n\n"
                f"❌ Критическая ошибка: {str(e)[:100]}\n\n"
                f"Проверьте логи программы"
            )

    finally:
        # Завершаем режим в StatusManager
        sm.update_mode_status("writeoffs", running=False)
        total = sm.get_status()["writeoffs"]["processed"]
        sm.add_log(f"Списания завершены. Обработано: {total}")
        
        if driver:
            logger_func("Закрытие браузера через 3 секунды...")
            time.sleep(3)
            driver.quit()
            logger_func("Браузер закрыт.")