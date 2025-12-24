"""
🔐 Сброс паролей — Dark Futuristic Corporate (QT-SAFE EDITION)
Эффектный UI без неподдерживаемого CSS, с настоящими Qt-эффектами.
"""

from PyQt6.QtWidgets import (
    QLabel, QLineEdit, QFileDialog, QPushButton,
    QHBoxLayout, QMessageBox, QTextEdit, QCheckBox,
    QWidget, QVBoxLayout, QGraphicsDropShadowEffect,
    QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import threading
import os
import sys

from .base import ModeBase

# ===== ПРОЦЕССОР =====
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from core.password_reset_processor import process_password_reset
    from settings_manager import load_settings
    PROCESSOR_AVAILABLE = True
except ImportError:
    PROCESSOR_AVAILABLE = False
    print("⚠️ password_reset_processor не найден!")


# =====================================================================
#  WORKER THREAD
# =====================================================================

class PasswordResetWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, file_path, site_choice):
        super().__init__()
        self.file_path = file_path
        self.site_choice = site_choice  # "max.credit" или "svoi-ludi.ru"
        self.stop_flag = threading.Event()

    def logger_func(self, message):
        self.log_signal.emit(message)

    def run(self):
        if not PROCESSOR_AVAILABLE:
            self.error_signal.emit("Процессор сброса паролей не доступен!")
            return

        try:
            self.log_signal.emit("🚀 Запуск процессора сброса паролей...")
            
            # Формируем user_link на основе выбора пользователя
            if self.site_choice == "svoi-ludi.ru":
                user_link = "https://svoi-ludi.ru"
                self.log_signal.emit("🌐 Сайт: Свои Люди")
            else:  # max.credit (по умолчанию)
                user_link = "https://www.max.credit"
                self.log_signal.emit("🌐 Сайт: Max.Credit")
            
            # Запускаем процессор с user_link
            process_password_reset(
                self.file_path,
                self.logger_func,
                self.stop_flag,
                user_link
            )
        except Exception as e:
            self.error_signal.emit(f"Ошибка: {e}")
        finally:
            self.finished_signal.emit()

    def stop(self):
        self.log_signal.emit("⏹ Остановка...")
        self.stop_flag.set()


# =====================================================================
#  CUSTOM TOGGLE (Qt-SAFE)
# =====================================================================

class Toggle(QCheckBox):
    """Современный toggle, работает без ::before/after (Qt-SAFE)"""

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QBrush
        from PyQt6.QtCore import QRectF

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # фон
        rect = QRectF(0, 0, 42, 22)
        if self.isChecked():
            painter.setBrush(QBrush(QColor("#22d3ee")))
            painter.setPen(QColor("#38bdf8"))
        else:
            painter.setBrush(QBrush(QColor("#1e293b")))
            painter.setPen(QColor("#475569"))

        painter.drawRoundedRect(rect, 11, 11)

        # бегунок
        pos = 22 if self.isChecked() else 2
        knob = QRectF(pos, 2, 18, 18)
        painter.setBrush(QBrush(QColor("#0f172a")))
        painter.setPen(QColor("#0f172a"))
        painter.drawEllipse(knob)


# =====================================================================
#  UI MODE
# =====================================================================

class PasswordResetMode(ModeBase):

    def __init__(self, parent=None):
        super().__init__(
            title="Сброс паролей",
            description="Массовая отправка запросов на восстановление пароля",
            parent=parent
        )

        self.worker = None
        self.selected_file = None
        self.file_path = None  # Путь к файлу из TG

        self.init_mode_ui()

    # =====================================================================
    #  UI
    # =====================================================================

    def init_mode_ui(self):

        # ------------------------------------------------------------
        # HERO CARD (с реальной тенью)
        # ------------------------------------------------------------

        hero = QWidget()
        hero.setObjectName("resetHero")
        hero_l = QVBoxLayout(hero)
        hero_l.setContentsMargins(18, 18, 18, 14)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 180))
        hero.setGraphicsEffect(shadow)

        hero.setStyleSheet("""
            #resetHero {
                background-color: #0a0f1a;
                border-radius: 18px;
                border: 1px solid rgba(56,189,248,0.55);
            }
            #resetHero QLabel {
                color: #e5e7eb;
            }
        """)

        t = QLabel("🔐 Массовый сброс паролей")
        t.setFont(QFont("Segoe UI Semibold", 14))

        st = QLabel(
            "Загрузи Excel со списком телефонов — бот отправит запросы\n"
            "на восстановление пароля автоматически."
        )
        st.setFont(QFont("Segoe UI", 10))
        st.setWordWrap(True)

        badge = QLabel("PASSWORD RESET ENGINE")
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
        # FILE SECTION (Qt-safe)
        # ------------------------------------------------------------

        file_section, file_l = self.create_section(
            "📁 Excel файл",
            "Поддерживаемые форматы: XLSX, XLS"
        )
        file_section.setObjectName("fileSec")

        file_section.setStyleSheet("""
            #fileSec {
                background-color: #020617;
                border-radius: 16px;
                border: 1px solid rgba(148,163,184,0.55);
            }
            #fileSec QLabel {
                color: #e5e7eb;
            }
        """)

        row = QHBoxLayout()

        self.file_path_label = QLabel("Файл не выбран")
        self.file_path_label.setStyleSheet("color: #6b7280;")
        self.file_path_label.setFont(QFont("Segoe UI", 10))
        row.addWidget(self.file_path_label, 1)

        choose_btn = QPushButton("📂 Выбрать файл")
        choose_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        choose_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e3a8a;
                color: white;
                padding: 8px 14px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #3b82f6;
            }
        """)
        choose_btn.clicked.connect(self.choose_file)
        row.addWidget(choose_btn)

        file_l.addLayout(row)
        self.content_layout.addWidget(file_section)

        # ------------------------------------------------------------
        # OPTIONS (toggle)
        # ------------------------------------------------------------

        opt_sec, opt_l = self.create_section("🎛 Опции запуска")
        opt_sec.setObjectName("optSec")

        opt_sec.setStyleSheet("""
            #optSec {
                background-color: #020617;
                border-radius: 16px;
                border: 1px solid rgba(148,163,184,0.55);
            }
            #optSec QLabel {
                color: #e5e7eb;
            }
        """)

        toggle_row = QHBoxLayout()
        self.run_in_background = Toggle()
        toggle_text = QLabel("Запустить в фоне")
        toggle_text.setStyleSheet("color: #e5e7eb; font-size: 11pt;")

        toggle_row.addWidget(self.run_in_background)
        toggle_row.addWidget(toggle_text)
        toggle_row.addStretch()

        opt_l.addLayout(toggle_row)

        warn = QLabel("⚠ Процесс будет работать даже после закрытия окна")
        warn.setStyleSheet("color: #fca5a5; font-size: 9.5pt;")
        opt_l.addWidget(warn)
        
        # ============ ВЫБОР САЙТА ============
        opt_l.addSpacing(12)
        
        site_row = QHBoxLayout()
        site_label = QLabel("🌐 Сайт для восстановления:")
        site_label.setStyleSheet("color: #e5e7eb; font-size: 11pt;")
        site_row.addWidget(site_label)
        
        self.site_combo = QComboBox()
        self.site_combo.addItem("Max.Credit", "max.credit")
        self.site_combo.addItem("Свои Люди", "svoi-ludi.ru")
        self.site_combo.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                color: #e5e7eb;
                border: 1px solid rgba(56,189,248,0.55);
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 10pt;
                min-width: 180px;
            }
            QComboBox:hover {
                border-color: #38bdf8;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #38bdf8;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #e5e7eb;
                border: 1px solid #38bdf8;
                selection-background-color: #0f172a;
                selection-color: #38bdf8;
            }
        """)
        site_row.addWidget(self.site_combo)
        site_row.addStretch()
        
        opt_l.addLayout(site_row)

        self.content_layout.addWidget(opt_sec)

        # ------------------------------------------------------------
        # LOG
        # ------------------------------------------------------------

        log_sec, ll = self.create_section("📋 Лог работы")
        log_sec.setObjectName("logSec")
        log_sec.setStyleSheet("""
            #logSec {
                background-color: #020617;
                border-radius: 16px;
                border: 1px solid rgba(56,189,248,0.55);
            }
            #logSec QLabel { color: #e5e7eb; }
        """)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(250)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                color: #e5e7eb;
                border-radius: 12px;
                border: 1px solid rgba(51,65,85,0.7);
                padding: 10px;
                font-family: Consolas;
                font-size: 10pt;
            }
        """)
        ll.addWidget(self.log_output)

        self.content_layout.addWidget(log_sec)

        # ------------------------------------------------------------
        # ACTION BUTTONS
        # ------------------------------------------------------------

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        base_btn = """
            QPushButton {
                background-color: #020617;
                border-radius: 999px;
                padding: 9px 22px;
                color: #e5e7eb;
                font-weight: 600;
                border: 1px solid rgba(148,163,184,0.55);
            }
            QPushButton:hover {
                border-color: #38bdf8;
            }
        """

        self.start_btn = QPushButton("🚀 Начать сброс")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet(base_btn + """
            QPushButton {
                background-color: #15803d;
                border-color: #22c55e;
                color: #ecfdf5;
            }
            QPushButton:hover {
                background-color: #22c55e;
            }
        """)
        self.start_btn.clicked.connect(self.start_reset)
        btn_row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹ Остановить")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(base_btn + """
            QPushButton {
                background-color: #7f1d1d;
                color: #fecaca;
                border-color: #f87171;
            }
            QPushButton:hover {
                background-color: #991b1b;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_reset)
        btn_row.addWidget(self.stop_btn)

        clear_btn = QPushButton("🧹 Очистить лог")
        clear_btn.setStyleSheet(base_btn)
        clear_btn.clicked.connect(lambda: self.log_output.clear())
        btn_row.addWidget(clear_btn)

        self.content_layout.addLayout(btn_row)

    # =====================================================================
    #  LOGIC (НЕ ТРОГАЛ)
    # =====================================================================

    def choose_file(self):
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
            self.add_log(f"Выбран файл: {base}")
        else:
            self.selected_file = None
            self.file_path_label.setText("Файл не выбран")
            self.file_path_label.setStyleSheet("color: #6b7280;")

    def add_log(self, msg):
        self.log_output.append(msg)
        s = self.log_output.verticalScrollBar()
        s.setValue(s.maximum())

    def start_reset(self):
        # Если файл уже установлен из TG - используем его
        if self.file_path and os.path.exists(self.file_path):
            file_to_use = self.file_path
            self.add_log(f"📎 Используем файл из TG: {os.path.basename(file_to_use)}")
        elif self.selected_file:
            file_to_use = self.selected_file
        else:
            QMessageBox.warning(self, "Ошибка", "Выберите Excel файл!")
            return

        if not PROCESSOR_AVAILABLE:
            QMessageBox.critical(self, "Ошибка", "Процессор недоступен!")
            return

        self.log_output.clear()
        
        # Получаем выбранный сайт из комбобокса
        selected_site = self.site_combo.currentData()  # "max.credit" или "svoi-ludi.ru"

        self.worker = PasswordResetWorker(file_to_use, selected_site)
        self.worker.log_signal.connect(self.add_log)
        self.worker.error_signal.connect(self.on_worker_error)
        self.worker.finished_signal.connect(self.on_worker_finished)

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.add_log("=" * 60)
        self.add_log("🚀 Сброс паролей запущен")
        self.add_log("=" * 60)

        self.worker.start()

        # Регистрируем worker в главном окне для корректного закрытия
        if hasattr(self.parent(), 'register_worker'):
            self.parent().register_worker(self.worker)

    def stop_reset(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.add_log("⏹ Команда остановки отправлена")

    def on_worker_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.add_log("=" * 60)
        self.add_log("✅ Процесс завершён")
        self.add_log("=" * 60)

    def on_worker_error(self, msg):
        self.add_log(f"❌ Ошибка: {msg}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.critical(self, "Ошибка", msg)
    
    # Алиас для TG команды
    def start_password_reset(self):
        """Алиас для start_reset (используется из TG)"""
        self.start_reset()