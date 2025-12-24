# -*- coding: utf-8 -*-
"""
💳 Процессор отправки ссылок на оплату
Автоматическая отправка платёжных ссылок клиентам с возможностью ограничения количества
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
from process_manager import register_driver



# XPath константы
XPATH_USERNAME_FIELD = "//*[@id='managerloginform-phone']"
XPATH_PASSWORD_FIELD = "//*[@id='managerloginform-password']"
XPATH_LOGIN_BUTTON = "//*[@id='w0']/div[3]/button"
XPATH_ALL_ROWS_TABLE = "//*[@id='w2-container']/table/tbody/tr"
XPATH_LI_NEXT_PAGINATION = "//*[@id='w2']/ul/li[contains(@class,'next')]"
MAIN_PAGE_PART = "collector-debt/work"

# XPath для кнопок отправки ссылок
XPATH_PAYMENT_LINK_BUTTON = "/html/body/div[1]/div/div[2]/div[3]/div[1]/div[2]/div/div/div[1]/form/button"
XPATH_PAYMENT_OK_BUTTON = "/html/body/div[6]/div/div/div[3]/div/div/button[2]"


def load_cookies(driver, url, path="cookies.json"):
    """Загрузка cookies перед логином"""
    import json, os
    
    if not os.path.exists(path):
        return False

    try:
        driver.get(url)
        time.sleep(2)

        with open(path, "r", encoding="utf-8") as f:
            cookies = json.load(f)
            
        driver.delete_all_cookies()
        time.sleep(0.5)

        for cookie in cookies:
            # Selenium требует убрать ключи, которые мешают
            cookie.pop("sameSite", None)
            cookie.pop("expiry", None)
            try:
                driver.add_cookie(cookie)
            except:
                pass

        driver.refresh()
        time.sleep(2)
        print("Cookies загружены.")
        return True

    except Exception as e:
        print("Ошибка загрузки cookies:", e)
        return False


def save_cookies(driver, path="cookies.json"):
    """Сохранение cookies после логина"""
    import json
    try:
        cookies = driver.get_cookies()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print("Cookies сохранены")
    except Exception as e:
        print(f"Ошибка сохранения cookies: {e}")


def bot_login_function(driver, wait, login_url_param, username_param, password_param, logger_func_param):
    """Функция логина для бота"""
    logger_func_param(f"Переход на страницу входа: {login_url_param}")
    driver.get(login_url_param)
    try:
        logger_func_param("Ожидание поля для ввода логина (телефона)...")
        username_field = wait.until(EC.visibility_of_element_located((By.XPATH, XPATH_USERNAME_FIELD)))
        logger_func_param(f"Ввод логина (телефона): {username_param}")
        username_field.clear()
        username_field.send_keys(username_param)
        time.sleep(0.3)
        
        logger_func_param("Ожидание поля для ввода пароля...")
        password_field = wait.until(EC.visibility_of_element_located((By.XPATH, XPATH_PASSWORD_FIELD)))
        logger_func_param("Ввод пароля...")
        password_field.clear()
        password_field.send_keys(password_param)
        time.sleep(0.3)
        
        logger_func_param("Ожидание кнопки 'Войти'...")
        login_button_elem = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_LOGIN_BUTTON)))
        logger_func_param("Клик по кнопке 'Войти'...")
        login_button_elem.click()
        time.sleep(2)
        
        logger_func_param("Ожидание загрузки таблицы...")
        wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE)))
        logger_func_param("Таблица загружена.")
        
        save_cookies(driver)
        return True
        
    except Exception as login_error:
        logger_func_param(f"Ошибка логина: {login_error}")
        return False


def process_payment_links(login_url_proc, username_proc, password_proc, logger_func, stop_flag=None, 
                          use_delay_search=False, delay_from="", delay_to="", max_links=None):
    """
    Функция для отправки ссылок на оплату клиентам.
    
    Args:
        login_url_proc: URL для входа
        username_proc: Логин
        password_proc: Пароль
        logger_func: Функция для логирования
        stop_flag: Флаг остановки
        use_delay_search: Использовать фильтр по дням просрочки
        delay_from: Просрочка от (дней)
        delay_to: Просрочка до (дней)
        max_links: Максимальное количество ссылок для отправки (None = все)
    """
    
    logger_func("Запуск процесса отправки ссылок на оплату...")
    
    if max_links:
        logger_func(f"🎯 Установлен лимит: {max_links} ссылок")
    else:
        logger_func("♾️ Лимит ссылок не установлен (будут отправлены все)")

    driver = None
    total_links_sent_this_session = 0
    limit_reached = False

    try:
        # Headless Chrome
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        register_driver(driver)
        wait = WebDriverWait(driver, 20)
        logger_func("Браузер запущен (headless режим)")

        # ===================== ЗАГРУЗКА COOKIES =====================
        cookies_loaded = load_cookies(driver, login_url_proc)
        if cookies_loaded:
            logger_func("Cookies загружены. Пробуем войти без логина...")
        else:
            logger_func("Cookies отсутствуют — будет обычный логин.")

        # Заходим в аккаунт
        driver.get(login_url_proc)
        time.sleep(2)

        # Если куки есть, проверяем авторизацию
        if cookies_loaded:
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE)))
                logger_func("Авторизация по cookies успешна, логин не требуется.")
            except:
                logger_func("Cookies невалидны — выполняем обычный логин...")

                if stop_flag and stop_flag.is_set():
                    logger_func("Остановка перед логином.")
                    return

                if not bot_login_function(driver, wait, login_url_proc,
                                          username_proc, password_proc, logger_func):
                    logger_func("Не удалось войти на сайт.")
                    return

                logger_func("Логин по логину+паролю успешно выполнен.")
        else:
            # Выполняем обычный логин
            if stop_flag and stop_flag.is_set():
                logger_func("Остановка перед логином.")
                return

            if not bot_login_function(driver, wait, login_url_proc,
                                      username_proc, password_proc, logger_func):
                logger_func("Не удалось зайти на сайт.")
                return

            logger_func("Логин выполнен успешно.")

        logger_func("Пауза после логина...")
        time.sleep(2)

        if stop_flag and stop_flag.is_set():
            logger_func("Остановка после логина.")
            return

        # ===================== ФИЛЬТРАЦИЯ ПО ПРОСРОЧКЕ =====================
        if use_delay_search and (delay_from or delay_to):
            logger_func("Поиск по дням просрочки активирован.")
            try:
                xpath_delay_from = '//*[@id="collectordebtsearch-delayfrom"]'
                xpath_delay_to   = '//*[@id="collectordebtsearch-delayto"]'

                if delay_from:
                    try:
                        f = wait.until(EC.presence_of_element_located((By.XPATH, xpath_delay_from)))
                        f.clear(); f.send_keys(delay_from); time.sleep(0.5)
                        logger_func(f"Установлено 'от': {delay_from}")
                    except Exception as err:
                        logger_func(f"Не удалось установить 'от': {err}")

                if delay_to:
                    try:
                        f = wait.until(EC.presence_of_element_located((By.XPATH, xpath_delay_to)))
                        f.clear(); f.send_keys(delay_to); time.sleep(0.5)
                        logger_func(f"Установлено 'до': {delay_to}")
                    except Exception as err:
                        logger_func(f"Не удалось установить 'до': {err}")

                search_btn = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="w1"]/div[4]/div[1]/button[1]')
                ))
                search_btn.click()
                time.sleep(3)
                wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE)))

                logger_func("Поиск выполнен.")

            except Exception as err:
                logger_func(f"Ошибка поиска: {err}")

        else:
            logger_func("Поиск по дням просрочки отключен.")

        if stop_flag and stop_flag.is_set():
            logger_func("Остановка после фильтров.")
            return

        protocol_domain = login_url_proc.split('/')[0] + '//' + login_url_proc.split('/')[2]
        expected_list_url_base = f"{protocol_domain}/{MAIN_PAGE_PART}"

        if not driver.current_url.startswith(expected_list_url_base):
            logger_func("ВНИМАНИЕ: URL неожиданен:")
            logger_func(driver.current_url)
        else:
            logger_func("URL соответствует ожидаемому списку.")

        try:
            wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE)))
            logger_func("Таблица после логина загружена.")
        except Exception as err:
            logger_func(f"Таблица не найдена: {err}")
            return

        # ===================== ОСНОВНОЙ ЦИКЛ ПО СТРАНИЦАМ =====================
        current_page_number = 1

        while True:
            if stop_flag and stop_flag.is_set():
                logger_func("Остановка перед началом обработки страницы.")
                break

            logger_func(f"\n=== СТРАНИЦА {current_page_number}: отправка ссылок ===")

            # Проверяем таблицу
            try:
                wait.until(EC.visibility_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE)))
                time.sleep(1.5)
            except:
                logger_func(f"Таблица не загружена на странице {current_page_number}.")
                break

            all_rows = driver.find_elements(By.XPATH, XPATH_ALL_ROWS_TABLE)
            rows_count = len(all_rows)

            if rows_count == 0:
                logger_func("Строк нет — конец.")
                break

            logger_func(f"Строк найдено: {rows_count}")

            # ===================== ОПРЕДЕЛЕНИЕ ИНДЕКСА СТОЛБЦА ФИО =====================
            fio_col_index = None
            try:
                # Ищем заголовок таблицы
                header_row = driver.find_element(By.XPATH, "//*[@id='w2-container']/table/thead/tr")
                header_cells = header_row.find_elements(By.TAG_NAME, "th")
                
                for idx, cell in enumerate(header_cells, start=1):
                    cell_text = cell.text.strip().lower()
                    if "фио" in cell_text:
                        fio_col_index = idx
                        logger_func(f"Столбец ФИО найден: индекс {fio_col_index}")
                        break
                
                if not fio_col_index:
                    logger_func("ВНИМАНИЕ: Столбец ФИО не найден автоматически, используем индекс 4 по умолчанию")
                    fio_col_index = 4
                    
            except Exception as err:
                logger_func(f"Ошибка определения столбца ФИО: {err}, используем индекс 4 по умолчанию")
                fio_col_index = 4

            # ===================== ОБРАБОТКА СТРОК =====================
            for i in range(rows_count):
                if stop_flag and stop_flag.is_set():
                    logger_func("Остановка обработки строк.")
                    break

                logger_func(f"\n--- Клиент {i+1}/{rows_count} ---")

                # Получаем свежую строку
                try:
                    fresh_rows = wait.until(EC.presence_of_all_elements_located(
                        (By.XPATH, XPATH_ALL_ROWS_TABLE)
                    ))
                    if i >= len(fresh_rows):
                        logger_func("Количество строк изменилось.")
                        break
                    row = fresh_rows[i]
                except Exception as err:
                    logger_func(f"Ошибка при получении строки {i+1}: {err}")
                    continue

                # ===== ФИО (НЕ ЗАВИСИТ ОТ НОМЕРА СТОЛБЦА) =====
                try:
                    fio_cell = row.find_element(By.XPATH, f".//td[{fio_col_index}]")

                    try:
                        fio_link = fio_cell.find_element(By.XPATH, ".//a")
                        fio_text = fio_link.text.strip()
                    except:
                        fio_text = fio_cell.text.strip()

                    if not fio_text:
                        logger_func("ФИО пустое.")
                        continue

                    logger_func(f"ФИО клиента: {fio_text}")

                except Exception as err:
                    logger_func(f"Не удалось получить ФИО: {err}")
                    continue

                list_page_url = driver.current_url
                main_handle = driver.current_window_handle

                # ===== ОТКРЫТИЕ КАРТОЧКИ КЛИЕНТА =====
                try:
                    handles_before = driver.window_handles

                    if fio_link:
                        fio_link.click()
                    else:
                        driver.execute_script("arguments[0].click();", fio_cell)

                    WebDriverWait(driver, 10).until(
                        EC.number_of_windows_to_be(len(handles_before) + 1)
                    )

                    new_handle = [h for h in driver.window_handles if h != main_handle][0]
                    driver.switch_to.window(new_handle)
                    logger_func("Переключились на страницу клиента.")

                except Exception as err:
                    logger_func(f"Ошибка открытия вкладки: {err}")
                    driver.get(list_page_url)
                    continue


                # ===================== ОТПРАВКА ССЫЛКИ =====================
                try:
                    WebDriverWait(driver, 15).until(
                        EC.url_contains("collector-comment/view")
                    )
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)

                    payment_button = None
                    payment_xpaths = [
                        "/html/body/div[1]/div/div[2]/div[3]/div[1]/div[2]/div/div/div[1]/form/button",  # Точный XPath - первым!
                        "//button[contains(text(), 'Ссылка для оплаты')]",
                        "//a[contains(text(), 'Ссылка для оплаты')]"
                    ]

                    for xpath in payment_xpaths:
                        try:
                            payment_button = wait.until(
                                EC.element_to_be_clickable((By.XPATH, xpath))
                            )
                            break
                        except:
                            continue

                    if not payment_button:
                        logger_func("Кнопка отправки ссылки не найдена.")
                    else:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", payment_button)
                        time.sleep(0.5)
                        payment_button.click()
                        time.sleep(1.5)  # ⏱️ Пауза после клика!
                        logger_func("Кнопка отправки ссылки нажата.")

                        # Модальное окно
                        try:
                            logger_func("Ожидание модального окна...")
                            WebDriverWait(driver, 5).until(
                                EC.visibility_of_element_located(
                                    (By.XPATH, "//div[contains(@class, 'modal-content')]")
                                )
                            )
                            logger_func("✅ Модальное окно появилось!")

                            ok_button = None
                            ok_xpaths = [
                                "/html/body/div[6]/div/div/div[3]/div/div/button[2]",  # Точный XPath - первым!
                                "//button[contains(text(), 'Ok')]",
                                "//button[contains(@class, 'btn-warning')]",
                                "//div[@class='modal-footer']//button[contains(text(), 'Ok')]"
                            ]

                            for idx, xpath in enumerate(ok_xpaths):
                                try:
                                    ok_button = WebDriverWait(driver, 3).until(
                                        EC.element_to_be_clickable((By.XPATH, xpath))
                                    )
                                    logger_func(f"✅ Кнопка OK найдена по XPath #{idx+1}")
                                    break
                                except:
                                    logger_func(f"❌ Кнопка OK не найдена по XPath #{idx+1}")
                                    continue

                            if ok_button:
                                time.sleep(0.5)  # ⏱️ Пауза перед OK!
                                # Используем JavaScript клик для надежности
                                driver.execute_script("arguments[0].click();", ok_button)
                                time.sleep(0.5)  # Пауза после клика
                                logger_func(f"✅ Ссылка клиенту '{fio_text}' отправлена.")
                                total_links_sent_this_session += 1

                                # Проверка лимита
                                if max_links and total_links_sent_this_session >= max_links:
                                    logger_func(f"🎯 Достигнут лимит: {max_links} ссылок. Завершение.")
                                    limit_reached = True
                                    break
                            else:
                                logger_func("Кнопка ОК не найдена.")

                        except TimeoutException:
                            logger_func("❌ Модальное окно не появилось.")
                            total_links_sent_this_session += 1

                except Exception as err:
                    logger_func(f"Ошибка отправки ссылки: {err}")
                    logger_func(traceback.format_exc())

                # ===================== ВОЗВРАТ НА ОСНОВНУЮ ВКЛАДКУ =====================
                finally:
                    driver.close()
                    driver.switch_to.window(main_handle)
                    driver.get(list_page_url)
                    time.sleep(2)
                    wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE)))

            # Проверка флага лимита после обработки строк
            if limit_reached:
                logger_func("Выход из цикла страниц - лимит достигнут.")
                break

            # ===================== ПАГИНАЦИЯ =====================
            logger_func(f"Переход к следующей странице...")

            try:
                li_next = driver.find_elements(By.XPATH, XPATH_LI_NEXT_PAGINATION)
                if not li_next:
                    logger_func("Пагинация не найдена. Конец.")
                    break

                if "disabled" in li_next[0].get_attribute("class").split():
                    logger_func("Кнопка 'Далее' выключена. Конец.")
                    break

                next_btn = li_next[0].find_element(By.XPATH, ".//a")
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", next_btn)
                time.sleep(0.5)
                next_btn.click()
                current_page_number += 1
                
                # Проверка флага лимита
                if limit_reached:
                    logger_func("Выход из цикла страниц - лимит достигнут.")
                    break

                time.sleep(2)
                wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_ROWS_TABLE)))
                time.sleep(1.5)

            except Exception as err_page:
                logger_func(f"Ошибка пагинации: {err_page}")
                break

        # ===================== ИТОГИ =====================
        logger_func("=" * 60)
        logger_func(f"Всего отправлено ссылок: {total_links_sent_this_session}")
        logger_func("=" * 60)

    except Exception as global_err:
        logger_func(f"Глобальная ошибка: {global_err}")
        logger_func(traceback.format_exc())

    finally:
        if driver:
            try:
                driver.quit()
                logger_func("Браузер закрыт.")
            except:
                pass