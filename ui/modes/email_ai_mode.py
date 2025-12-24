# -*- coding: utf-8 -*-
"""
📧 Email AI Agent Mode - ОБНОВЛЕННАЯ ВЕРСИЯ
Добавлено:
- Настройка имени коллектора
- Просмотр переписок с клиентами
- Управление диалогами (остановка/возобновление)
"""

from PyQt6.QtWidgets import (
    QLabel, QLineEdit, QFileDialog, QPushButton, QHBoxLayout, QMessageBox, QTextEdit,
    QComboBox, QWidget, QVBoxLayout, QGraphicsDropShadowEffect, QSpinBox,
    QListWidget, QListWidgetItem, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import threading
import os

from .base import ModeBase
from settings_manager import get_settings_manager


# =====================================================================
#  WORKER THREAD (БЕЗ ИЗМЕНЕНИЙ)
# =====================================================================

class EmailAIWorker(QThread):
    """Worker поток для Email AI процессора"""
    
    log_signal = pyqtSignal(str)
    stats_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    
    def __init__(self, processor, mode='monitor'):
        super().__init__()
        self.processor = processor
        self.mode = mode  # 'load_excel' или 'monitor'
        self.excel_path = None
        self.max_clients = 0  # ✨ НОВОЕ
        self.stop_flag = threading.Event()
    
    def run(self):
        """Основной цикл работы"""
        try:
            if self.mode == 'load_excel' and self.excel_path:
                self._load_excel()
            elif self.mode == 'monitor':
                self._monitor_loop()
        except Exception as e:
            self.error_signal.emit(f"Ошибка: {e}")
        finally:
            self.finished_signal.emit()
    
    def _load_excel(self):
        """Загрузка клиентов из Excel"""
        self.log_signal.emit(f"📊 Загружаю Excel: {self.excel_path}")
        
        try:
            # ✨ НОВОЕ: Передаём max_clients
            processed_clients = self.processor.process_excel(
                self.excel_path, 
                max_clients=self.max_clients
            )
            
            sent_count = len(processed_clients)
            self.log_signal.emit(f"✅ Загружено клиентов: {sent_count}")
            
            if processed_clients:
                self.log_signal.emit("📋 Первые клиенты:")
                for client in processed_clients[:5]:
                    self.log_signal.emit(f"  • {client['fio']} ({client['email']})")
                
                if len(processed_clients) > 5:
                    self.log_signal.emit(f"  ... и ещё {len(processed_clients) - 5}")
            
            stats = {'loaded': sent_count}
            self.stats_signal.emit(stats)
            
        except Exception as e:
            self.error_signal.emit(f"Ошибка загрузки Excel: {e}")
    
    def _monitor_loop(self):
        """Цикл мониторинга входящих писем"""
        self.log_signal.emit("🔄 Запущен мониторинг входящих писем")
        
        check_interval = self.processor.check_interval
        
        while not self.stop_flag.is_set():
            try:
                self.processor.check_incoming_emails()
                
                try:
                    stats = self.processor.get_statistics()
                    self.stats_signal.emit(stats)
                except:
                    pass
                
                for _ in range(check_interval * 10):
                    if self.stop_flag.is_set():
                        break
                    self.msleep(100)
                    
            except Exception as e:
                self.log_signal.emit(f"❌ Ошибка мониторинга: {e}")
                self.msleep(5000)
        
        self.log_signal.emit("⏸ Мониторинг остановлен")
    
    def stop(self):
        """Остановка worker'а"""
        self.log_signal.emit("⏹ Остановка...")
        self.stop_flag.set()


# =====================================================================
#  UI MODE (ОБНОВЛЕННАЯ ВЕРСИЯ)
# =====================================================================

class EmailAIMode(ModeBase):
    """Режим Email AI Agent"""

    def __init__(self, parent=None):
        super().__init__(
            title="📧 Email AI Agent",
            description="Автоматическая обработка email-переписки с клиентами через ChatGPT",
            parent=parent
        )

        self.worker = None
        self.processor = None
        self.selected_file = None
        self.is_monitoring = False
        self.stats = {
            'loaded': 0,
            'sent': 0,
            'received': 0,
            'active': 0,
            'stopped': 0
        }
        
        # Для просмотра диалогов
        self.current_dialog_email = None

        self.init_mode_ui()
        self.load_settings()

    # =====================================================================
    #  UI
    # =====================================================================

    def init_mode_ui(self):

        # ------------------------------------------------------------
        # HERO CARD
        # ------------------------------------------------------------

        hero = QWidget()
        hero.setObjectName("emailHero")
        hero_l = QVBoxLayout(hero)
        hero_l.setContentsMargins(18, 18, 18, 14)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 180))
        hero.setGraphicsEffect(shadow)

        hero.setStyleSheet("""
            #emailHero {
                background-color: #0a0f1a;
                border-radius: 18px;
                border: 1px solid rgba(56,189,248,0.55);
            }
            #emailHero QLabel {
                color: #e5e7eb;
            }
        """)

        t = QLabel("📧 Email AI Agent")
        t.setFont(QFont("Segoe UI Semibold", 14))

        st = QLabel(
            "Автоматическая обработка писем клиентов через ChatGPT\n"
            "1) Загрузи Excel с клиентами → 2) Настрой стиль и задержки → 3) Запусти мониторинг"
        )
        st.setFont(QFont("Segoe UI", 10))
        st.setWordWrap(True)

        badge = QLabel("AI-POWERED EMAIL AUTOMATION")
        badge.setFont(QFont("Segoe UI Semibold", 9))
        badge.setStyleSheet("""
            QLabel {
                color: #38bdf8;
                background-color: #0f172a;
                border: 1px solid rgba(56,189,248,0.6);
                border-radius: 999px;
                padding: 4px 10px;
            }
        """)

        hero_l.addWidget(t)
        hero_l.addWidget(st)
        hero_l.addSpacing(4)
        hero_l.addWidget(badge)

        self.content_layout.addWidget(hero)

        # ------------------------------------------------------------
        # GMAIL SETTINGS
        # ------------------------------------------------------------

        email_section, email_l = self.create_section(
            "📧 Настройки Gmail",
            "Укажи свой Gmail и App Password для отправки писем"
        )

        # Email
        email_row = QHBoxLayout()
        email_label = QLabel("Email:")
        email_label.setMinimumWidth(120)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your@gmail.com")
        self.email_input.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                color: #e5e7eb;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
        """)
        email_row.addWidget(email_label)
        email_row.addWidget(self.email_input)

        # Password
        pass_row = QHBoxLayout()
        pass_label = QLabel("App Password:")
        pass_label.setMinimumWidth(120)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("xxxx xxxx xxxx xxxx")
        self.password_input.setStyleSheet(self.email_input.styleSheet())
        pass_row.addWidget(pass_label)
        pass_row.addWidget(self.password_input)
        
        # ✨ НОВОЕ: Имя коллектора
        name_row = QHBoxLayout()
        name_label = QLabel("Имя коллектора:")
        name_label.setMinimumWidth(120)
        self.collector_name_input = QLineEdit()
        self.collector_name_input.setPlaceholderText("Руслан")
        self.collector_name_input.setToolTip("Имя от которого будет вестись переписка с клиентами")
        self.collector_name_input.setStyleSheet(self.email_input.styleSheet())
        name_row.addWidget(name_label)
        name_row.addWidget(self.collector_name_input)
        
        # Подсказка под полем
        name_hint = QLabel("Это имя будет использоваться в ответах клиентам")
        name_hint.setStyleSheet("color: #6b7280; font-size: 11px; padding-left: 120px;")
        name_hint.setWordWrap(True)

        email_l.addLayout(email_row)
        email_l.addLayout(pass_row)
        email_l.addLayout(name_row)
        email_l.addWidget(name_hint)

        self.content_layout.addWidget(email_section)

        # ------------------------------------------------------------
        # AI SETTINGS
        # ------------------------------------------------------------

        ai_section, ai_l = self.create_section(
            "🤖 Настройки ИИ и рассылки",
            "Настрой поведение бота, задержки и лимиты отправки"
        )

        # Style
        style_row = QHBoxLayout()
        style_label = QLabel("Стиль общения:")
        style_label.setMinimumWidth(120)
        self.ai_style_combo = QComboBox()
        self.ai_style_combo.addItems(["soft", "medium", "hard"])
        self.ai_style_combo.setCurrentText("medium")
        self.ai_style_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                color: #e5e7eb;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QComboBox:hover {
                border: 1px solid #38bdf8;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #0f172a;
                color: #e5e7eb;
                selection-background-color: #1e40af;
            }
        """)
        style_row.addWidget(style_label)
        style_row.addWidget(self.ai_style_combo)

        # Interval
        interval_row = QHBoxLayout()
        interval_label = QLabel("Интервал проверки писем:")
        interval_label.setMinimumWidth(120)
        self.interval_spin = QSpinBox()
        self.interval_spin.setMinimum(10)
        self.interval_spin.setMaximum(600)
        self.interval_spin.setValue(60)
        self.interval_spin.setSuffix(" сек")
        self.interval_spin.setToolTip("Как часто проверять новые письма от клиентов (рекомендуется 60-120 сек)")
        self.interval_spin.setStyleSheet("""
            QSpinBox {
                background-color: #0f172a;
                color: #e5e7eb;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
        """)
        interval_row.addWidget(interval_label)
        interval_row.addWidget(self.interval_spin)
        
        # Подсказка под полем
        interval_hint = QLabel("Как часто проверять входящие письма от клиентов")
        interval_hint.setStyleSheet("color: #6b7280; font-size: 11px; padding-left: 120px;")
        interval_hint.setWordWrap(True)

        # ✨ НОВОЕ: Задержка между письмами
        send_delay_row = QHBoxLayout()
        send_delay_label = QLabel("Задержка при отправке:")
        send_delay_label.setMinimumWidth(120)
        self.send_delay_spin = QSpinBox()
        self.send_delay_spin.setMinimum(10)
        self.send_delay_spin.setMaximum(300)
        self.send_delay_spin.setValue(60)
        self.send_delay_spin.setSuffix(" сек")
        self.send_delay_spin.setToolTip("Пауза между отправкой писем, чтобы не попасть в спам-фильтр (рекомендуется 60+ сек)")
        self.send_delay_spin.setStyleSheet(self.interval_spin.styleSheet())
        send_delay_row.addWidget(send_delay_label)
        send_delay_row.addWidget(self.send_delay_spin)
        
        # Подсказка под полем
        send_delay_hint = QLabel("Пауза между отправкой писем клиентам (защита от спам-фильтров)")
        send_delay_hint.setStyleSheet("color: #6b7280; font-size: 11px; padding-left: 120px;")
        send_delay_hint.setWordWrap(True)
        
        # ✨ НОВОЕ: Лимит клиентов
        max_clients_row = QHBoxLayout()
        max_clients_label = QLabel("Макс. клиентов из Excel:")
        max_clients_label.setMinimumWidth(120)
        self.max_clients_spin = QSpinBox()
        self.max_clients_spin.setMinimum(0)
        self.max_clients_spin.setMaximum(1000)
        self.max_clients_spin.setValue(0)
        self.max_clients_spin.setSpecialValueText("Без лимита")
        self.max_clients_spin.setToolTip("Ограничить количество клиентов при загрузке Excel (0 = отправить всем)")
        self.max_clients_spin.setStyleSheet(self.interval_spin.styleSheet())
        max_clients_row.addWidget(max_clients_label)
        max_clients_row.addWidget(self.max_clients_spin)
        
        # Подсказка под полем
        max_clients_hint = QLabel("Сколько клиентов взять из Excel файла (0 = отправить всем)")
        max_clients_hint.setStyleSheet("color: #6b7280; font-size: 11px; padding-left: 120px;")
        max_clients_hint.setWordWrap(True)
        
        # ✨ НОВОЕ: Задержка перед ответом
        reply_delay_row = QHBoxLayout()
        reply_delay_label = QLabel("Задержка перед ответом:")
        reply_delay_label.setMinimumWidth(120)
        self.reply_delay_spin = QSpinBox()
        self.reply_delay_spin.setMinimum(30)
        self.reply_delay_spin.setMaximum(600)
        self.reply_delay_spin.setValue(120)
        self.reply_delay_spin.setSuffix(" сек")
        self.reply_delay_spin.setToolTip("Сколько ждать перед ответом клиенту (имитация 'печатает...', рекомендуется 60-180 сек)")
        self.reply_delay_spin.setStyleSheet(self.interval_spin.styleSheet())
        reply_delay_row.addWidget(reply_delay_label)
        reply_delay_row.addWidget(self.reply_delay_spin)
        
        # Подсказка под полем
        reply_delay_hint = QLabel("Время 'думания' перед ответом клиенту (чтобы выглядело естественно)")
        reply_delay_hint.setStyleSheet("color: #6b7280; font-size: 11px; padding-left: 120px;")
        reply_delay_hint.setWordWrap(True)

        ai_l.addLayout(style_row)
        ai_l.addLayout(interval_row)
        ai_l.addWidget(interval_hint)
        ai_l.addSpacing(8)
        ai_l.addLayout(send_delay_row)
        ai_l.addWidget(send_delay_hint)
        ai_l.addSpacing(8)
        ai_l.addLayout(max_clients_row)
        ai_l.addWidget(max_clients_hint)
        ai_l.addSpacing(8)
        ai_l.addLayout(reply_delay_row)
        ai_l.addWidget(reply_delay_hint)

        # Save button
        save_btn = QPushButton("💾 Сохранить настройки")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e3a8a;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1e40af;
            }
        """)
        ai_l.addWidget(save_btn)

        self.content_layout.addWidget(ai_section)

        # ------------------------------------------------------------
        # FILE UPLOAD
        # ------------------------------------------------------------

        file_section, file_l = self.create_section(
            "📁 Загрузка Excel",
            "Выбери файл с клиентами и начни рассылку"
        )

        file_row = QHBoxLayout()
        self.file_path_label = QLabel("Файл не выбран")
        self.file_path_label.setStyleSheet("color: #6b7280;")
        choose_file_btn = QPushButton("📂 Выбрать файл")
        choose_file_btn.clicked.connect(self.choose_file)
        choose_file_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        file_row.addWidget(self.file_path_label, 1)
        file_row.addWidget(choose_file_btn)

        file_l.addLayout(file_row)

        # Load button
        self.load_btn = QPushButton("📤 Загрузить и отправить письма")
        self.load_btn.clicked.connect(self.load_excel)
        self.load_btn.setEnabled(False)
        self.load_btn.setStyleSheet("""
            QPushButton {
                background-color: #15803d;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #6b7280;
            }
        """)
        file_l.addWidget(self.load_btn)

        self.content_layout.addWidget(file_section)

        # ------------------------------------------------------------
        # MONITORING CONTROL
        # ------------------------------------------------------------

        control_section, control_l = self.create_section(
            "🎮 Управление мониторингом",
            "Запусти или останови проверку входящих писем"
        )

        control_row = QHBoxLayout()

        self.start_btn = QPushButton("▶ Запустить мониторинг")
        self.start_btn.clicked.connect(self.start_monitoring)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #15803d;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #6b7280;
            }
        """)

        self.stop_btn = QPushButton("⏹ Остановить")
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #991b1b;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #6b7280;
            }
        """)

        control_row.addWidget(self.start_btn)
        control_row.addWidget(self.stop_btn)

        control_l.addLayout(control_row)

        self.content_layout.addWidget(control_section)
        
        # ------------------------------------------------------------
        # ✨ НОВОЕ: ПРОСМОТР ДИАЛОГОВ
        # ------------------------------------------------------------

        dialogs_section, dialogs_l = self.create_section(
            "💬 Просмотр диалогов",
            "Просматривай переписку с клиентами и управляй диалогами"
        )
        
        # Кнопка обновить список
        refresh_btn = QPushButton("🔄 Обновить список диалогов")
        refresh_btn.clicked.connect(self.refresh_dialogs_list)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        dialogs_l.addWidget(refresh_btn)
        
        # Список клиентов с диалогами
        self.dialogs_list = QListWidget()
        self.dialogs_list.setStyleSheet("""
            QListWidget {
                background-color: #0f172a;
                color: #e5e7eb;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }
            QListWidget::item:selected {
                background-color: #1e40af;
            }
            QListWidget::item:hover {
                background-color: #1e3a8a;
            }
        """)
        self.dialogs_list.setMaximumHeight(200)
        self.dialogs_list.itemClicked.connect(self.on_dialog_selected)
        dialogs_l.addWidget(self.dialogs_list)
        
        # Просмотр диалога
        dialog_label = QLabel("Выбранный диалог:")
        dialog_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        dialogs_l.addWidget(dialog_label)
        
        self.dialog_display = QTextEdit()
        self.dialog_display.setReadOnly(True)
        self.dialog_display.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                color: #e5e7eb;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 12px;
                font-size: 13px;
                font-family: 'Segoe UI', monospace;
            }
        """)
        self.dialog_display.setMaximumHeight(300)
        self.dialog_display.setPlaceholderText("Выберите клиента из списка выше...")
        dialogs_l.addWidget(self.dialog_display)
        
        # Кнопки управления диалогом
        dialog_control_row = QHBoxLayout()
        
        self.stop_dialog_btn = QPushButton("🛑 Остановить диалог")
        self.stop_dialog_btn.clicked.connect(self.stop_dialog_manual)
        self.stop_dialog_btn.setEnabled(False)
        self.stop_dialog_btn.setStyleSheet("""
            QPushButton {
                background-color: #991b1b;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #6b7280;
            }
        """)
        
        self.resume_dialog_btn = QPushButton("▶️ Возобновить диалог")
        self.resume_dialog_btn.clicked.connect(self.resume_dialog)
        self.resume_dialog_btn.setEnabled(False)
        self.resume_dialog_btn.setStyleSheet("""
            QPushButton {
                background-color: #15803d;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #6b7280;
            }
        """)
        
        dialog_control_row.addWidget(self.stop_dialog_btn)
        dialog_control_row.addWidget(self.resume_dialog_btn)
        
        dialogs_l.addLayout(dialog_control_row)
        
        self.content_layout.addWidget(dialogs_section)

        # ------------------------------------------------------------
        # STATS
        # ------------------------------------------------------------

        stats_section, stats_l = self.create_section(
            "📊 Статистика",
            "Текущее состояние системы"
        )

        stats_grid = QHBoxLayout()

        self.loaded_label = QLabel("Загружено: 0")
        self.sent_label = QLabel("Отправлено: 0")
        self.received_label = QLabel("Получено: 0")
        self.active_label = QLabel("Активных: 0")
        self.stopped_label = QLabel("Остановлено: 0")

        for lbl in [self.loaded_label, self.sent_label, self.received_label, self.active_label, self.stopped_label]:
            lbl.setStyleSheet("""
                QLabel {
                    background-color: #0f172a;
                    color: #38bdf8;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 13px;
                    font-weight: 600;
                }
            """)
            stats_grid.addWidget(lbl)

        stats_l.addLayout(stats_grid)

        self.content_layout.addWidget(stats_section)

        # ------------------------------------------------------------
        # LOG OUTPUT
        # ------------------------------------------------------------

        log_section, log_l = self.create_section(
            "📜 Лог событий",
            "Вся активность системы в реальном времени"
        )

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #0a0f1a;
                color: #9ca3af;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        self.log_output.setMinimumHeight(200)

        log_l.addWidget(self.log_output)

        self.content_layout.addWidget(log_section)

        self.content_layout.addStretch()

    # =====================================================================
    #  SETTINGS
    # =====================================================================

    def load_settings(self):
        """Загрузка настроек"""
        sm = get_settings_manager()
        email_settings = sm.get_email_settings()
        
        self.email_input.setText(email_settings.get('gmail_email', ''))
        self.password_input.setText(email_settings.get('gmail_app_password', ''))
        self.ai_style_combo.setCurrentText(email_settings.get('ai_style', 'medium'))
        self.interval_spin.setValue(email_settings.get('check_interval', 60))
        self.collector_name_input.setText(email_settings.get('collector_name', 'Руслан'))
        self.send_delay_spin.setValue(email_settings.get('send_delay', 60))  # ✨ НОВОЕ
        self.max_clients_spin.setValue(email_settings.get('max_clients', 0))  # ✨ НОВОЕ
        self.reply_delay_spin.setValue(email_settings.get('reply_delay', 120))  # ✨ НОВОЕ
        
        # Активируем кнопки если настройки уже есть
        if email_settings.get('gmail_email') and email_settings.get('gmail_app_password'):
            self.start_btn.setEnabled(True)
            self.add_log("✅ Настройки загружены, мониторинг доступен")

    def save_settings(self):
        """Сохранение настроек"""
        sm = get_settings_manager()
        sm.set_email_settings(
            gmail_email=self.email_input.text(),
            gmail_app_password=self.password_input.text(),
            ai_style=self.ai_style_combo.currentText(),
            check_interval=self.interval_spin.value(),
            collector_name=self.collector_name_input.text() or "Руслан",
            send_delay=self.send_delay_spin.value(),  # ✨ НОВОЕ
            max_clients=self.max_clients_spin.value(),  # ✨ НОВОЕ
            reply_delay=self.reply_delay_spin.value()  # ✨ НОВОЕ
        )
        
        self.add_log("✅ Настройки сохранены")
        
        # Проверяем можно ли активировать кнопки
        if self.email_input.text() and self.password_input.text():
            self.load_btn.setEnabled(True)
            self.start_btn.setEnabled(True)

    # =====================================================================
    #  FILE OPERATIONS
    # =====================================================================

    def choose_file(self):
        """Выбор Excel файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите Excel файл",
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        
        if file_path:
            self.selected_file = file_path
            base = os.path.basename(file_path)
            self.file_path_label.setText(base)
            self.file_path_label.setStyleSheet("color: #4ade80;")
            self.add_log(f"📁 Выбран файл: {base}")
            self.load_btn.setEnabled(True)
        else:
            self.selected_file = None
            self.file_path_label.setText("Файл не выбран")
            self.file_path_label.setStyleSheet("color: #6b7280;")

    def load_excel(self):
        """Загрузка клиентов из Excel"""
        if not self.selected_file:
            QMessageBox.warning(self, "Ошибка", "Выберите Excel файл!")
            return
        
        if not self.email_input.text() or not self.password_input.text():
            QMessageBox.warning(self, "Ошибка", "Заполните Email и App Password!")
            return
        
        # Инициализируем процессор
        if not self.processor:
            self._init_processor()
        
        if not self.processor:
            return
        
        # Отключаем кнопки
        self.load_btn.setEnabled(False)
        
        # Запускаем worker
        self.worker = EmailAIWorker(self.processor, mode='load_excel')
        self.worker.excel_path = self.selected_file
        self.worker.max_clients = self.max_clients_spin.value()  # ✨ НОВОЕ
        self.worker.log_signal.connect(self.add_log)
        self.worker.stats_signal.connect(self.update_stats)
        self.worker.finished_signal.connect(self.on_load_finished)
        self.worker.error_signal.connect(self.on_worker_error)
        self.worker.start()
        
        self.add_log("=" * 60)
        self.add_log("⏳ Начинаю рассылку писем...")
        self.add_log("=" * 60)

        if hasattr(self.parent(), 'register_worker'):
            self.parent().register_worker(self.worker)

    def on_load_finished(self):
        """Завершение загрузки"""
        self.load_btn.setEnabled(True)
        self.add_log("=" * 60)
        self.add_log("✅ Рассылка завершена")
        self.add_log("=" * 60)

    # =====================================================================
    #  MONITORING
    # =====================================================================

    def start_monitoring(self):
        """Запуск мониторинга"""
        if not self.processor:
            self._init_processor()
        
        if not self.processor:
            return
        
        if self.is_monitoring:
            self.add_log("⚠️ Мониторинг уже запущен")
            return
        
        # Отключаем кнопки
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.load_btn.setEnabled(False)
        
        # Запускаем worker
        self.worker = EmailAIWorker(self.processor, mode='monitor')
        self.worker.log_signal.connect(self.add_log)
        self.worker.stats_signal.connect(self.update_stats)
        self.worker.finished_signal.connect(self.on_monitoring_stopped)
        self.worker.error_signal.connect(self.on_worker_error)
        self.worker.start()
        
        self.is_monitoring = True
        
        self.add_log("=" * 60)
        self.add_log("▶ Мониторинг запущен")
        self.add_log("=" * 60)

        if hasattr(self.parent(), 'register_worker'):
            self.parent().register_worker(self.worker)

    def stop_monitoring(self):
        """Остановка мониторинга"""
        if not self.is_monitoring:
            return
        
        self.add_log("⏹ Остановка мониторинга...")
        
        if self.worker:
            self.worker.stop()

    def on_monitoring_stopped(self):
        """Обработка остановки мониторинга"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.load_btn.setEnabled(True)
        self.is_monitoring = False
        
        self.add_log("=" * 60)
        self.add_log("⏸ Мониторинг остановлен")
        self.add_log("=" * 60)
    
    # =====================================================================
    #  ✨ НОВОЕ: ПРОСМОТР ДИАЛОГОВ
    # =====================================================================
    
    def refresh_dialogs_list(self):
        """Обновление списка диалогов"""
        if not self.processor:
            self._init_processor()
        
        if not self.processor:
            QMessageBox.warning(self, "Ошибка", "Процессор не инициализирован!")
            return
        
        try:
            # Получаем список клиентов с диалогами
            clients = self.processor.get_clients_with_dialogs()
            
            self.dialogs_list.clear()
            
            if not clients:
                self.add_log("⚠️ Нет клиентов с переписками")
                return
            
            for client in clients:
                status_icon = "✅" if client['status'] == 'active' else "🛑"
                item_text = f"{status_icon} {client['fio']} ({client['messages_count']} сообщений)"
                
                if client['status'] == 'stopped':
                    item_text += f" - ОСТАНОВЛЕНО: {client['stop_reason']}"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, client['email'])
                self.dialogs_list.addItem(item)
            
            self.add_log(f"✅ Загружено диалогов: {len(clients)}")
            
        except Exception as e:
            self.add_log(f"❌ Ошибка загрузки диалогов: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить диалоги: {e}")
    
    def on_dialog_selected(self, item):
        """Обработка выбора диалога"""
        email = item.data(Qt.ItemDataRole.UserRole)
        self.current_dialog_email = email
        
        try:
            # Получаем историю диалога
            history = self.processor.get_dialog_history_full(email)
            
            if not history:
                self.dialog_display.setPlainText("Нет сообщений в диалоге")
                return
            
            # Получаем инфо о клиенте
            client = self.processor._get_client_from_db(email)
            
            # Формируем текст
            dialog_text = f"📧 {client['fio']} ({email})\n"
            dialog_text += f"💰 Долг: {client['debt']:.2f}₽ | ⏰ Просрочка: {client['days']} дн.\n"
            dialog_text += f"📊 Статус: {client['status'].upper()}\n"
            dialog_text += "=" * 70 + "\n\n"
            
            # Добавляем сообщения (пропускаем ПЕРВОЕ наше сообщение)
            first_assistant_skipped = False
            
            for msg in history:
                # Пропускаем первое assistant сообщение
                if msg['role'] == 'assistant' and not first_assistant_skipped:
                    first_assistant_skipped = True
                    continue
                
                role_icon = "👤 Клиент" if msg['role'] == 'user' else "🤖 Коллектор"
                timestamp = msg['timestamp'][:19]  # Обрезаем миллисекунды
                
                dialog_text += f"{role_icon} [{timestamp}]:\n"
                dialog_text += f"{msg['content']}\n\n"
            
            self.dialog_display.setPlainText(dialog_text)
            
            # Активируем кнопки в зависимости от статуса
            if client['status'] == 'active':
                self.stop_dialog_btn.setEnabled(True)
                self.resume_dialog_btn.setEnabled(False)
            else:
                self.stop_dialog_btn.setEnabled(False)
                self.resume_dialog_btn.setEnabled(True)
            
        except Exception as e:
            self.add_log(f"❌ Ошибка загрузки диалога: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить диалог: {e}")
    
    def stop_dialog_manual(self):
        """Остановка диалога вручную"""
        if not self.current_dialog_email:
            return
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Остановить диалог с {self.current_dialog_email}?\n"
            "Система больше не будет отвечать этому клиенту.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.processor.stop_client_dialog_manual(self.current_dialog_email)
                self.add_log(f"🛑 Диалог остановлен: {self.current_dialog_email}")
                self.refresh_dialogs_list()
                
                # Обновляем отображение текущего диалога
                for i in range(self.dialogs_list.count()):
                    item = self.dialogs_list.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == self.current_dialog_email:
                        self.on_dialog_selected(item)
                        break
                
            except Exception as e:
                self.add_log(f"❌ Ошибка остановки диалога: {e}")
                QMessageBox.critical(self, "Ошибка", f"Не удалось остановить диалог: {e}")
    
    def resume_dialog(self):
        """Возобновление диалога"""
        if not self.current_dialog_email:
            return
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Возобновить диалог с {self.current_dialog_email}?\n"
            "Система снова начнёт отвечать на письма от этого клиента.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.processor.resume_client_dialog(self.current_dialog_email)
                self.add_log(f"▶️ Диалог возобновлён: {self.current_dialog_email}")
                self.refresh_dialogs_list()
                
                # Обновляем отображение текущего диалога
                for i in range(self.dialogs_list.count()):
                    item = self.dialogs_list.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == self.current_dialog_email:
                        self.on_dialog_selected(item)
                        break
                
            except Exception as e:
                self.add_log(f"❌ Ошибка возобновления диалога: {e}")
                QMessageBox.critical(self, "Ошибка", f"Не удалось возобновить диалог: {e}")

    # =====================================================================
    #  PROCESSOR
    # =====================================================================

    def _init_processor(self):
        """Инициализация Email AI процессора"""
        try:
            from core.email_ai_processor import EmailAIProcessor
            
            sm = get_settings_manager()
            email_settings = sm.get_email_settings()
            
            self.processor = EmailAIProcessor(
                gmail_email=email_settings.get('gmail_email', ''),
                gmail_app_password=email_settings.get('gmail_app_password', ''),
                ai_style=email_settings.get('ai_style', 'medium'),
                collector_name=email_settings.get('collector_name', 'Руслан'),  # ✨ НОВОЕ
                send_delay=email_settings.get('send_delay', 60),  # ✨ НОВОЕ
                reply_delay=email_settings.get('reply_delay', 120)  # ✨ НОВОЕ
            )

            # Устанавливаем интервал
            self.processor.check_interval = email_settings.get('check_interval', 60)
            
            self.add_log("✅ Процессор инициализирован")
            
        except Exception as e:
            self.add_log(f"❌ Ошибка инициализации: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось инициализировать процессор: {e}")
            self.processor = None

    # =====================================================================
    #  STATS & LOGS
    # =====================================================================

    def update_stats(self, stats):
        """Обновление статистики"""
        self.stats.update(stats)
        
        self.loaded_label.setText(f"Загружено: {self.stats.get('loaded', 0)}")
        self.sent_label.setText(f"Отправлено: {self.stats.get('sent', 0)}")
        self.received_label.setText(f"Получено: {self.stats.get('received', 0)}")
        self.active_label.setText(f"Активных: {self.stats.get('active', 0)}")
        self.stopped_label.setText(f"Остановлено: {self.stats.get('stopped', 0)}")

    def add_log(self, msg):
        """Добавление в лог"""
        self.log_output.append(msg)
        s = self.log_output.verticalScrollBar()
        s.setValue(s.maximum())

    def on_worker_error(self, msg):
        """Обработка ошибок worker'а"""
        self.add_log(f"❌ Ошибка: {msg}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.load_btn.setEnabled(True)
        self.is_monitoring = False