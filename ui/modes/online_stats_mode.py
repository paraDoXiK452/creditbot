"""
📊 Режим онлайн-статистики
Отображение статистики Max.Credit в реальном времени
"""

import logging
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTextEdit, QGroupBox, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont

from .base import ModeBase


class QtLogHandler(logging.Handler):
    """Обработчик логов для отправки в Qt UI через сигналы"""
    
    def __init__(self, signal):
        super().__init__()
        self.signal = signal
    
    def emit(self, record):
        """Отправка лога через сигнал"""
        try:
            msg = self.format(record)
            
            # Определяем уровень для цветового кодирования
            level_map = {
                logging.INFO: "info",
                logging.WARNING: "warning",
                logging.ERROR: "error",
                logging.CRITICAL: "error",
                logging.DEBUG: "info"
            }
            level = level_map.get(record.levelno, "info")
            
            # Отправляем через сигнал (потокобезопасно)
            self.signal.emit(msg, level)
        except Exception:
            pass


class OnlineStatsWorkerThread(QThread):
    """
    QThread для запуска мониторинга онлайн статистики
    ВАЖНО: Это QThread, а не threading.Thread!
    Это позволяет updater.py корректно остановить поток перед обновлением
    """
    error_signal = pyqtSignal(str)
    
    def __init__(self, online_stats):
        super().__init__()
        self.online_stats = online_stats
        self._is_running = True
    
    def run(self):
        """Запуск мониторинга в QThread"""
        import asyncio
        
        try:
            # Создаём новый event loop для этого потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Запускаем мониторинг
            self.online_stats.is_running = True
            loop.run_until_complete(self.online_stats.monitoring_loop())
        except Exception as e:
            self.error_signal.emit(f"❌ Ошибка в потоке мониторинга: {e}")
            import traceback
            traceback.print_exc()
        finally:
            loop.close()
    
    def stop(self):
        """Остановка потока (вызывается updater.py)"""
        self._is_running = False
        if self.online_stats:
            self.online_stats.stop()


class OnlineStatsMode(ModeBase):
    """Режим онлайн-статистики"""
    
    # Сигналы для обновления UI из других потоков
    stats_updated = pyqtSignal(dict)
    log_message = pyqtSignal(str, str)  # message, level
    
    def __init__(self, parent=None):
        super().__init__(
            title="📊 Онлайн статистика",
            description="Мониторинг клиентов, оплат и премий Max.Credit",
            parent=parent
        )
        self.online_stats = None
        self.online_stats_thread = None
        self.is_running = False
        
        # Подключаем сигналы
        self.stats_updated.connect(self.update_stats_display)
        self.log_message.connect(self.add_log_message)
        
        # Настраиваем перехват логов из модуля online_statistics
        self.setup_log_capture()
        
        self.init_ui()
        
        # Таймер для обновления отображения
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.check_status)
        self.update_timer.start(2000)  # Каждые 2 секунды
    
    def setup_log_capture(self):
        """Настройка перехвата логов из модуля online_statistics"""
        try:
            # Создаём handler для логов
            log_handler = QtLogHandler(self.log_message)
            log_handler.setLevel(logging.INFO)
            
            # Форматирование логов (убираем timestamp т.к. добавляем свой)
            formatter = logging.Formatter('%(message)s')
            log_handler.setFormatter(formatter)
            
            # Подключаем к логгеру online_statistics
            online_stats_logger = logging.getLogger('online_statistics')
            online_stats_logger.addHandler(log_handler)
            online_stats_logger.setLevel(logging.INFO)
            
            self.log_handler = log_handler  # Сохраняем ссылку
            
        except Exception as e:
            print(f"⚠️ Не удалось настроить перехват логов: {e}")
    
    
    def get_real_status(self):
        """
        Получает РЕАЛЬНЫЙ статус мониторинга из status_manager
        Это надёжнее чем self.is_running, т.к. работает даже если GUI перезапущен
        """
        try:
            from status_manager import get_status_manager
            status_manager = get_status_manager()
            
            if "online_stats" in status_manager.status:
                return status_manager.status["online_stats"].get("running", False)
            return False
        except Exception:
            return False
    
    def init_ui(self):
        """Инициализация интерфейса"""
        
        # ═══════════════════════════════════════════════════════════════
        # СТАТИСТИКА
        # ═══════════════════════════════════════════════════════════════
        
        stats_group = QGroupBox("📈 Текущая статистика")
        stats_group.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        stats_layout = QGridLayout()
        stats_layout.setSpacing(15)
        
        # Создаем лейблы для статистики
        self.status_label = self.create_stat_label("🔴 Не запущен", is_status=True)
        self.clients_label = self.create_stat_label("—")
        self.sbor_label = self.create_stat_label("—")
        self.premium_label = self.create_stat_label("—")
        self.sbor_premium_label = self.create_stat_label("—")
        self.extensions_premium_label = self.create_stat_label("—")
        self.extensions_count_label = self.create_stat_label("—")
        self.last_update_label = self.create_stat_label("—", is_small=True)
        
        # Добавляем в сетку
        row = 0
        stats_layout.addWidget(QLabel("Статус:"), row, 0)
        stats_layout.addWidget(self.status_label, row, 1)
        
        row += 1
        stats_layout.addWidget(self.create_separator(), row, 0, 1, 2)
        
        row += 1
        stats_layout.addWidget(QLabel("👥 Клиентов:"), row, 0)
        stats_layout.addWidget(self.clients_label, row, 1)
        
        row += 1
        stats_layout.addWidget(QLabel("💰 Текущий сбор:"), row, 0)
        stats_layout.addWidget(self.sbor_label, row, 1)
        
        row += 1
        stats_layout.addWidget(self.create_separator(), row, 0, 1, 2)
        
        row += 1
        stats_layout.addWidget(QLabel("💵 Премия за месяц:"), row, 0)
        stats_layout.addWidget(self.premium_label, row, 1)
        
        row += 1
        stats_layout.addWidget(QLabel("  • По сбору:"), row, 0)
        stats_layout.addWidget(self.sbor_premium_label, row, 1)
        
        row += 1
        stats_layout.addWidget(QLabel("  • По продлениям:"), row, 0)
        stats_layout.addWidget(self.extensions_premium_label, row, 1)
        
        row += 1
        stats_layout.addWidget(QLabel("  • Продлений:"), row, 0)
        stats_layout.addWidget(self.extensions_count_label, row, 1)
        
        row += 1
        stats_layout.addWidget(self.create_separator(), row, 0, 1, 2)
        
        row += 1
        stats_layout.addWidget(QLabel("🕐 Обновлено:"), row, 0)
        stats_layout.addWidget(self.last_update_label, row, 1)
        
        stats_group.setLayout(stats_layout)
        
        # ═══════════════════════════════════════════════════════════════
        # КНОПКИ УПРАВЛЕНИЯ
        # ═══════════════════════════════════════════════════════════════
        
        buttons_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ Запустить мониторинг")
        self.start_btn.clicked.connect(self.start_monitoring)
        self.start_btn.setMinimumHeight(40)
        
        self.stop_btn = QPushButton("⏹ Остановить")
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        
        self.clear_logs_btn = QPushButton("🗑 Очистить логи")
        self.clear_logs_btn.clicked.connect(self.clear_logs)
        self.clear_logs_btn.setMinimumHeight(40)
        
        buttons_layout.addWidget(self.start_btn)
        buttons_layout.addWidget(self.stop_btn)
        buttons_layout.addWidget(self.clear_logs_btn)
        
        # ═══════════════════════════════════════════════════════════════
        # ЛОГИ
        # ═══════════════════════════════════════════════════════════════
        
        logs_group = QGroupBox("📋 Логи работы")
        logs_group.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        logs_layout = QVBoxLayout()
        
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setMinimumHeight(300)
        self.logs_text.setFont(QFont("Consolas", 9))
        self.logs_text.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        logs_layout.addWidget(self.logs_text)
        logs_group.setLayout(logs_layout)
        
        # ═══════════════════════════════════════════════════════════════
        # СОБИРАЕМ LAYOUT
        # ═══════════════════════════════════════════════════════════════
        
        self.content_layout.addWidget(stats_group)
        self.content_layout.addLayout(buttons_layout)
        self.content_layout.addWidget(logs_group)
        
        self.apply_styles()
    
    def create_stat_label(self, text, is_status=False, is_small=False):
        """Создать красивый лейбл для статистики"""
        label = QLabel(text)
        
        if is_status:
            label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        elif is_small:
            label.setFont(QFont("Segoe UI", 8))
        else:
            label.setFont(QFont("Segoe UI", 11))
        
        label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        return label
    
    def create_separator(self):
        """Создать разделитель"""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #334155;")
        return line
    
    def apply_styles(self):
        """Применить стили"""
        self.setStyleSheet("""
            QGroupBox {
                background-color: #020617;
                border: 1px solid #334155;
                border-radius: 12px;
                margin-top: 10px;
                padding: 20px;
                font-weight: bold;
            }
            
            QGroupBox::title {
                color: #e2e8f0;
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }
            
            QLabel {
                color: #cbd5e1;
                background: transparent;
            }
            
            QPushButton {
                background-color: #1e40af;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 11pt;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #2563eb;
            }
            
            QPushButton:pressed {
                background-color: #1e3a8a;
            }
            
            QPushButton:disabled {
                background-color: #475569;
                color: #94a3b8;
            }
        """)
    
    def start_monitoring(self):
        """Запуск мониторинга"""
        # Проверяем РЕАЛЬНЫЙ статус через status_manager
        real_status = self.get_real_status()
        if real_status or self.is_running:
            self.add_log("⚠️ Мониторинг уже запущен", "warning")
            return
        
        try:
            self.add_log("🔄 Инициализация мониторинга...", "info")
            
            # Получаем настройки
            from settings_manager import get_settings_manager
            settings = get_settings_manager()
            url = settings.get_login_url()
            phone = settings.get_username()
            password = settings.get_password()
            
            if not all([url, phone, password]):
                self.add_log("❌ Не заполнены данные авторизации", "error")
                return
            
            self.add_log(f"📍 URL: {url}", "info")
            self.add_log(f"👤 Телефон: {phone}", "info")
            
            # Импортируем модуль онлайн-статистики
            try:
                from online_statistics import OnlineStatistics
                self.add_log("✅ Модуль online_statistics загружен", "success")
            except ImportError:
                self.add_log("❌ Модуль online_statistics.py не найден", "error")
                return
            
            # Создаём экземпляр
            self.online_stats = OnlineStatistics(
                url=url,
                phone=phone,
                password=password
            )
            self.add_log("✅ Экземпляр OnlineStatistics создан", "success")
            
            # Запускаем в QThread (не threading.Thread!)
            # Это важно для корректной остановки updater.py
            self.online_stats_thread = OnlineStatsWorkerThread(self.online_stats)
            self.online_stats_thread.error_signal.connect(
                lambda msg: self.add_log(msg, "error")
            )
            self.online_stats_thread.start()
            
            self.is_running = True
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
            self.add_log("✅ Мониторинг запущен в фоновом потоке", "success")
            self.add_log("⏱ Ожидайте авторизации и получения данных...", "info")
            self.status_label.setText("🟢 Запущен")
            self.status_label.setStyleSheet("color: #22c55e; font-weight: bold;")
            
        except Exception as e:
            self.add_log(f"❌ Ошибка запуска: {e}", "error")
            import traceback
            traceback.print_exc()
    

    def stop_monitoring(self):
        """Остановка мониторинга"""
        # Проверяем реальный статус
        real_status = self.get_real_status()
        if not real_status and not self.is_running:
            self.add_log("⚠️ Мониторинг не запущен", "warning")
            return
        
        try:
            from status_manager import get_status_manager
            status_manager = get_status_manager()
            
            # Запрашиваем остановку через status_manager
            # Это работает ВСЕГДА - и для вручную запущенного, и для автозапуска!
            status_manager.request_stop("online_stats")
            self.add_log("🛑 Отправлен запрос на остановку через status_manager", "info")
            
            # Дополнительно пытаемся остановить напрямую если есть ссылка
            if self.online_stats:
                self.online_stats.stop()
                self.add_log("🛑 Отправлена прямая команда остановки", "info")
            
            self.status_label.setText("🟡 Остановка...")
            self.status_label.setStyleSheet("color: #eab308; font-weight: bold;")
            
        except Exception as e:
            self.add_log(f"❌ Ошибка при остановке: {e}", "error")
        
        # Обновляем локальные флаги
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def check_status(self):
        """Проверка статуса и обновление отображения"""
        try:
            from status_manager import get_status_manager
            status_manager = get_status_manager()
            
            if "online_stats" in status_manager.status:
                stats_data = status_manager.status["online_stats"]
                
                # Обновляем отображение через сигнал
                self.stats_updated.emit(stats_data)

                # Синхронизируем состояние кнопок с реальным статусом
                real_running = stats_data.get("running", False)
                if real_running:
                    self.start_btn.setEnabled(False)
                    self.stop_btn.setEnabled(True)
                    self.is_running = True
                else:
                    self.start_btn.setEnabled(True)
                    self.stop_btn.setEnabled(False)
                    self.is_running = False
                
        except Exception as e:
            pass  # Игнорируем ошибки проверки статуса
    
    def update_stats_display(self, stats_data):
        """Обновление отображения статистики (вызывается из главного потока)"""
        try:
            if stats_data.get("running"):
                self.status_label.setText("🟢 Работает")
                self.status_label.setStyleSheet("color: #22c55e; font-weight: bold;")
            else:
                self.status_label.setText("🔴 Остановлен")
                self.status_label.setStyleSheet("color: #ef4444; font-weight: bold;")
            
            # Обновляем счетчики
            clients_count = stats_data.get("clients_count", 0)
            self.clients_label.setText(f"<b>{clients_count}</b>")
            
            sbor = stats_data.get("sbor", 0.0)
            self.sbor_label.setText(f"<b>{sbor:,.2f}</b> руб")
            
            # Премия
            premium = stats_data.get("premium", {})
            if isinstance(premium, dict):
                total_premium = premium.get("total_premium", 0.0)
                sbor_premium = premium.get("sbor_premium", 0.0)
                extensions_premium = premium.get("extensions_premium", 0.0)
                extensions_count = premium.get("extensions_count", 0)
                
                self.premium_label.setText(f"<b>{total_premium:,.2f}</b> руб")
                self.sbor_premium_label.setText(f"<b>{sbor_premium:,.2f}</b> руб")
                self.extensions_premium_label.setText(f"<b>{extensions_premium:,.2f}</b> руб")
                self.extensions_count_label.setText(f"<b>{extensions_count}</b> шт")
            
            # Время обновления
            from datetime import datetime
            current_time = datetime.now().strftime("%H:%M:%S")
            self.last_update_label.setText(current_time)
            
            # Ошибки
            if stats_data.get("last_error"):
                self.add_log(f"⚠️ {stats_data['last_error']}", "warning")
            
        except Exception as e:
            print(f"Ошибка обновления UI: {e}")
    
    def add_log(self, message, level="info"):
        """Добавление записи в лог"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Очищаем сообщение от лишних частей
        # Убираем префиксы типа "online_statistics - INFO - "
        clean_message = message
        if " - " in message:
            parts = message.split(" - ")
            if len(parts) >= 3:
                # Берём только текст сообщения (последняя часть)
                clean_message = parts[-1]
        
        # Автоопределение уровня по эмодзи в сообщении
        if level == "info":
            if any(emoji in clean_message for emoji in ["✅", "🟢"]):
                level = "success"
            elif any(emoji in clean_message for emoji in ["❌", "🔴"]):
                level = "error"
            elif any(emoji in clean_message for emoji in ["⚠️", "🟡"]):
                level = "warning"
        
        # Цвета для разных уровней
        colors = {
            "info": "#60a5fa",      # Синий
            "success": "#22c55e",   # Зелёный
            "warning": "#eab308",   # Жёлтый
            "error": "#ef4444"      # Красный
        }
        
        color = colors.get(level, "#cbd5e1")
        
        log_html = f'<span style="color: #64748b;">[{timestamp}]</span> <span style="color: {color};">{clean_message}</span>'
        
        self.logs_text.append(log_html)
        self.logs_text.verticalScrollBar().setValue(
            self.logs_text.verticalScrollBar().maximum()
        )
    
    def add_log_message(self, message, level):
        """Добавление лога через сигнал (для других потоков)"""
        self.add_log(message, level)
    
    def clear_logs(self):
        """Очистка логов"""
        self.logs_text.clear()
        self.add_log("🗑 Логи очищены", "info")