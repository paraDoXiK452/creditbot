"""
💰 Автоматические списания — Dark Futuristic Corporate UI (QT-SAFE EDITION)
Полноценный премиальный интерфейс с реальными Qt-эффектами (тенями),
без неподдерживаемых веб-CSS свойств.
"""

from PyQt6.QtWidgets import (
    QLabel, QLineEdit, QFileDialog, QPushButton, QCheckBox,
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

# === Импорт процессора списаний ===
try:
    from core.writeoffs_processor import process_auto_writeoffs
    PROCESSOR_AVAILABLE = True
except ImportError:
    PROCESSOR_AVAILABLE = False
    print("⚠️ writeoffs_processor не найден!")


# =====================================================================
# WORKER
# =====================================================================

class WriteoffsWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, login_url, username, password):
        super().__init__()
        self.login_url = login_url
        self.username = username
        self.password = password
        self.stop_flag = threading.Event()

    def logger_func(self, message):
        self.log_signal.emit(message)

    def run(self):
        if not PROCESSOR_AVAILABLE:
            self.error_signal.emit("Процессор списаний не доступен!")
            return

        try:
            self.log_signal.emit("🚀 Запуск автоматических списаний...")
            process_auto_writeoffs(
                self.login_url,
                self.username,
                self.password,
                self.logger_func,
                self.stop_flag
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

class WriteoffsMode(ModeBase):

    def __init__(self, parent=None):
        super().__init__(
            title="Автоматические списания",
            description="Массовое списание средств с карт клиентов",
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
        hero.setObjectName("writeoffHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(18, 18, 18, 14)

        # SHADOW EFFECT
        hero_shadow = QGraphicsDropShadowEffect(self)
        hero_shadow.setBlurRadius(40)
        hero_shadow.setOffset(0, 6)
        hero_shadow.setColor(QColor(0, 0, 0, 180))
        hero.setGraphicsEffect(hero_shadow)

        title = QLabel("💰 Автоматические списания")
        title.setFont(QFont("Segoe UI Semibold", 14))

        subtitle = QLabel(
            "Система автоматически создаёт списания по договорам.\n"
            "Работает в headless-режиме, не блокирует интерфейс."
        )
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setWordWrap(True)

        badge = QLabel("AUTO WRITE-OFF ENGINE")
        badge.setFont(QFont("Segoe UI Semibold", 9))

        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        hero_layout.addSpacing(4)
        hero_layout.addWidget(badge)

        hero.setStyleSheet("""
            #writeoffHero {
                background-color: #0a0f1a;
                border-radius: 18px;
                border: 1px solid rgba(56,189,248,0.55);
            }
            #writeoffHero QLabel {
                color: #e5e7eb;
            }
        """)

        badge.setStyleSheet("""
            QLabel {
                color: #38bdf8;
                padding: 4px 10px;
                border-radius: 999px;
                background-color: #0f172a;
                border: 1px solid rgba(56,189,248,0.5);
            }
        """)

        self.content_layout.addWidget(hero)

        # ------------------------------------------------------------
        # ЛОГ (с тенями)
        # ------------------------------------------------------------
        log_section, log_layout = self.create_section("📋 Лог работы")
        log_section.setObjectName("writeoffLog")

        # SHADOW
        log_shadow = QGraphicsDropShadowEffect(self)
        log_shadow.setBlurRadius(25)
        log_shadow.setOffset(0, 4)
        log_shadow.setColor(QColor(0, 0, 0, 160))
        log_section.setGraphicsEffect(log_shadow)

        log_section.setStyleSheet("""
            #writeoffLog {
                background-color: #020617;
                border-radius: 16px;
                border: 1px solid rgba(56,189,248,0.55);
            }
            #writeoffLog QLabel {
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
                border-color: #38bdf8;
            }
        """

        # START
        self.start_btn = QPushButton("🚀 Начать списания")
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
        self.start_btn.clicked.connect(self.start_writeoffs)
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
        self.stop_btn.clicked.connect(self.stop_writeoffs)
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
                "⚠️ Процессор списаний не найден!\n"
                "Проверь файл: core/writeoffs_processor.py"
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
    # ЛОГИКА — НЕ ИЗМЕНЯЛ
    # =====================================================================

    def add_log(self, msg):
        self.log_output.append(msg)
        bar = self.log_output.verticalScrollBar()
        bar.setValue(bar.maximum())

    def start_writeoffs(self):
        login_url = self.settings.get_login_url()
        username = self.settings.get_username()
        password = self.settings.get_password()

        if not all([login_url, username, password]):
            QMessageBox.warning(self, "Ошибка",
                "Заполните настройки аккаунта перед запуском!")
            return

        if not PROCESSOR_AVAILABLE:
            QMessageBox.critical(self, "Ошибка",
                "Процессор списаний не найден!")
            return

        self.log_output.clear()

        self.worker = WriteoffsWorker(login_url, username, password)
        self.worker.log_signal.connect(self.add_log)
        self.worker.error_signal.connect(self.on_worker_error)
        self.worker.finished_signal.connect(self.on_worker_finished)

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.add_log("=" * 60)
        self.add_log("🚀 Запуск автоматических списаний...")
        self.add_log("=" * 60)
        self.worker.start()

        # Регистрируем worker в главном окне для корректного закрытия
        if hasattr(self.parent(), 'register_worker'):
            self.parent().register_worker(self.worker)

    def stop_writeoffs(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.add_log("⏹ Остановка отправлена...")

    def on_worker_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.add_log("=" * 60)
        self.add_log("✅ Списания завершены!")
        self.add_log("=" * 60)

    def on_worker_error(self, msg):
        self.add_log(f"❌ Ошибка: {msg}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.critical(self, "Ошибка", msg)