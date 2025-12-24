"""
💳 Отправка ссылок на оплату — Dark Futuristic Corporate UI (QT-SAFE EDITION)
Полноценный премиальный интерфейс с реальными Qt-эффектами (тенями),
без неподдерживаемых веб-CSS свойств.
"""

from PyQt6.QtWidgets import (
    QLabel, QLineEdit, QPushButton, QCheckBox,
    QHBoxLayout, QMessageBox, QTextEdit, QVBoxLayout, QWidget,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import threading
import os
import sys

from .base import ModeBase
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from settings_manager import get_settings_manager

# === Импорт процессора ссылок ===
try:
    from core.payment_links_processor import process_payment_links
    PROCESSOR_AVAILABLE = True
except ImportError:
    PROCESSOR_AVAILABLE = False
    print("⚠️ payment_links_processor не найден!")


# =====================================================================
# WORKER
# =====================================================================

class PaymentLinksWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, login_url, username, password, use_delay_search=False, 
                 delay_from="", delay_to="", max_links=None):
        super().__init__()
        self.login_url = login_url
        self.username = username
        self.password = password
        self.use_delay_search = use_delay_search
        self.delay_from = delay_from
        self.delay_to = delay_to
        self.max_links = max_links
        self.stop_flag = threading.Event()

    def logger_func(self, message):
        self.log_signal.emit(message)

    def run(self):
        if not PROCESSOR_AVAILABLE:
            self.error_signal.emit("Процессор отправки ссылок не доступен!")
            return

        try:
            self.log_signal.emit("🚀 Запуск отправки ссылок на оплату...")
            process_payment_links(
                self.login_url,
                self.username,
                self.password,
                self.logger_func,
                self.stop_flag,
                use_delay_search=self.use_delay_search,
                delay_from=self.delay_from,
                delay_to=self.delay_to,
                max_links=self.max_links
            )
            self.finished_signal.emit()
        except Exception as e:
            self.error_signal.emit(str(e))

    def stop(self):
        self.log_signal.emit("⏹️ Остановка...")
        self.stop_flag.set()


# =====================================================================
# UI MODE
# =====================================================================

class PaymentLinksMode(ModeBase):

    def __init__(self, parent=None):
        super().__init__(
            title="Отправка ссылок на оплату",
            description="Массовая отправка платёжных ссылок клиентам",
            parent=parent
        )

        self.settings = get_settings_manager()
        self.worker = None
        self.init_mode_ui()

    # =====================================================================
    # DARK FUTURISTIC UI
    # =====================================================================

    def init_mode_ui(self):

        # ------------------------------------------------------------
        # HERO CARD (with shadow)
        # ------------------------------------------------------------
        hero = QWidget()
        hero.setObjectName("paymentHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(18, 18, 18, 14)

        # SHADOW EFFECT
        hero_shadow = QGraphicsDropShadowEffect(self)
        hero_shadow.setBlurRadius(40)
        hero_shadow.setOffset(0, 6)
        hero_shadow.setColor(QColor(0, 0, 0, 180))
        hero.setGraphicsEffect(hero_shadow)

        title = QLabel("💳 Отправка ссылок на оплату")
        title.setFont(QFont("Segoe UI Semibold", 14))

        subtitle = QLabel(
            "Система автоматически отправляет платёжные ссылки клиентам.\n"
            "Поддерживает фильтрацию по дням просрочки и ограничение количества."
        )
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setWordWrap(True)

        badge = QLabel("PAYMENT LINK ENGINE")
        badge.setFont(QFont("Segoe UI Semibold", 9))

        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        hero_layout.addSpacing(4)
        hero_layout.addWidget(badge)

        hero.setStyleSheet("""
            #paymentHero {
                background-color: #0a0f1a;
                border-radius: 18px;
                border: 1px solid rgba(34,197,94,0.55);
            }
            #paymentHero QLabel {
                color: #e5e7eb;
            }
        """)

        badge.setStyleSheet("""
            QLabel {
                color: #22c55e;
                padding: 4px 10px;
                border-radius: 999px;
                background-color: #0f172a;
                border: 1px solid rgba(34,197,94,0.5);
            }
        """)

        self.content_layout.addWidget(hero)

        # ------------------------------------------------------------
        # ФИЛЬТР ПО ДНЯМ ПРОСРОЧКИ
        # ------------------------------------------------------------
        filter_section, filter_layout = self.create_section(
            "🔍 Фильтр по дням просрочки"
        )
        filter_section.setObjectName("paymentFilter")

        filter_section.setStyleSheet("""
            #paymentFilter {
                background-color: #020617;
                border-radius: 16px;
                border: 1px solid rgba(148,163,184,0.55);
            }
            #paymentFilter QLabel {
                color: #e5e7eb;
                font-size: 10.5pt;
            }
            #paymentFilter QCheckBox {
                color: #e5e7eb;
                font-size: 11pt;
            }
        """)

        self.use_delay_filter = QCheckBox("Использовать фильтр по просрочке")
        filter_layout.addWidget(self.use_delay_filter)

        # Поля От/До
        delay_inputs = QHBoxLayout()
        
        delay_from_label = QLabel("От:")
        delay_inputs.addWidget(delay_from_label)
        
        self.delay_from_input = QLineEdit()
        self.delay_from_input.setPlaceholderText("дней")
        self.delay_from_input.setMaximumWidth(100)
        self.delay_from_input.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                color: #e5e7eb;
                padding: 6px 10px;
                border-radius: 8px;
                border: 1px solid rgba(51,65,85,0.6);
            }
        """)
        delay_inputs.addWidget(self.delay_from_input)
        
        delay_to_label = QLabel("До:")
        delay_inputs.addWidget(delay_to_label)
        
        self.delay_to_input = QLineEdit()
        self.delay_to_input.setPlaceholderText("дней")
        self.delay_to_input.setMaximumWidth(100)
        self.delay_to_input.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                color: #e5e7eb;
                padding: 6px 10px;
                border-radius: 8px;
                border: 1px solid rgba(51,65,85,0.6);
            }
        """)
        delay_inputs.addWidget(self.delay_to_input)
        
        delay_inputs.addStretch()
        filter_layout.addLayout(delay_inputs)

        self.content_layout.addWidget(filter_section)

        # ------------------------------------------------------------
        # КОЛИЧЕСТВО ССЫЛОК
        # ------------------------------------------------------------
        count_section, count_layout = self.create_section(
            "🎯 Ограничение количества"
        )
        count_section.setObjectName("paymentCount")

        count_section.setStyleSheet("""
            #paymentCount {
                background-color: #020617;
                border-radius: 16px;
                border: 1px solid rgba(148,163,184,0.55);
            }
            #paymentCount QLabel {
                color: #e5e7eb;
                font-size: 10.5pt;
            }
        """)

        count_info = QLabel(
            "Укажите максимальное количество ссылок для отправки.\n"
            "Оставьте пустым для отправки всех."
        )
        count_info.setWordWrap(True)
        count_info.setStyleSheet("color: #94a3b8;")
        count_layout.addWidget(count_info)

        # Поле ввода количества
        count_inputs = QHBoxLayout()
        
        count_label = QLabel("Отправить:")
        count_inputs.addWidget(count_label)
        
        self.max_links_input = QLineEdit()
        self.max_links_input.setPlaceholderText("150")
        self.max_links_input.setMaximumWidth(120)
        self.max_links_input.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                color: #e5e7eb;
                padding: 8px 12px;
                border-radius: 8px;
                border: 1px solid rgba(34,197,94,0.6);
                font-weight: 600;
            }
        """)
        count_inputs.addWidget(self.max_links_input)
        
        count_suffix = QLabel("ссылок")
        count_suffix.setStyleSheet("color: #94a3b8;")
        count_inputs.addWidget(count_suffix)
        
        count_inputs.addStretch()
        count_layout.addLayout(count_inputs)

        self.content_layout.addWidget(count_section)

        # ------------------------------------------------------------
        # ЛОГ (с тенями)
        # ------------------------------------------------------------
        log_section, log_layout = self.create_section("📋 Лог работы")
        log_section.setObjectName("paymentLog")

        # SHADOW
        log_shadow = QGraphicsDropShadowEffect(self)
        log_shadow.setBlurRadius(25)
        log_shadow.setOffset(0, 4)
        log_shadow.setColor(QColor(0, 0, 0, 160))
        log_section.setGraphicsEffect(log_shadow)

        log_section.setStyleSheet("""
            #paymentLog {
                background-color: #020617;
                border-radius: 16px;
                border: 1px solid rgba(34,197,94,0.55);
            }
            #paymentLog QLabel {
                color: #e5e7eb;
            }
            QTextEdit {
                background-color: #0f172a;
                color: #e2e8f0;
                padding: 10px;
                border-radius: 12px;
                font-family: Consolas;
                font-size: 10pt;
                border: 1px solid rgba(51,65,85,0.6);
            }
        """)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(200)
        log_layout.addWidget(self.log_output)

        self.content_layout.addWidget(log_section)

        # ------------------------------------------------------------
        # КНОПКИ
        # ------------------------------------------------------------
        actions = QHBoxLayout()
        actions.addStretch()

        # BASE BUTTON STYLE (QT SAFE)
        base_btn = """
            QPushButton {
                background-color: #020617;
                color: #e5e7eb;
                font-size: 10pt;
                padding: 9px 22px;
                font-weight: 600;
                border-radius: 999px;
                border: 1px solid rgba(148,163,184,0.55);
            }
            QPushButton:hover {
                border-color: #22c55e;
            }
        """

        # START
        self.start_btn = QPushButton("🚀 Начать отправку")
        self.start_btn.setStyleSheet(base_btn + """
            QPushButton {
                background-color: #15803d;
                border: 1px solid rgba(34,197,94,0.9);
                color: #ecfdf5;
            }
            QPushButton:hover {
                background-color: #22c55e;
            }
        """)
        self.start_btn.clicked.connect(self.start_payment_links)
        actions.addWidget(self.start_btn)

        # STOP
        self.stop_btn = QPushButton("⏹ Остановить")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(base_btn + """
            QPushButton {
                background-color: #7f1d1d;
                color: #fecaca;
                border: 1px solid rgba(248,113,113,0.85);
            }
            QPushButton:hover {
                background-color: #991b1b;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_payment_links)
        actions.addWidget(self.stop_btn)

        # CLEAR
        clear_log_btn = QPushButton("🧹 Очистить лог")
        clear_log_btn.setStyleSheet(base_btn)
        clear_log_btn.clicked.connect(lambda: self.log_output.clear())
        actions.addWidget(clear_log_btn)

        self.content_layout.addLayout(actions)

        # ------------------------------------------------------------
        # WARNING (если нет процессора)
        # ------------------------------------------------------------
        if not PROCESSOR_AVAILABLE:
            warn = QLabel(
                "⚠️ Процессор отправки ссылок не найден!\n"
                "Проверь файл: core/payment_links_processor.py"
            )
            warn.setWordWrap(True)
            warn.setStyleSheet("""
                color: #fca5a5;
                font-weight: 600;
                background: rgba(127,29,29,0.55);
                border: 1px solid #b91c1c;
                padding: 8px 10px;
                border-radius: 10px;
            """)
            self.content_layout.insertWidget(0, warn)

    # =====================================================================
    # ЛОГИКА
    # =====================================================================

    def add_log(self, msg):
        self.log_output.append(msg)
        bar = self.log_output.verticalScrollBar()
        bar.setValue(bar.maximum())

    def start_payment_links(self):
        login_url = self.settings.get_login_url()
        username = self.settings.get_username()
        password = self.settings.get_password()

        if not all([login_url, username, password]):
            QMessageBox.warning(self, "Ошибка",
                "Заполните настройки аккаунта перед запуском!")
            return

        if not PROCESSOR_AVAILABLE:
            QMessageBox.critical(self, "Ошибка",
                "Процессор отправки ссылок не найден!")
            return

        # Получаем параметры фильтра
        use_delay_search = self.use_delay_filter.isChecked()
        delay_from = self.delay_from_input.text().strip()
        delay_to = self.delay_to_input.text().strip()

        # Получаем максимальное количество ссылок
        max_links_str = self.max_links_input.text().strip()
        max_links = None
        if max_links_str:
            try:
                max_links = int(max_links_str)
                if max_links <= 0:
                    QMessageBox.warning(self, "Ошибка",
                        "Количество ссылок должно быть больше 0!")
                    return
            except ValueError:
                QMessageBox.warning(self, "Ошибка",
                    "Количество ссылок должно быть числом!")
                return

        self.log_output.clear()

        self.worker = PaymentLinksWorker(
            login_url, username, password,
            use_delay_search=use_delay_search,
            delay_from=delay_from,
            delay_to=delay_to,
            max_links=max_links
        )
        self.worker.log_signal.connect(self.add_log)
        self.worker.error_signal.connect(self.on_worker_error)
        self.worker.finished_signal.connect(self.on_worker_finished)

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.add_log("=" * 60)
        self.add_log("🚀 Запуск отправки ссылок на оплату...")
        if max_links:
            self.add_log(f"🎯 Установлен лимит: {max_links} ссылок")
        self.add_log("=" * 60)
        self.worker.start()

        # Регистрируем worker в главном окне для корректного закрытия
        if hasattr(self.parent(), 'register_worker'):
            self.parent().register_worker(self.worker)

    def stop_payment_links(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.add_log("⏹ Остановка отправлена...")

    def on_worker_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.add_log("=" * 60)
        self.add_log("✅ Отправка ссылок завершена!")
        self.add_log("=" * 60)

    def on_worker_error(self, msg):
        self.add_log(f"❌ Ошибка: {msg}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.critical(self, "Ошибка", msg)