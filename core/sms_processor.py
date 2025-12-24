"""
📱 SMS AI Agent - Процессор автоматической SMS-рассылки с ИИ
Использует Android телефон через Telegram для отправки SMS
Аналог email_ai_processor.py но для SMS

ФУНКЦИИ:
- Массовая рассылка SMS через Android телефон
- AI генерация персонализированных сообщений
- Управление через Telegram Bot
- История отправки в БД
- QR код для подключения Android устройства
"""

import sqlite3
import json
import time
import logging
import qrcode
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from openai import OpenAI

# Telegram уведомления
try:
    from telegram_manager import send_notification_sync, is_bot_available
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    def send_notification_sync(msg): pass
    def is_bot_available(): return False

logger = logging.getLogger(__name__)


class SMSProcessor:
    """Процессор для автоматической SMS-рассылки с ИИ"""
    
    import os
    openai.api_key = os.getenv("OPENAI_API_KEY", "")
    
    def __init__(self, bot_token: str, bot_chat_id: str, 
                 ai_style: str = "medium", collector_name: str = "Руслан",
                 send_delay: int = 10):
        """
        Args:
            bot_token: Токен Telegram бота
            bot_chat_id: Chat ID для отправки команд Android устройству
            ai_style: "soft" / "medium" / "hard"
            collector_name: Имя коллектора
            send_delay: Задержка между SMS в секундах
        """
        self.bot_token = bot_token
        self.bot_chat_id = bot_chat_id
        self.ai_style = ai_style
        self.collector_name = collector_name
        self.send_delay = send_delay
        
        # OpenAI клиент (опционально для AI генерации)
        self.openai_client = OpenAI(api_key=self.OPENAI_API_KEY) if self.OPENAI_API_KEY else None
        
        # База данных для истории
        self.db_path = Path.home() / ".maxcredit_sms" / "sms_history.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        logger.info("✅ SMSProcessor инициализирован")
    
    def _init_database(self):
        """Инициализация БД для хранения истории SMS"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sms_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL,
                fio TEXT,
                message TEXT NOT NULL,
                debt REAL,
                days INTEGER,
                status TEXT DEFAULT 'sent',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                phone TEXT PRIMARY KEY,
                fio TEXT,
                debt REAL,
                days INTEGER,
                contract TEXT,
                total_sms_sent INTEGER DEFAULT 0,
                last_sms_sent TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("📊 База данных SMS инициализирована")
    
    def generate_qr_code(self, device_name: str = "Android Device") -> str:
        """
        Генерирует QR код для подключения Android устройства
        
        Args:
            device_name: Название устройства
        
        Returns:
            Путь к сохранённому QR коду
        """
        qr_data = {
            "bot_token": self.bot_token,
            "chat_id": self.bot_chat_id,
            "device_name": device_name
        }
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        qr_path = self.db_path.parent / "device_qr.png"
        img.save(qr_path)
        
        logger.info(f"✅ QR код создан: {qr_path}")
        return str(qr_path)
    
    def send_sms(self, phone: str, message: str) -> bool:
        """
        Отправляет SMS через Android устройство
        
        Args:
            phone: Номер телефона (10 цифр)
            message: Текст сообщения
        
        Returns:
            True если команда отправлена
        """
        try:
            # Форматируем номер (убираем +7, оставляем 10 цифр)
            phone_clean = ''.join(filter(str.isdigit, str(phone)))
            if phone_clean.startswith('7') and len(phone_clean) == 11:
                phone_clean = phone_clean[1:]
            
            # Отправляем команду через Telegram
            command = f"SMS:{phone_clean}:{message}"
            
            if TELEGRAM_AVAILABLE and is_bot_available():
                send_notification_sync(command)
                logger.info(f"📱 SMS команда отправлена: {phone_clean}")
                return True
            else:
                logger.error("❌ Telegram бот недоступен")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки SMS: {e}")
            return False
    
    def process_excel(self, excel_path: str, max_clients: int = 0, 
                     use_ai: bool = False) -> List[Dict]:
        """
        Обрабатывает Excel с клиентами и отправляет SMS
        
        Args:
            excel_path: Путь к Excel файлу
            max_clients: Максимум клиентов (0 = без лимита)
            use_ai: Использовать AI для генерации текста
        
        Returns:
            Список обработанных клиентов
        """
        logger.info(f"📊 Обработка Excel: {excel_path}")
        if max_clients > 0:
            logger.info(f"🔢 Лимит клиентов: {max_clients}")
        
        try:
            df = pd.read_excel(excel_path)
            
            # Нужные колонки: ФИО, Телефон, Задолженность, Просрочка
            required_columns = ['ФИО', 'Телефон', 'Общая задолженность', 'Просрочка']
            for col in required_columns:
                if col not in df.columns:
                    logger.error(f"❌ Отсутствует колонка: {col}")
                    return []
            
            # Применяем лимит
            if max_clients > 0 and len(df) > max_clients:
                df = df.head(max_clients)
                logger.info(f"✂️ Ограничено до {max_clients} клиентов")
            
            processed = []
            
            # 📱 Уведомление о запуске
            if TELEGRAM_AVAILABLE and is_bot_available():
                send_notification_sync(
                    f"📱 <b>SMS РАССЫЛКА ЗАПУЩЕНА</b>\n\n"
                    f"👥 Клиентов в очереди: <b>{len(df)}</b>\n"
                    f"🤖 AI генерация: {'Да' if use_ai else 'Нет'}\n"
                    f"⏱ Задержка: {self.send_delay} сек"
                )
            
            for idx, row in df.iterrows():
                client = {
                    'fio': str(row['ФИО']),
                    'phone': str(row['Телефон']),
                    'debt': float(row['Общая задолженность']),
                    'days': int(row['Просрочка']),
                    'contract': str(row.get('Договор', ''))
                }
                
                # Генерируем сообщение
                if use_ai and self.openai_client:
                    message = self._generate_ai_message(client)
                else:
                    message = self._get_template_message(client)
                
                # Отправляем SMS
                success = self.send_sms(client['phone'], message)
                
                if success:
                    # Сохраняем в БД
                    self._save_to_history(client, message, 'sent')
                    self._update_client_stats(client)
                    processed.append(client)
                    
                    logger.info(f"✅ {idx+1}/{len(df)}: {client['fio']} - SMS отправлено")
                    
                    # Задержка между SMS
                    if idx < len(df) - 1:
                        time.sleep(self.send_delay)
                else:
                    self._save_to_history(client, message, 'error')
                    logger.error(f"❌ {idx+1}/{len(df)}: {client['fio']} - ошибка")
            
            logger.info(f"✅ Обработано клиентов: {len(processed)}")
            
            # 📱 Финальное уведомление
            if TELEGRAM_AVAILABLE and is_bot_available():
                send_notification_sync(
                    f"✅ <b>SMS РАССЫЛКА ЗАВЕРШЕНА</b>\n\n"
                    f"📊 Всего: {len(df)}\n"
                    f"✅ Отправлено: <b>{len(processed)}</b>\n"
                    f"❌ Ошибок: {len(df) - len(processed)}\n"
                    f"⏱ Завершено: {datetime.now().strftime('%H:%M:%S')}"
                )
            
            return processed
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки Excel: {e}")
            
            if TELEGRAM_AVAILABLE and is_bot_available():
                send_notification_sync(f"🚨 <b>ОШИБКА SMS РАССЫЛКИ</b>\n\n❌ {str(e)[:200]}")
            
            return []
    
    def _get_template_message(self, client: Dict) -> str:
        """
        Генерирует сообщение по шаблону (без AI)
        
        Args:
            client: Данные клиента
        
        Returns:
            Текст SMS
        """
        days = client['days']
        debt = client['debt']
        
        if days < 30:
            template = (
                f"{client['fio']}, напоминаем о задолженности {debt:.0f}₽. "
                f"Просрочка {days} дн. Просьба погасить долг. "
                f"Вопросы: 8-800-XXX-XX-XX"
            )
        elif days < 90:
            template = (
                f"{client['fio']}, срочно погасите задолженность {debt:.0f}₽. "
                f"Просрочка {days} дн. Возможны штрафные санкции. "
                f"Контакты: 8-800-XXX-XX-XX"
            )
        else:
            template = (
                f"{client['fio']}, важно! Задолженность {debt:.0f}₽, просрочка {days} дн. "
                f"Без оплаты возможна передача в суд. "
                f"Звоните: 8-800-XXX-XX-XX"
            )
        
        # Обрезаем до 160 символов (1 SMS)
        return template[:160]
    
    def _generate_ai_message(self, client: Dict) -> str:
        """
        Генерирует персонализированное сообщение через ChatGPT
        
        Args:
            client: Данные клиента
        
        Returns:
            Текст SMS
        """
        try:
            system_prompt = f"""Ты коллектор {self.collector_name}. 
            Стиль: {self.ai_style} (soft=мягкий, medium=средний, hard=жёсткий).
            Задача: написать SMS напоминание о долге.
            Требования:
            - Максимум 160 символов (1 SMS)
            - Обращение по имени
            - Сумма и срок просрочки
            - Призыв к действию
            - Без эмодзи
            """
            
            user_prompt = f"""Клиент: {client['fio']}
            Задолженность: {client['debt']:.0f}₽
            Просрочка: {client['days']} дней
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            message = response.choices[0].message.content.strip()
            
            # Обрезаем до 160 символов
            return message[:160]
            
        except Exception as e:
            logger.error(f"❌ Ошибка AI генерации: {e}")
            # Возвращаем шаблон как fallback
            return self._get_template_message(client)
    
    def _save_to_history(self, client: Dict, message: str, status: str):
        """Сохраняет SMS в историю"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sms_history (phone, fio, message, debt, days, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            client['phone'],
            client['fio'],
            message,
            client['debt'],
            client['days'],
            status
        ))
        
        conn.commit()
        conn.close()
    
    def _update_client_stats(self, client: Dict):
        """Обновляет статистику клиента"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO clients (phone, fio, debt, days, contract, total_sms_sent, last_sms_sent)
            VALUES (?, ?, ?, ?, ?, 
                COALESCE((SELECT total_sms_sent FROM clients WHERE phone = ?), 0) + 1,
                CURRENT_TIMESTAMP)
        ''', (
            client['phone'],
            client['fio'],
            client['debt'],
            client['days'],
            client.get('contract', ''),
            client['phone']
        ))
        
        conn.commit()
        conn.close()
    
    def get_statistics(self) -> Dict:
        """
        Получает статистику по SMS
        
        Returns:
            Словарь со статистикой
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Всего отправлено
            cursor.execute("SELECT COUNT(*) FROM sms_history WHERE status = 'sent'")
            sent = cursor.fetchone()[0]
            
            # Ошибок
            cursor.execute("SELECT COUNT(*) FROM sms_history WHERE status = 'error'")
            errors = cursor.fetchone()[0]
            
            # Уникальных клиентов
            cursor.execute("SELECT COUNT(DISTINCT phone) FROM sms_history")
            unique_clients = cursor.fetchone()[0]
            
            # За сегодня
            cursor.execute('''
                SELECT COUNT(*) FROM sms_history 
                WHERE DATE(timestamp) = DATE('now') AND status = 'sent'
            ''')
            today = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_sent': sent,
                'total_errors': errors,
                'unique_clients': unique_clients,
                'today': today
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {
                'total_sent': 0,
                'total_errors': 0,
                'unique_clients': 0,
                'today': 0
            }
    
    def get_client_history(self, phone: str) -> List[Dict]:
        """
        Получает историю SMS для клиента
        
        Args:
            phone: Номер телефона
        
        Returns:
            Список SMS
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT message, status, timestamp
            FROM sms_history
            WHERE phone = ?
            ORDER BY timestamp DESC
        ''', (phone,))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                'message': row[0],
                'status': row[1],
                'timestamp': row[2]
            })
        
        return history


# =================================================================
# ТЕСТИРОВАНИЕ
# =================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Пример использования
    processor = SMSProcessor(
        bot_token="YOUR_BOT_TOKEN",
        bot_chat_id="YOUR_CHAT_ID",
        ai_style="medium",
        collector_name="Руслан",
        send_delay=10
    )
    
    # Генерация QR кода для Android
    # qr_path = processor.generate_qr_code("Мой телефон")
    # print(f"QR код сохранён: {qr_path}")
    
    # Обработка Excel
    # processor.process_excel("clients.xlsx", max_clients=100, use_ai=True)
    
    # Статистика
    # stats = processor.get_statistics()
    # print(f"Статистика: {stats}")
