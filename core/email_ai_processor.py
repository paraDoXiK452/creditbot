"""
📧 Email AI Agent - Процессор автоматической email-переписки с ИИ
Использует ChatGPT для ведения диалогов с клиентами по долгам

ОБНОВЛЕНО:
- Добавлена настройка имени коллектора
- Добавлена задержка между отправкой писем
- Добавлен лимит количества клиентов
- Добавлен просмотр диалогов и управление ими
"""

import imaplib
import smtplib
import email
import sqlite3
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Tuple
import pandas as pd
from openai import OpenAI

# Импортируем наши промпты и проверку стоп-слов
from email_ai_prompts import (
    get_system_prompt,
    get_greeting_template,
    check_stop_words,
    check_standard_responses
)

logger = logging.getLogger(__name__)

class EmailAIProcessor:
    """Процессор для автоматической email-переписки с ИИ"""
    
    # Импорт API ключа
    try:
        from api_config import OPENAI_API_KEY
    except ImportError:
        import os
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    def __init__(self, gmail_email: str, gmail_app_password: str,
                 ai_style: str = "medium", collector_name: str = "Руслан",
                 send_delay: int = 60, reply_delay: int = 120):
        """
        Args:
            gmail_email: Gmail адрес
            gmail_app_password: App Password от Gmail
            ai_style: "soft" / "medium" / "hard"
            collector_name: Имя коллектора (по умолчанию "Руслан")
            send_delay: Задержка между письмами в секундах
            reply_delay: Задержка перед ответом клиенту в секундах
        """
        self.gmail_email = gmail_email
        self.gmail_password = gmail_app_password
        self.ai_style = ai_style
        self.collector_name = collector_name
        self.send_delay = send_delay
        self.reply_delay = reply_delay
        
        # OpenAI клиент
        self.openai_client = OpenAI(api_key=self.OPENAI_API_KEY)
                
        # База данных для хранения диалогов
        self.db_path = Path.home() / ".maxcredit_email_ai" / "dialogs.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Путь к актуальным клиентам из online_statistics
        self.clients_file = Path.home() / ".maxcredit_stats" / "clients.json"
        
        # Флаг работы
        self.is_running = False
        
        logger.info("✅ EmailAIProcessor инициализирован")
        
    def _init_database(self):
        """Инициализация SQLite базы для хранения диалогов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица клиентов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                email TEXT PRIMARY KEY,
                fio TEXT,
                debt REAL,
                days INTEGER,
                contract TEXT,
                prolongation_available INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                first_message_sent TIMESTAMP,
                last_message_received TIMESTAMP,
                stop_reason TEXT
            )
        ''')
        
        # Таблица истории сообщений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_email TEXT,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_email) REFERENCES clients(email)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("📊 База данных инициализирована")
    
    def load_active_clients(self) -> Dict[str, Dict]:
        """
        Загружает актуальных клиентов из online_statistics
        
        Returns:
            {email: {"fio": ..., "in_work": True/False}}
        """
        if not self.clients_file.exists():
            logger.warning("⚠️ Файл clients.json не найден")
            return {}
        
        try:
            with open(self.clients_file, 'r', encoding='utf-8') as f:
                clients_data = json.load(f)
            
            logger.info(f"📂 Загружено {len(clients_data)} клиентов из online_statistics")
            return clients_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки clients.json: {e}")
            return {}
    
    def process_excel(self, excel_path: str, max_clients: int = 0) -> List[Dict]:
        """
        Обрабатывает Excel с клиентами и отправляет первые письма
        
        Args:
            excel_path: путь к Excel файлу
            max_clients: максимальное количество клиентов (0 = без лимита)
        
        Returns:
            список обработанных клиентов
        """
        logger.info(f"📊 Обработка Excel: {excel_path}")
        if max_clients > 0:
            logger.info(f"🔢 Лимит клиентов: {max_clients}")
        
        try:
            df = pd.read_excel(excel_path)
            
            required_columns = ['ФИО', 'Email', 'Общая задолженность', 'Просрочка', 'Договор']
            for col in required_columns:
                if col not in df.columns:
                    logger.error(f"❌ Отсутствует колонка: {col}")
                    return []
            
            # Применяем лимит если задан
            if max_clients > 0 and len(df) > max_clients:
                df = df.head(max_clients)
                logger.info(f"✂️ Ограничено до {max_clients} клиентов")
            
            processed = []
            
            for idx, row in df.iterrows():
                client = {
                    'fio': str(row['ФИО']),
                    'email': str(row['Email']).strip().lower(),
                    'debt': float(row['Общая задолженность']),
                    'days': int(row['Просрочка']),
                    'contract': str(row['Договор']),
                    'prolongation_available': False  # По умолчанию нет продления
                }
                
                # Отправляем первое письмо
                success = self.send_first_email(client)
                
                if success:
                    # Добавляем в базу
                    self._add_client_to_db(client)
                    processed.append(client)
                    
                    # Задержка между письмами
                    if idx < len(df) - 1:  # Не задерживаем после последнего
                        logger.info(f"⏳ Задержка {self.send_delay} сек перед следующим письмом...")
                        time.sleep(self.send_delay)
            
            logger.info(f"✅ Обработано клиентов: {len(processed)}")
            return processed
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки Excel: {e}")
            return []
    
    def send_first_email(self, client: Dict) -> bool:
        """Отправляет первое письмо клиенту"""
        try:
            # Получаем шаблон первого письма
            template = get_greeting_template(self.ai_style, client['days'])
            
            # Подставляем ФИО
            message_text = f"Здравствуйте, {client['fio']}!\n\n{template}"
            
            # Отправляем
            subject = "Напоминание о задолженности"
            self._send_email(client['email'], subject, message_text)
            
            # Сохраняем в историю
            self._save_message(client['email'], 'assistant', message_text)
            
            logger.info(f"📧 Отправлено первое письмо: {client['email']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки первого письма: {e}")
            return False
    
    def _send_email(self, to_email: str, subject: str, body: str):
        """Отправляет email через Gmail SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.gmail_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(self.gmail_email, self.gmail_password)
            server.sendmail(self.gmail_email, [to_email], msg.as_string())
            server.quit()
            
            logger.info(f"✉️ Email отправлен: {to_email}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки email: {e}")
            raise
    
    def check_incoming_emails(self):
        """Проверяет входящие письма и генерирует ответы"""
        logger.info("📬 Проверка входящих писем...")
        
        try:
            # Подключаемся к Gmail IMAP
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(self.gmail_email, self.gmail_password)
            mail.select('INBOX')
            
            # Ищем непрочитанные письма
            result, data = mail.search(None, 'UNSEEN')
            email_ids = data[0].split()
            
            logger.info(f"📨 Найдено непрочитанных писем: {len(email_ids)}")
            
            for email_id in email_ids:
                try:
                    # Получаем письмо
                    result, msg_data = mail.fetch(email_id, '(RFC822)')
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # Извлекаем отправителя
                    from_email = email.utils.parseaddr(msg['From'])[1].lower()
                    
                    # Извлекаем текст письма
                    body = self._extract_email_body(msg)
                    
                    logger.info(f"📩 Письмо от: {from_email}")
                    
                    # Обрабатываем письмо
                    self._process_incoming_email(from_email, body)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки письма: {e}")
                    continue
            
            mail.close()
            mail.logout()
            
            # Синхронизируем базы - удаляем оплативших
            self.sync_with_active_clients()
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки почты: {e}")
    
    def _extract_email_body(self, msg) -> str:
        """Извлекает текст письма"""
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == 'text/plain':
                        return part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            return ""
    
    def _process_incoming_email(self, from_email: str, body: str):
        """Обрабатывает входящее письмо и генерирует ответ"""
        
        logger.info(f"📧 Обработка письма от: {from_email}")
        
        # 0. Проверяем: клиент уже остановлен?
        if self._is_client_in_db(from_email):
            client_info_check = self._get_client_from_db(from_email)
            if client_info_check and client_info_check['status'] == 'stopped':
                logger.info(f"⛔ Клиент в СТОП-листе [{client_info_check.get('stop_reason', 'unknown')}]: {from_email}")
                return
        
        # 1. Проверяем стоп-слова
        is_stop, stop_reason = check_stop_words(body)
        if is_stop:
            logger.info(f"🛑 СТОП-СЛОВО обнаружено [{stop_reason}]: {from_email}")
            if self._is_client_in_db(from_email):
                self._mark_client_stopped(from_email, stop_reason)
            return
        
        # 2. Проверяем: есть ли в базе?
        client_info = self._get_client_from_db(from_email)
        
        if not client_info:
            logger.info(f"⏭️ Email не найден в базе, пропускаем: {from_email}")
            return
        
        # Сохраняем входящее сообщение
        self._save_message(from_email, 'user', body)
        
        # ✨ НОВОЕ: Проверяем стандартные ответы
        is_standard, standard_response = check_standard_responses(
            body, 
            client_info, 
            collector_name=self.collector_name
        )
        
        if is_standard:
            # Используем стандартный ответ БЕЗ вызова ИИ
            logger.info(f"✨ Стандартный ответ для {from_email}")
            ai_reply = standard_response
        else:
            # Генерируем ответ через ИИ
            ai_reply = self.generate_ai_reply(client_info, body)
        
        # Проверяем метку СТОП
        if '[СТОП_ДИАЛОГ]' in ai_reply:
            logger.info(f"🛑 ИИ обнаружил причину для остановки: {from_email}")
            ai_reply = ai_reply.replace('[СТОП_ДИАЛОГ]', '').strip()
            self._mark_client_stopped(from_email, "AI decision")
        
        # Сохраняем ответ
        self._save_message(from_email, 'assistant', ai_reply)
        
        # ✨ ЗАДЕРЖКА перед ответом (имитация "печатает...")
        logger.info(f"⏳ Жду {self.reply_delay} сек перед ответом (выглядит естественнее)...")
        time.sleep(self.reply_delay)
        
        # Отправляем ответ
        try:
            subject = f"Re: Напоминание о задолженности"
            self._send_email(from_email, subject, ai_reply)
            logger.info(f"✅ Ответ отправлен: {from_email}")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки ответа: {e}")
    
    def generate_ai_reply(self, client_info: Dict, client_message: str) -> str:
        """
        Генерирует ответ через ChatGPT
        
        Args:
            client_info: информация о клиенте
            client_message: сообщение от клиента
        
        Returns:
            Текст ответа
        """
        try:
            # Получаем системный промпт с collector_name
            system_prompt = get_system_prompt(self.ai_style, {
                'fio': client_info['fio'],
                'debt': client_info['debt'],
                'days': client_info['days'],
                'contract': client_info['contract'],
                'prolongation_available': client_info.get('prolongation_available', False)
            }, collector_name=self.collector_name)
            
            # Получаем историю диалога
            history = self._get_dialog_history(client_info['email'])
            
            # Формируем сообщения
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history)
            messages.append({"role": "user", "content": client_message})
            
            # Генерируем ответ
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            ai_reply = response.choices[0].message.content
            
            logger.info(f"🤖 Сгенерирован ответ для {client_info['email']}")
            return ai_reply
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации ответа: {e}")
            return "Извините, произошла техническая ошибка. Мы свяжемся с вами позже."
    
    # =================================================================
    # МЕТОДЫ РАБОТЫ С БАЗОЙ ДАННЫХ
    # =================================================================
    
    def _add_client_to_db(self, client: Dict):
        """Добавляет клиента в базу"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO clients (email, fio, debt, days, contract, prolongation_available, first_message_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            client['email'],
            client['fio'],
            client['debt'],
            client['days'],
            client['contract'],
            1 if client.get('prolongation_available', False) else 0,
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    def _update_client_in_db(self, client: Dict):
        """Обновляет данные клиента"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE clients
            SET debt = ?, days = ?, contract = ?, prolongation_available = ?
            WHERE email = ?
        ''', (
            client['debt'],
            client['days'],
            client['contract'],
            1 if client.get('prolongation_available', False) else 0,
            client['email']
        ))
        
        conn.commit()
        conn.close()
    
    def _is_client_in_db(self, email: str) -> bool:
        """Проверяет наличие клиента в базе"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT email FROM clients WHERE email = ?', (email,))
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    def _get_client_from_db(self, email: str) -> Optional[Dict]:
        """Получает информацию о клиенте из базы"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT email, fio, debt, days, contract, status, prolongation_available, stop_reason
            FROM clients WHERE email = ?
        ''', (email,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'email': row[0],
                'fio': row[1],
                'debt': row[2],
                'days': row[3],
                'contract': row[4],
                'status': row[5],
                'prolongation_available': bool(row[6]),
                'stop_reason': row[7]
            }
        return None
    
    def _mark_client_stopped(self, email: str, reason: str):
        """Помечает клиента как остановленного"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE clients
            SET status = 'stopped', stop_reason = ?
            WHERE email = ?
        ''', (reason, email))
        
        conn.commit()
        conn.close()
        
        logger.info(f"🛑 Клиент помечен как остановлен [{reason}]: {email}")
    
    def _save_message(self, client_email: str, role: str, content: str):
        """Сохраняет сообщение в историю"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO messages (client_email, role, content)
            VALUES (?, ?, ?)
        ''', (client_email, role, content))
        
        conn.commit()
        conn.close()
    
    def _get_dialog_history(self, email: str, limit: int = 10) -> List[Dict]:
        """
        Получает последние N сообщений диалога
        
        Args:
            email: email клиента
            limit: количество сообщений
        
        Returns:
            [{"role": "user"/"assistant", "content": "..."}]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT role, content
            FROM messages
            WHERE client_email = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (email, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Возвращаем в обратном порядке (от старых к новым)
        history = [{"role": row[0], "content": row[1]} for row in reversed(rows)]
        return history
    
    # =================================================================
    # ✨ НОВЫЕ МЕТОДЫ: ПРОСМОТР И УПРАВЛЕНИЕ ДИАЛОГАМИ
    # =================================================================
    
    def get_clients_with_dialogs(self) -> List[Dict]:
        """
        Получает список клиентов у которых есть переписка (минимум 1 ответ от клиента)
        
        Returns:
            [{"email": ..., "fio": ..., "debt": ..., "days": ..., "status": ..., "messages_count": ...}]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем клиентов у которых есть хотя бы 1 входящее сообщение (role='user')
        cursor.execute('''
            SELECT 
                c.email,
                c.fio,
                c.debt,
                c.days,
                c.status,
                c.stop_reason,
                COUNT(m.id) as msg_count,
                MAX(m.timestamp) as last_msg
            FROM clients c
            INNER JOIN messages m ON c.email = m.client_email
            WHERE m.role = 'user'
            GROUP BY c.email
            ORDER BY last_msg DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        clients = []
        for row in rows:
            clients.append({
                'email': row[0],
                'fio': row[1],
                'debt': row[2],
                'days': row[3],
                'status': row[4],
                'stop_reason': row[5],
                'messages_count': row[6],
                'last_message': row[7]
            })
        
        return clients
    
    def get_dialog_history_full(self, email: str) -> List[Dict]:
        """
        Получает ПОЛНУЮ историю диалога с клиентом
        
        Args:
            email: email клиента
        
        Returns:
            [{"role": "user"/"assistant", "content": "...", "timestamp": "..."}]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT role, content, timestamp
            FROM messages
            WHERE client_email = ?
            ORDER BY timestamp ASC
        ''', (email,))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                'role': row[0],
                'content': row[1],
                'timestamp': row[2]
            })
        
        return history
    
    def resume_client_dialog(self, email: str):
        """
        Возобновляет диалог с клиентом (убирает статус 'stopped')
        
        Args:
            email: email клиента
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE clients
            SET status = 'active', stop_reason = NULL
            WHERE email = ?
        ''', (email,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"▶️ Диалог возобновлён: {email}")
    
    def stop_client_dialog_manual(self, email: str):
        """
        Останавливает диалог с клиентом вручную (через UI)
        
        Args:
            email: email клиента
        """
        self._mark_client_stopped(email, "остановлено вручную")
    
    # =================================================================
    # СИНХРОНИЗАЦИЯ И СТАТИСТИКА
    # =================================================================
    
    def sync_with_active_clients(self):
        """
        Синхронизация с online_statistics - удаление клиентов которые оплатили
        """
        try:
            # Загружаем актуальных клиентов
            active_clients = self.load_active_clients()
            
            if not active_clients:
                logger.warning("⚠️ Не удалось загрузить список активных клиентов")
                return
            
            active_fios = set(active_clients.keys())
            
            # Получаем всех клиентов из базы
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT email, fio FROM clients WHERE status = 'active'")
            email_ai_clients = cursor.fetchall()
            
            # Ищем кого нужно удалить
            to_delete = []
            for email, fio in email_ai_clients:
                if fio not in active_fios:
                    to_delete.append((email, fio))
            
            # Удаляем
            if to_delete:
                logger.info(f"🗑️ Удаляем {len(to_delete)} оплативших клиентов:")
                for email, fio in to_delete:
                    cursor.execute("DELETE FROM clients WHERE email = ?", (email,))
                    cursor.execute("DELETE FROM messages WHERE client_email = ?", (email,))
                    logger.info(f"  • {fio} ({email})")
                
                conn.commit()
            else:
                logger.info("✅ Все клиенты актуальны")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации: {e}")
    
    def get_statistics(self) -> Dict:
        """
        Получает статистику по клиентам
        
        Returns:
            Словарь со статистикой
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Всего загружено
            cursor.execute("SELECT COUNT(*) FROM clients")
            loaded = cursor.fetchone()[0]
            
            # Отправлено писем
            cursor.execute("SELECT COUNT(*) FROM clients WHERE first_message_sent IS NOT NULL")
            sent = cursor.fetchone()[0]
            
            # Получено ответов
            cursor.execute("SELECT COUNT(DISTINCT client_email) FROM messages WHERE role = 'user'")
            received = cursor.fetchone()[0]
            
            # Активных
            cursor.execute("SELECT COUNT(*) FROM clients WHERE status = 'active'")
            active = cursor.fetchone()[0]
            
            # Остановлено
            cursor.execute("SELECT COUNT(*) FROM clients WHERE status = 'stopped'")
            stopped = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'loaded': loaded,
                'sent': sent,
                'received': received,
                'active': active,
                'stopped': stopped
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {
                'loaded': 0,
                'sent': 0,
                'received': 0,
                'active': 0,
                'stopped': 0
            }
    
    # =================================================================
    # ОСНОВНОЙ ЦИКЛ МОНИТОРИНГА
    # =================================================================
    
    def start_monitoring(self, check_interval: int = 60):
        """
        Запускает мониторинг входящих писем
        
        Args:
            check_interval: интервал проверки в секундах
        """
        self.is_running = True
        logger.info("🚀 Запуск мониторинга email")
        
        while self.is_running:
            try:
                self.check_incoming_emails()
                time.sleep(check_interval)
            except KeyboardInterrupt:
                logger.info("⏹️ Остановка по Ctrl+C")
                break
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле мониторинга: {e}")
                time.sleep(10)  # Пауза перед повтором
    
    def stop_monitoring(self):
        """Останавливает мониторинг"""
        self.is_running = False
        logger.info("⏹️ Остановка мониторинга")


# =================================================================
# ТЕСТИРОВАНИЕ
# =================================================================

if __name__ == "__main__":
    # Пример использования
    logging.basicConfig(level=logging.INFO)
    
    processor = EmailAIProcessor(
        gmail_email="your@gmail.com",
        gmail_app_password="your_app_password",
        ai_style="medium",
        collector_name="Руслан",
        send_delay=60
    )
    
    # Обработка Excel с лимитом
    # processor.process_excel("clients.xlsx", max_clients=100)
    
    # Запуск мониторинга
    # processor.start_monitoring(check_interval=60)