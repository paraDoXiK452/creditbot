#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Модуль онлайн-статистики для Max.Credit
Отслеживает оплаты, изменения количества клиентов и отправляет уведомления в Telegram
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Set
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Импортируем telegram_manager для отправки уведомлений
try:
    from telegram_manager import send_notification_async, is_bot_available
    TELEGRAM_AVAILABLE = True
    print("✅ telegram_manager доступен для online_statistics")
except ImportError:
    print("⚠️ telegram_manager не найден, уведомления отключены")
    TELEGRAM_AVAILABLE = False
    async def send_notification_async(msg): 
        pass
    def is_bot_available(): 
        return False

# Импортируем process_manager для регистрации браузеров
try:
    from process_manager import register_driver
    PROCESS_MANAGER_AVAILABLE = True
except ImportError:
    PROCESS_MANAGER_AVAILABLE = False
    def register_driver(driver): 
        pass

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class OnlineStatistics:
    """Класс для отслеживания онлайн-статистики Max.Credit"""
    
    def __init__(self, url: str, phone: str, password: str):
        """
        Инициализация модуля статистики
        
        Args:
            url: URL авторизации Max.Credit
            phone: Телефон для входа
            password: Пароль
        """
        self.url = url
        self.phone = phone
        self.password = password
        # telegram_bot больше не нужен - используется telegram_manager
        self.driver = None
        self.is_running = False
        self.update_interval = 60  # Обновление раз в минуту
        
        # Извлекаем базовый URL (домен) из url для правильной навигации
        # Например: https://www.max.credit/manager/site/login → https://www.max.credit
        # Или: https://svoi-ludi.ru/manager/site/login → https://svoi-ludi.ru
        from urllib.parse import urlparse
        parsed = urlparse(url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        logger.info(f"📍 Базовый URL: {self.base_url}")
        
        # Пути к файлам данных
        self.data_dir = Path.home() / ".maxcredit_stats"
        self.data_dir.mkdir(exist_ok=True)
        self.clients_file = self.data_dir / "clients.json"
        self.stats_file = self.data_dir / "stats.json"
        
        # XPath элементы - АВТОРИЗАЦИЯ
        self.XPATH_USERNAME = "//*[@id='managerloginform-phone']"
        self.XPATH_PASSWORD = "//*[@id='managerloginform-password']"
        self.XPATH_LOGIN_BTN = "//*[@id='w0']/div[3]/button"
        
        # XPath элементы - КЛИЕНТЫ
        self.XPATH_PER_PAGE_SELECT = "/html/body/div[1]/div/div[2]/form/div[4]/div[2]/select"
        self.XPATH_SEARCH_BTN = "/html/body/div[1]/div/div[2]/form/div[4]/div[1]/button[1]"
        self.XPATH_CLIENTS_ROWS = "/html/body/div[1]/div/div[2]/div[2]/div/div[1]/table/tbody/tr"
        self.XPATH_CLIENT_FIO = "td[3]/a"  # Относительно строки
        
        # XPath элементы - ОПЛАТЫ
        self.XPATH_PAYMENT_TAB = "/html/body/div[1]/div/div[2]/ul[1]/li[4]/a"
        self.XPATH_PAYMENT_DATE_INPUT = "/html/body/div[1]/div/div[2]/form/div[1]/div[1]/div/div[1]/div/input[1]"
        self.XPATH_PAYMENT_SEARCH_BTN = "/html/body/div[1]/div/div[2]/form/div[2]/button[1]"
        self.XPATH_PAYMENTS_ROWS = "/html/body/div[1]/div/div[2]/div[2]/div[1]/table/tbody/tr"
        # Индексы столбцов определяются динамически по заголовкам таблицы
        
        
        # XPath элементы - ПРОДЛЕНИЯ
        self.XPATH_EXTENSIONS_TAB = "/html/body/div[1]/div/div[2]/ul/li[5]/a"
        self.XPATH_EXTENSIONS_DATE_INPUT = "/html/body/div[1]/div/div[2]/form/div[1]/div[1]/div/div[1]/div/input[1]"
        self.XPATH_EXTENSIONS_COUNT = "/html/body/div[1]/div/div[2]/div[2]/div[2]/b[2]"
        
        self.MAIN_PAGE_PART = "collector-debt/work"
        
        # Текущие данные
        self.current_clients: Dict[str, Dict] = {}  # {fio: {data}}
        self.current_sbor: float = 0.0
        self.current_premium: Dict[str, float] = {'sbor_premium': 0.0, 'extensions_premium': 0.0, 'extensions_count': 0, 'total_premium': 0.0}  # Премия за месяц
        
        # Импортируем status_manager
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from status_manager import get_status_manager
            self.status_manager = get_status_manager()
        except Exception as e:
            logger.warning(f"Status manager недоступен: {e}")
            self.status_manager = None
        
        logger.info("📊 Модуль онлайн-статистики инициализирован")
    
    def init_driver(self) -> bool:
        """Инициализация браузера в headless режиме"""
        try:
            import platform
            
            service = Service(ChromeDriverManager().install())
            options = Options()
            
            # Определяем путь к Chrome в зависимости от ОС
            system = platform.system()
            if system == "Linux":
                options.binary_location = "/usr/bin/google-chrome"
            # На Windows ChromeDriver сам найдёт Chrome, не указываем путь
            
            options.add_argument("--headless")  # Скрытый режим
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            
            self.driver = webdriver.Chrome(service=service, options=options)
            register_driver(self.driver)  # Регистрируем браузер для автозакрытия
            logger.info("✅ Браузер инициализирован в headless режиме")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации браузера: {e}")
            return False
    
    def login(self) -> bool:
        """Вход в систему"""
        try:
            logger.info(f"🔐 Вход в систему...")
            self.driver.get(self.url)
            
            wait = WebDriverWait(self.driver, 20)
            
            # Ввод телефона
            username_field = wait.until(EC.visibility_of_element_located((By.XPATH, self.XPATH_USERNAME)))
            username_field.clear()
            username_field.send_keys(self.phone)
            time.sleep(0.3)
            
            # Ввод пароля
            password_field = wait.until(EC.visibility_of_element_located((By.XPATH, self.XPATH_PASSWORD)))
            password_field.clear()
            password_field.send_keys(self.password)
            time.sleep(0.3)
            
            # Нажатие ВОЙТИ
            login_button = wait.until(EC.element_to_be_clickable((By.XPATH, self.XPATH_LOGIN_BTN)))
            login_button.click()
            
            # Ожидание загрузки главной страницы
            WebDriverWait(self.driver, 30).until(EC.url_contains(self.MAIN_PAGE_PART))
            
            logger.info("✅ Успешный вход в систему")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка входа: {e}")
            return False
    
    def get_clients_list(self) -> Dict[str, Dict]:
        """
        Получение списка клиентов
        Автоматически определяет столбец ФИО по заголовку таблицы
        """
        try:
            wait = WebDriverWait(self.driver, 15)

            # Выбираем 1000 записей на странице
            logger.info("📋 Выбираем 1000 записей на странице...")
            select_element = wait.until(EC.presence_of_element_located((By.XPATH, self.XPATH_PER_PAGE_SELECT)))
            select = Select(select_element)
            select.select_by_value("1000")
            time.sleep(1)

            # Нажимаем кнопку "Поиск"
            search_btn = wait.until(EC.element_to_be_clickable((By.XPATH, self.XPATH_SEARCH_BTN)))
            search_btn.click()
            time.sleep(3)

            clients = {}

            # --- 1. Определяем индексы столбцов ФИО и Просрочка ---
            logger.info("🔍 Определяем столбцы ФИО и Просрочка...")
            headers = self.driver.find_elements(By.XPATH, "//table/thead/tr/th")
            fio_col_index = None
            prosrochka_col_index = None

            for i, th in enumerate(headers, start=1):
                header_text = th.text.strip()
                header_text_lower = header_text.lower()
                
                if "фио" in header_text_lower or "фамилия" in header_text_lower:
                    fio_col_index = i
                    logger.info(f"✅ Столбец ФИО найден: {i} ({header_text})")
                
                # ТОЧНОЕ совпадение "Дни" (с заглавной!) чтобы не найти "сотруДНик"
                if header_text == "Дни" or "просрочка" in header_text_lower:
                    prosrochka_col_index = i
                    logger.info(f"✅ Столбец Просрочка/Дни найден: {i} ({header_text})")

            if fio_col_index is None:
                logger.error("❌ Не удалось определить столбец ФИО")
                return {}

            logger.info(f"✅ Столбцы найдены - ФИО: {fio_col_index}, Просрочка: {prosrochka_col_index}")

            # --- 2. Читаем строки таблицы ---
            rows = self.driver.find_elements(By.XPATH, self.XPATH_CLIENTS_ROWS)
            logger.info(f"📊 Найдено {len(rows)} клиентов")

            for idx, row in enumerate(rows, 1):
                try:
                    fio_cell = row.find_element(By.XPATH, f"td[{fio_col_index}]")
                    fio = fio_cell.text.strip()

                    if fio:
                        client_data = {
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        # Пытаемся получить день просрочки
                        if prosrochka_col_index:
                            try:
                                prosrochka_cell = row.find_element(By.XPATH, f"td[{prosrochka_col_index}]")
                                prosrochka = prosrochka_cell.text.strip()
                                if prosrochka:
                                    client_data["prosrochka"] = prosrochka
                            except:
                                pass  # Если не удалось получить - не критично
                        
                        clients[fio] = client_data

                except Exception as e:
                    logger.warning(f"⚠️ Ошибка обработки строки клиента {idx}: {e}")
                    continue

            logger.info(f"✅ Получен список из {len(clients)} клиентов")
            return clients

        except Exception as e:
            logger.error(f"❌ Ошибка получения списка клиентов: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}

    
    def get_payments_info(self) -> List[Dict]:
        """
        Получение информации об оплатах
        
        Returns:
            Список словарей с данными оплат
        """
        try:
            wait = WebDriverWait(self.driver, 15)
            
            # Переход на вкладку "Оплаты"
            logger.info("💰 Переход на вкладку оплат...")
            payment_tab = wait.until(EC.element_to_be_clickable((By.XPATH, self.XPATH_PAYMENT_TAB)))
            payment_tab.click()
            time.sleep(2)
            
            # Устанавливаем дату "от 1 числа текущего месяца"
            try:
                logger.info("📅 Устанавливаем дату от 1 числа текущего месяца...")
                date_input = wait.until(EC.presence_of_element_located((By.XPATH, self.XPATH_PAYMENT_DATE_INPUT)))
                
                # Формируем дату: 01.MM.YYYY
                from datetime import datetime
                first_day = datetime.now().replace(day=1).strftime("%d.%m.%Y")
                
                # Очищаем через JavaScript и вводим дату
                self.driver.execute_script("arguments[0].value = '';", date_input)
                time.sleep(0.3)
                date_input.send_keys(first_day)
                time.sleep(0.5)
                
                # ВАЖНО: Закрываем календарь кликом по body
                self.driver.find_element(By.TAG_NAME, "body").click()
                time.sleep(0.5)
                
                # Теперь кнопка поиска
                search_btn = wait.until(EC.element_to_be_clickable((By.XPATH, self.XPATH_PAYMENT_SEARCH_BTN)))
                search_btn.click()
                
                # ВАЖНО: Ждём появления таблицы оплат
                logger.info("⏳ Ожидание загрузки таблицы оплат...")
                try:
                    # Ждём до 10 секунд появления заголовков таблицы
                    wait.until(EC.presence_of_element_located((By.XPATH, "//div[@id='w1']//table/thead/tr/th")))
                    time.sleep(1)  # Дополнительная пауза для стабилизации
                    logger.info("✅ Таблица оплат загружена")
                except TimeoutException:
                    logger.warning("⚠️ Таймаут загрузки таблицы оплат, пробуем продолжить...")
                    time.sleep(2)
                
                logger.info(f"✅ Дата установлена: {first_day}")
                
            except Exception as e:
                logger.warning(f"⚠️ Не удалось установить дату: {e}")
            
            # Получаем список оплат
            payments = []
            
            # --- 1. Определяем индексы столбцов по заголовкам ---
            logger.info("🔍 Определяем столбцы таблицы оплат...")
            
            # Ищем заголовки в текущей вкладке оплат
            headers = self.driver.find_elements(By.XPATH, "//div[@id='w1']//table/thead/tr/th")
            
            # Если не нашли по первому xpath, попробуем более общий
            if not headers:
                headers = self.driver.find_elements(By.XPATH, "//table/thead/tr/th")
            
            fio_col_index = None
            summa_col_index = None
            date_col_index = None
            
            for i, th in enumerate(headers, start=1):
                header_text = th.text.strip()
                header_text_lower = header_text.lower()
                
                # Ищем столбец ФИО
                if "фио" in header_text_lower or "фамилия" in header_text_lower:
                    fio_col_index = i
                    logger.info(f"✅ Столбец ФИО найден: {i} ({header_text})")
                
                # Ищем столбец "Сумма оплаты"
                if "сумма оплаты" in header_text_lower or ("оплат" in header_text_lower and "сумма" in header_text_lower):
                    summa_col_index = i
                    logger.info(f"✅ Столбец Сумма оплаты найден: {i} ({header_text})")
                
                # Ищем столбец "Просрочка" (дни просрочки, не дату!)
                if "просрочка" in header_text_lower:
                    date_col_index = i
                    logger.info(f"✅ Столбец Просрочка найден: {i} ({header_text})")
            
            # Проверяем, что нашли все необходимые столбцы
            if not all([fio_col_index, summa_col_index, date_col_index]):
                logger.error(f"❌ Не удалось определить столбцы таблицы оплат")
                logger.error(f"   ФИО: {fio_col_index}, Сумма: {summa_col_index}, Дата: {date_col_index}")
                logger.error(f"   Найденные заголовки: {[th.text.strip() for th in headers]}")
                return []
            
            # --- 2. Читаем строки таблицы оплат ---
            
            # Находим строки таблицы оплат
            rows = self.driver.find_elements(By.XPATH, self.XPATH_PAYMENTS_ROWS)
            logger.info(f"💳 Найдено {len(rows)} записей оплат")
            
            # Берём только первые 10 оплат
            for idx, row in enumerate(rows[:10], 1):
                try:
                    # Получаем данные из ячеек используя динамические индексы
                    summa_elem = row.find_element(By.XPATH, f"td[{summa_col_index}]")
                    fio_elem = row.find_element(By.XPATH, f"td[{fio_col_index}]")
                    date_elem = row.find_element(By.XPATH, f"td[{date_col_index}]")
                    
                    payment = {
                        "summa": summa_elem.text.strip(),
                        "fio": fio_elem.text.strip(),
                        "prosrochka_dni": date_elem.text.strip(),  # Дни просрочки (не дата!)
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    payments.append(payment)
                    logger.debug(f"Оплата {idx}: {payment}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка обработки строки оплаты {idx}: {e}")
                    continue
            
            logger.info(f"✅ Получено {len(payments)} оплат")
            return payments
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения оплат: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def get_extensions_count(self) -> int:
        """
        Получение количества продлений за текущий месяц
        С retry механизмом для стабильности
        
        Returns:
            int: Количество продлений
        """
        # RETRY МЕХАНИЗМ: 3 попытки с паузой между ними
        for attempt in range(3):
            try:
                wait = WebDriverWait(self.driver, 20)  # Увеличили таймаут до 20 секунд
                
                # Переходим на вкладку "Продления"
                logger.info(f"🔄 Переход на вкладку продлений (попытка {attempt + 1}/3)...")
                extensions_tab = wait.until(EC.element_to_be_clickable((By.XPATH, self.XPATH_EXTENSIONS_TAB)))
                extensions_tab.click()
                time.sleep(2)
                
                # Устанавливаем дату от 1 числа текущего месяца
                logger.info("📅 Устанавливаем дату от 1 числа месяца для продлений...")
                
                # Получаем первое число текущего месяца
                from datetime import datetime
                first_day = datetime.now().replace(day=1).strftime("%d.%m.%Y")
                
                # ИСПОЛЬЗУЕМ РАБОЧИЙ МЕТОД установки даты
                date_input = wait.until(EC.presence_of_element_located((By.XPATH, self.XPATH_EXTENSIONS_DATE_INPUT)))
                
                # Очищаем через JavaScript
                self.driver.execute_script("arguments[0].value = '';", date_input)
                time.sleep(0.3)
                date_input.send_keys(first_day)
                time.sleep(0.5)
                
                # Закрываем календарь
                self.driver.find_element(By.TAG_NAME, "body").click()
                time.sleep(0.5)
                
                # Нажимаем поиск (или просто ждём автообновления)
                try:
                    search_btn = self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div[2]/form/div[2]/button[1]")
                    search_btn.click()
                    time.sleep(3)
                except:
                    time.sleep(3)
                
                logger.info(f"✅ Дата установлена для продлений: {first_day}")
                
                # Получаем количество продлений
                count_element = wait.until(EC.presence_of_element_located((By.XPATH, self.XPATH_EXTENSIONS_COUNT)))
                count_text = count_element.text.strip()
                
                # Парсим число
                count_text = count_text.replace(' ', '').replace('\xa0', '')
                extensions_count = int(count_text)
                
                logger.info(f"📊 Количество продлений: {extensions_count}")
                return extensions_count
                
            except Exception as e:
                logger.warning(f"⚠️ Попытка {attempt + 1}/3 не удалась: {e}")
                if attempt < 2:
                    logger.info("⏳ Пауза 5 секунд перед повтором...")
                    time.sleep(5)
                else:
                    logger.error(f"❌ Все попытки исчерпаны при получении количества продлений")
                    import traceback
                    logger.error(traceback.format_exc())
                    return 0
        
        # На всякий случай (не должно сюда дойти)
        return 0
    
    def calculate_extensions_premium(self, count: int) -> float:
        """
        Расчёт премии по продлениям
        
        Градация:
        - 0-199: 100₽/продление
        - 200-249: 200₽/продление
        - 250-299: 250₽/продление
        - 300+: 300₽/продление
        
        Args:
            count: Количество продлений
        
        Returns:
            float: Премия в рублях
        """
        if count < 200:
            rate = 100
        elif count < 250:
            rate = 200
        elif count < 300:
            rate = 250
        else:
            rate = 300
        
        premium = count * rate
        logger.info(f"💰 Премия по продлениям: {count} × {rate}₽ = {premium:,.2f}₽")
        return premium
    
    def calculate_monthly_premium(self) -> Dict[str, float]:
        """
        Расчёт премии за месяц (по сбору И по продлениям)
        
        Returns:
            Dict: {
                'sbor_premium': float,      # Премия по сбору
                'extensions_premium': float, # Премия по продлениям  
                'extensions_count': int,     # Количество продлений
                'total_premium': float       # Общая премия
            }
        """
        try:
            wait = WebDriverWait(self.driver, 15)
            
            # ========== ПРЕМИЯ ПО СБОРУ (старый код) ==========
            logger.info("💰 Переход на вкладку оплат для подсчета премии...")
            payment_tab = wait.until(EC.element_to_be_clickable((By.XPATH, self.XPATH_PAYMENT_TAB)))
            payment_tab.click()
            time.sleep(2)
            
            # Устанавливаем дату от 1 числа месяца
            logger.info("📅 Устанавливаем дату от 1 числа месяца для премии...")
            
            from datetime import datetime
            first_day = datetime.now().replace(day=1).strftime("%d.%m.%Y")
            
            
            date_input = wait.until(EC.presence_of_element_located((By.XPATH, self.XPATH_PAYMENT_DATE_INPUT)))
            
            # Очищаем через JavaScript (рабочий код из get_payments_info)
            self.driver.execute_script("arguments[0].value = '';", date_input)
            time.sleep(0.3)
            date_input.send_keys(first_day)
            time.sleep(0.5)
            
            # ВАЖНО: Закрываем календарь кликом по body
            self.driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(0.5)
            
            # Теперь кнопка поиска
            search_btn = wait.until(EC.element_to_be_clickable((By.XPATH, self.XPATH_PAYMENT_SEARCH_BTN)))
            search_btn.click()
            time.sleep(2)
            
            logger.info(f"✅ Дата установлена для премии: {first_day}")
            
            # Определяем столбцы
            try:
                headers = self.driver.find_elements(By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div[1]/table/thead/tr/th")
                prosrochka_col = None
                summa_col = None
                
                for i, header in enumerate(headers, 1):
                    header_text = header.text.lower().strip()
                    if "просрочка" in header_text:
                        prosrochka_col = i
                        logger.info(f"✅ Столбец Просрочка найден: {i}")
                    
                    if "сумма оплаты" in header_text or ("сумма" in header_text and "оплат" in header_text):
                        summa_col = i
                        logger.info(f"✅ Столбец Сумма оплаты найден: {i}")
                
                if not prosrochka_col or not summa_col:
                    logger.error(f"❌ Не удалось определить столбцы для премии")
                    return {'sbor_premium': 0.0, 'extensions_premium': 0.0, 'extensions_count': 0, 'total_premium': 0.0}
            
            except Exception as e:
                logger.error(f"❌ Ошибка определения столбцов: {e}")
                return {'sbor_premium': 0.0, 'extensions_premium': 0.0, 'extensions_count': 0, 'total_premium': 0.0}
            
            # Собираем оплаты со всех страниц
            total_premium_sbor = 0.0
            page = 1
            
            while True:
                try:
                    logger.info(f"📄 Обрабатываю страницу {page}...")
                    rows = self.driver.find_elements(By.XPATH, self.XPATH_PAYMENTS_ROWS)
                    logger.info(f"💳 Найдено {len(rows)} оплат на странице {page}")
                    
                    if not rows:
                        logger.info("📄 Это последняя страница оплат")
                        break
                    
                    for row in rows:
                        try:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            
                            # ЗАЩИТА ОТ ФУТЕРА: Проверяем что в строке достаточно ячеек
                            if len(cells) < max(prosrochka_col, summa_col):
                                logger.debug(f"⏭️ Пропускаю строку с {len(cells)} ячейками (ожидалось минимум {max(prosrochka_col, summa_col)})")
                                continue
                            
                            prosrochka_text = cells[prosrochka_col - 1].text.strip()
                            summa_text = cells[summa_col - 1].text.strip()
                            
                            # Парсим просрочку
                            prosrochka_days = int(''.join(filter(str.isdigit, prosrochka_text))) if prosrochka_text else 0
                            
                            # Парсим сумму
                            summa_clean = summa_text.replace(' ', '').replace(',', '.').replace('\xa0', '')
                            summa_clean = summa_clean.replace('руб', '').replace('₽', '').replace('р', '').strip()
                            summa = float(summa_clean)
                            
                            # Считаем премию по градации:
                            # 3-29 дней просрочки: 1% от суммы
                            # 30+ дней просрочки: 5% от суммы
                            if 3 <= prosrochka_days <= 29:
                                premium = summa * 0.01
                                total_premium_sbor += premium
                            elif prosrochka_days >= 30:
                                premium = summa * 0.05
                                total_premium_sbor += premium
                        
                        except Exception as e:
                            logger.warning(f"⚠️ Ошибка обработки строки: {e}")
                            continue
                    
                    # Переход на следующую страницу
                    try:
                        next_button = self.driver.find_element(By.XPATH, "//li[contains(@class,'next')]/a")
                        
                        if 'disabled' in next_button.get_attribute('class'):
                            logger.info("📄 Это последняя страница оплат")
                            break
                        
                        logger.info("➡️ Переход на следующую страницу...")
                        next_button.click()
                        time.sleep(3)
                        page += 1
                        
                    except Exception:
                        logger.info("📄 Это последняя страница оплат")
                        break
                
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки страницы {page}: {e}")
                    break
            
            # ========== ПРЕМИЯ ПО ПРОДЛЕНИЯМ (новый код) ==========
            extensions_count = self.get_extensions_count()
            extensions_premium = self.calculate_extensions_premium(extensions_count)
            
            # Общая премия
            total_premium = total_premium_sbor + extensions_premium
            
            logger.info(f"✅ ПРЕМИЯ ЗА МЕСЯЦ:")
            logger.info(f"   💰 По сбору: {total_premium_sbor:,.2f} руб")
            logger.info(f"   🔄 По продлениям: {extensions_premium:,.2f} руб ({extensions_count} шт)")
            logger.info(f"   💵 ИТОГО: {total_premium:,.2f} руб")
            
            return {
                'sbor_premium': total_premium_sbor,
                'extensions_premium': extensions_premium,
                'extensions_count': extensions_count,
                'total_premium': total_premium
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчёта премии: {e}")
            return {'sbor_premium': 0.0, 'extensions_premium': 0.0, 'extensions_count': 0, 'total_premium': 0.0}
    
    def get_total_sbor(self) -> float:
        """
        Получение общей суммы сбора из footer таблицы оплат
        Динамически определяет столбец "Сумма оплаты"
        
        Returns:
            Сумма сбора
        """
        try:
            wait = WebDriverWait(self.driver, 10)
            
            # --- 1. Определяем индекс столбца "Сумма оплаты" ---
            logger.info("🔍 Определяем столбец Сумма оплаты для footer...")
            
            # Ищем заголовки таблицы оплат
            headers = self.driver.find_elements(By.XPATH, "//div[@id='w1']//table/thead/tr/th")
            if not headers:
                headers = self.driver.find_elements(By.XPATH, "//table/thead/tr/th")
            
            summa_col_index = None
            for i, th in enumerate(headers, start=1):
                header_text = th.text.strip().lower()
                if "сумма оплаты" in header_text or ("оплат" in header_text and "сумма" in header_text):
                    summa_col_index = i
                    logger.info(f"✅ Столбец Сумма оплаты найден: {i}")
                    break
            
            if not summa_col_index:
                logger.error("❌ Не удалось определить столбец Сумма оплаты")
                return 0.0
            
            # --- 2. Получаем значение из footer ---
            sbor_xpath = f"//table/tfoot/tr/td[{summa_col_index}]"
            sbor_element = wait.until(EC.presence_of_element_located((By.XPATH, sbor_xpath)))
            sbor_text = sbor_element.text.strip()
            
            logger.info(f"💰 Текст суммы сбора: '{sbor_text}'")
            
            # Проверяем на специальные значения
            if not sbor_text or sbor_text in ["(незадано)", "(не задано)", "-", "—", "N/A"]:
                logger.warning(f"⚠️ Сбор не указан или равен нулю: '{sbor_text}'")
                return 0.0
            
            # Убираем все пробелы, заменяем запятую на точку
            sbor_text = sbor_text.replace(' ', '').replace(',', '.').replace('\xa0', '')
            
            # Убираем валюту и другие символы
            sbor_text = sbor_text.replace('руб', '').replace('₽', '').replace('р', '').strip()
            
            # Убираем точки, которые используются как разделители тысяч
            # Находим последнюю точку (это десятичный разделитель)
            parts = sbor_text.split('.')
            if len(parts) > 2:
                # Если точек больше одной, склеиваем все кроме последней части
                sbor_clean = ''.join(parts[:-1]) + '.' + parts[-1]
            else:
                sbor_clean = sbor_text
            
            # Проверяем, что остались только цифры и одна точка
            if not sbor_clean or not any(c.isdigit() for c in sbor_clean):
                logger.warning(f"⚠️ Не удалось извлечь число из: '{sbor_text}'")
                return 0.0
            
            try:
                sbor = float(sbor_clean)
                logger.info(f"💰 Общий сбор: {sbor:,.2f} руб")
                return sbor
            except ValueError:
                logger.warning(f"⚠️ Не удалось преобразовать в число: '{sbor_clean}'")
                return 0.0
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения сбора: {e}")
            return 0.0
    
    def load_previous_data(self):
        """Загрузка предыдущих данных из файлов"""
        try:
            if self.clients_file.exists():
                with open(self.clients_file, 'r', encoding='utf-8') as f:
                    self.current_clients = json.load(f)
                logger.info(f"📂 Загружено {len(self.current_clients)} клиентов из файла")
            
            if self.stats_file.exists():
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                    self.current_sbor = stats.get('sbor', 0.0)
                    loaded_premium = stats.get('premium', {'sbor_premium': 0.0, 'extensions_premium': 0.0, 'extensions_count': 0, 'total_premium': 0.0})
                    # Совместимость со старым форматом (float)
                    if isinstance(loaded_premium, float):
                        loaded_premium = {'sbor_premium': loaded_premium, 'extensions_premium': 0.0, 'extensions_count': 0, 'total_premium': loaded_premium}
                    self.current_premium = loaded_premium
                logger.info(f"📂 Загружен предыдущий сбор: {self.current_sbor:,.2f} руб")
                logger.info(f"📂 Загружена предыдущая премия: {self.current_premium.get('total_premium', 0.0):,.2f} руб")
                
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки предыдущих данных: {e}")
    
    def save_current_data(self, clients: Dict, sbor: float, premium: Dict[str, float] = None):
        """Сохранение текущих данных в файлы"""
        try:
            # Сохраняем клиентов
            with open(self.clients_file, 'w', encoding='utf-8') as f:
                json.dump(clients, f, ensure_ascii=False, indent=2)
            
            # Сохраняем статистику
            if premium is None:
                premium = {'sbor_premium': 0.0, 'extensions_premium': 0.0, 'extensions_count': 0, 'total_premium': 0.0}
            stats = {
                'sbor': sbor,
                'premium': premium,
                'clients_count': len(clients),
                'timestamp': datetime.now().isoformat()
            }
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            logger.info("💾 Данные сохранены")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения данных: {e}")
    
    async def compare_and_notify(self, new_clients: Dict, new_sbor: float, payments: List[Dict]):
        """
        Сравнение данных и отправка уведомлений
        
        Args:
            new_clients: Новый список клиентов {fio: {timestamp, prosrochka}}
            new_sbor: Новая сумма сбора
            payments: Список последних оплат (может быть устаревшим!)
        """
        try:
            # ==================== ПРОВЕРКА ОПЛАТ ====================
            if new_sbor > self.current_sbor:
                delta = new_sbor - self.current_sbor
                logger.info(f"💰 ОПЛАТА! Сбор увеличился на {delta:,.2f} руб")
                
                # ВАЖНО: Запрашиваем СВЕЖИЙ список оплат!
                logger.info("🔄 Запрашиваю свежий список оплат...")
                fresh_payments = self.get_payments_info()
                
                if fresh_payments:
                    # Пытаемся найти ВСЕ новые оплаты
                    # Логика: если прирост больше суммы первой оплаты - было несколько оплат
                    new_payments_list = []
                    accumulated_sum = 0.0
                    
                    for payment in fresh_payments:
                        try:
                            # Парсим сумму оплаты
                            summa_text = payment['summa'].replace(' ', '').replace(',', '.').replace('\xa0', '')
                            summa_text = summa_text.replace('руб', '').replace('₽', '').replace('р', '').strip()
                            summa = float(summa_text)
                            
                            if accumulated_sum < delta:
                                new_payments_list.append({
                                    'fio': payment['fio'],
                                    'summa': summa,
                                    'summa_text': payment['summa'],
                                    'prosrochka_dni': payment['prosrochka_dni']
                                })
                                accumulated_sum += summa
                                
                                # Если накопили примерно столько же сколько прирост - стоп
                                if abs(accumulated_sum - delta) < 1.0:  # Погрешность 1 рубль
                                    break
                        except:
                            continue
                    
                    # Формируем уведомление
                    if len(new_payments_list) == 1:
                        # Одна оплата
                        payment = new_payments_list[0]
                        message = (
                            f"💰 <b>ОПЛАТА!</b>\n\n"
                            f"Сумма: <b>{payment['summa_text']} руб</b>\n"
                            f"Клиент: <b>{payment['fio']}</b>\n"
                            f"Просрочка: {payment['prosrochka_dni']} дн\n"
                            f"Общий сбор: <b>{new_sbor:,.2f} руб</b>\n"
                            f"Прирост: +{delta:,.2f} руб"
                        )
                        logger.info(f"✅ Оплата от клиента: {payment['fio']}, сумма: {payment['summa_text']}")
                    else:
                        # Несколько оплат!
                        message = f"💰 <b>НЕСКОЛЬКО ОПЛАТ!</b>\n\n"
                        message += f"Количество: <b>{len(new_payments_list)}</b>\n\n"
                        
                        for i, payment in enumerate(new_payments_list, 1):
                            message += f"{i}. <b>{payment['fio']}</b>\n"
                            message += f"   Сумма: {payment['summa_text']} руб\n"
                            message += f"   Просрочка: {payment['prosrochka_dni']} дн\n\n"
                        
                        message += f"Общий сбор: <b>{new_sbor:,.2f} руб</b>\n"
                        message += f"Прирост: +{delta:,.2f} руб"
                        
                        logger.info(f"✅ Несколько оплат: {len(new_payments_list)} клиентов на сумму {delta:,.2f} руб")
                    
                    # Отправляем уведомление
                    if TELEGRAM_AVAILABLE and is_bot_available():
                        await send_notification_async(message)
                else:
                    # Если не удалось получить список оплат, отправляем без деталей
                    logger.warning("⚠️ Не удалось получить список оплат")
                    message = (
                        f"💰 <b>ОПЛАТА!</b>\n\n"
                        f"Общий сбор: <b>{new_sbor:,.2f} руб</b>\n"
                        f"Прирост: +{delta:,.2f} руб"
                    )
                    
                    if TELEGRAM_AVAILABLE and is_bot_available():
                        await send_notification_async(message)
            
            # ==================== ПРОВЕРКА КЛИЕНТОВ ====================
            old_fios = set(self.current_clients.keys())
            new_fios = set(new_clients.keys())
            
            # Пропавшие клиенты
            removed = old_fios - new_fios
            if removed and new_sbor <= self.current_sbor:
                # Клиенты пропали НЕ из-за оплаты
                logger.info(f"📉 Пропали клиенты: {len(removed)}")
                
                # Формируем список с днями просрочки
                removed_list = []
                for fio in list(removed)[:10]:  # Максимум 10
                    prosrochka = self.current_clients[fio].get('prosrochka', '?')
                    removed_list.append(f"• {fio} (просрочка: {prosrochka})")
                
                message = (
                    f"📉 <b>ПРОПАЛИ КЛИЕНТЫ!</b>\n\n"
                    f"Количество: {len(removed)}\n\n"
                    + "\n".join(removed_list)
                )
                
                if len(removed) > 10:
                    message += f"\n... и ещё {len(removed) - 10}"
                
                if TELEGRAM_AVAILABLE and is_bot_available():
                    await send_notification_async(message)
            
            # Новые клиенты
            added = new_fios - old_fios
            if added:
                logger.info(f"📈 Добавились клиенты: {len(added)}")
                
                # Формируем список с днями просрочки
                added_list = []
                for fio in list(added)[:10]:  # Максимум 10
                    prosrochka = new_clients[fio].get('prosrochka', '?')
                    added_list.append(f"• {fio} (просрочка: {prosrochka})")
                
                message = (
                    f"📈 <b>НОВЫЕ КЛИЕНТЫ!</b>\n\n"
                    f"Количество: {len(added)}\n\n"
                    + "\n".join(added_list)
                )
                
                if len(added) > 10:
                    message += f"\n... и ещё {len(added) - 10}"
                
                if TELEGRAM_AVAILABLE and is_bot_available():
                    await send_notification_async(message)
            
        except Exception as e:
            logger.error(f"❌ Ошибка сравнения данных: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def monitoring_loop(self):
        """Основной цикл мониторинга"""
        logger.info("🔄 Запуск цикла мониторинга...")
        
        # Обновляем статус - запущен
        if self.status_manager:
            self.status_manager.update_mode_status("online_stats", running=True)
        
        # Загружаем предыдущие данные
        self.load_previous_data()
        
        # Инициализируем браузер
        if not self.init_driver():
            logger.error("❌ Не удалось инициализировать браузер")
            if self.status_manager:
                self.status_manager.update_mode_status("online_stats", running=False, last_error="Не удалось инициализировать браузер")
            return
        
        # Входим в систему
        if not self.login():
            logger.error("❌ Не удалось войти в систему")
            if self.driver:
                self.driver.quit()
            if self.status_manager:
                self.status_manager.update_mode_status("online_stats", running=False, last_error="Не удалось войти в систему")
            return
        
        # ПРОВЕРКА 1: После входа, перед первым получением данных
        if self.status_manager and self.status_manager.check_stop_requested("online_stats"):
            logger.info("🛑 Получен запрос на остановку (после входа)")
            if self.driver:
                self.driver.quit()
            if self.status_manager:
                self.status_manager.clear_stop_request("online_stats")
                self.status_manager.update_mode_status("online_stats", running=False)
            return
        
        # Первое получение данных
        logger.info("📊 Первое получение данных...")
        
        clients = self.get_clients_list()
        
        # ПРОВЕРКА 2: После получения клиентов
        if self.status_manager and self.status_manager.check_stop_requested("online_stats"):
            logger.info("🛑 Получен запрос на остановку (после получения клиентов)")
            if self.driver:
                self.driver.quit()
            if self.status_manager:
                self.status_manager.clear_stop_request("online_stats")
                self.status_manager.update_mode_status("online_stats", running=False)
            return
        
        payments = self.get_payments_info()
        
        # ПРОВЕРКА 3: После получения оплат
        if self.status_manager and self.status_manager.check_stop_requested("online_stats"):
            logger.info("🛑 Получен запрос на остановку (после получения оплат)")
            if self.driver:
                self.driver.quit()
            if self.status_manager:
                self.status_manager.clear_stop_request("online_stats")
                self.status_manager.update_mode_status("online_stats", running=False)
            return
        
        sbor = self.get_total_sbor()
        premium = self.calculate_monthly_premium()  # ← НОВОЕ: Считаем премию!
        
        # Сохраняем
        self.save_current_data(clients, sbor, premium)  # ← Передаем премию
        self.current_clients = clients
        self.current_sbor = sbor
        self.current_premium = premium  # ← НОВОЕ: Сохраняем в поле класса
        
        # Обновляем статус с данными
        if self.status_manager:
            self.status_manager.status["online_stats"] = {
                "running": True,
                "clients_count": len(clients),
                "sbor": sbor,
                "premium": premium,  # ← НОВОЕ: Добавляем премию в статус
                "last_error": None
            }
            self.status_manager.save_status()
        
        logger.info(f"✅ Мониторинг запущен: {len(clients)} клиентов, сбор {sbor:,.2f} руб, премия {premium.get('total_premium', 0.0):,.2f} руб")
        
        # Отправляем стартовое уведомление
        if TELEGRAM_AVAILABLE and is_bot_available():
            message = (
                f"📊 <b>МОНИТОРИНГ ЗАПУЩЕН</b>\n\n"
                f"🟢 <b>Статус: Активен</b>\n\n"
                f"👥 Клиентов: <b>{len(clients)}</b>\n"
                f"💰 Текущий сбор: <b>{sbor:,.2f} руб</b>\n\n"
                f"💵 <b>Премия за месяц: {premium.get('total_premium', 0.0):,.2f} руб</b>\n"
                f"   • По сбору: <b>{premium.get('sbor_premium', 0.0):,.2f} руб</b>\n"
                f"   • По продлениям: <b>{premium.get('extensions_premium', 0.0):,.2f} руб</b> ({premium.get('extensions_count', 0)} шт)\n\n"
                f"🔔 Уведомления будут приходить при изменениях\n"
                f"⏱ Обновление каждую минуту"
            )
            await send_notification_async(message)
        
        # Основной цикл
        iteration = 0  # ← НОВОЕ: Счетчик итераций для обновления премии
        while self.is_running:
            # Проверяем флаг остановки через status_manager
            if self.status_manager and self.status_manager.check_stop_requested("online_stats"):
                logger.info("🛑 Получен запрос на остановку через status_manager")
                self.is_running = False
                break
            
            try:
                await asyncio.sleep(self.update_interval)
                
                logger.info("🔄 Обновление данных...")
                iteration += 1  # ← НОВОЕ
                
                # Переходим на страницу клиентов (используем базовый URL из настроек!)
                clients_url = f"{self.base_url}/manager/collector-debt/work"
                logger.info(f"📍 Переход на страницу клиентов: {clients_url}")
                self.driver.get(clients_url)
                
                # Ждём полной загрузки страницы
                wait = WebDriverWait(self.driver, 15)
                wait.until(EC.presence_of_element_located((By.XPATH, self.XPATH_PER_PAGE_SELECT)))
                time.sleep(1)
                
                # Получаем новые данные
                # ВАЖНО: Между этими запросами проходит время (несколько секунд)
                # Если за это время появится новая оплата, то new_payments может быть устаревшим
                # Но это НЕ проблема - в compare_and_notify() мы запросим свежий список!
                new_clients = self.get_clients_list()
                new_payments = self.get_payments_info()
                new_sbor = self.get_total_sbor()
                
                # ПРЕМИЮ обновляем реже (раз в час) чтобы не тормозить
                # ИЛИ всегда если была оплата (сбор вырос)
                new_premium = self.current_premium  # По умолчанию - старое значение
                if iteration % 60 == 0 or new_sbor > self.current_sbor:
                    logger.info("💵 Обновляю премию...")
                    new_premium = self.calculate_monthly_premium()
                
                # Сравниваем и уведомляем
                await self.compare_and_notify(new_clients, new_sbor, new_payments)
                
                # Обновляем текущие данные
                self.save_current_data(new_clients, new_sbor, new_premium)  # ← Передаем премию
                self.current_clients = new_clients
                self.current_sbor = new_sbor
                self.current_premium = new_premium  # ← НОВОЕ
                
                # Обновляем статус
                if self.status_manager:
                    self.status_manager.status["online_stats"] = {
                        "running": True,
                        "clients_count": len(new_clients),
                        "sbor": new_sbor,
                        "premium": new_premium,  # ← НОВОЕ
                        "last_error": None
                    }
                    self.status_manager.save_status()
                
            except (TimeoutException, WebDriverException) as e:
                # Браузер завис или упал - перезапускаем!
                logger.error(f"❌ Браузер завис/упал: {e}")
                logger.info("🔄 Перезапускаю браузер...")
                
                # Убиваем старый браузер
                try:
                    if self.driver:
                        self.driver.quit()
                except Exception:
                    pass
                
                # Пауза перед перезапуском
                await asyncio.sleep(5)
                
                # Создаём новый браузер
                if not self.init_driver():
                    logger.error("❌ Не удалось перезапустить браузер!")
                    if self.status_manager:
                        self.status_manager.update_mode_status("online_stats", running=False, last_error="Не удалось перезапустить браузер")
                    break
                
                # Логинимся заново
                if not self.login():
                    logger.error("❌ Не удалось войти после перезапуска!")
                    if self.driver:
                        self.driver.quit()
                    if self.status_manager:
                        self.status_manager.update_mode_status("online_stats", running=False, last_error="Не удалось войти после перезапуска")
                    break
                
                logger.info("✅ Браузер успешно перезапущен!")
                
                # Обновляем статус
                if self.status_manager:
                    self.status_manager.update_mode_status("online_stats", last_error="Браузер перезапущен")
                
            except Exception as e:
                # Другие ошибки - просто логируем
                logger.error(f"❌ Ошибка в цикле мониторинга: {e}")
                if self.status_manager:
                    self.status_manager.update_mode_status("online_stats", last_error=str(e))
                await asyncio.sleep(10)  # Пауза перед повтором
        
        # Закрываем браузер
        if self.driver:
            self.driver.quit()
        
        # Обновляем статус - остановлен
        if self.status_manager:
            self.status_manager.update_mode_status("online_stats", running=False)
        
        # Очищаем флаг остановки
        if self.status_manager:
            self.status_manager.clear_stop_request("online_stats")
        
        logger.info("🛑 Мониторинг остановлен")
    
    def start(self):
        """Запуск мониторинга"""
        if self.is_running:
            logger.warning("⚠️ Мониторинг уже запущен")
            return
        
        self.is_running = True
        asyncio.create_task(self.monitoring_loop())
    
    def stop(self):
        """Остановка мониторинга"""
        self.is_running = False
        logger.info("🛑 Команда остановки мониторинга")


if __name__ == "__main__":
    # Тестовый запуск
    stats = OnlineStatistics(
        url="https://max.credit/login",
        phone="79123456789",
        password="test_password"
    )
    stats.start()