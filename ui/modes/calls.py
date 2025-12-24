"""
📞 Режим обработки звонков — Dark Futuristic Corporate UI (QT-SAFE)
Автоматическая обработка очереди звонков + премиальный эффектный интерфейс
"""

from PyQt6.QtWidgets import (
    QLabel, QTextEdit, QLineEdit, QPushButton,
    QHBoxLayout, QMessageBox, QWidget, QVBoxLayout,
    QGraphicsDropShadowEffect, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import threading
import os
import sys

from .base import ModeBase

# settings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from settings_manager import get_settings_manager

# processor
try:
    from core.calls_processor import process_call_list
    PROCESSOR_AVAILABLE = True
except ImportError:
    PROCESSOR_AVAILABLE = False
    print("⚠️ calls_processor не найден!")


# =====================================================================
# WORKER (с поддержкой длительности звонка)
# =====================================================================

class CallsWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, login_url, username, password, call_comments, repeat_mode=False, 
                 use_call_duration=False, duration_min=10, duration_max=15, use_timezones=False):
        super().__init__()
        self.login_url = login_url
        self.username = username
        self.password = password
        self.call_comments = call_comments
        self.stop_flag = threading.Event()
        self.repeat_mode = repeat_mode
        
        # НОВЫЕ параметры длительности
        self.use_call_duration = use_call_duration
        self.duration_min = duration_min
        self.duration_max = duration_max
        
        # Параметр часовых поясов
        self.use_timezones = use_timezones

    def logger_func(self, msg):
        self.log_signal.emit(msg)

    def progress_callback(self, count):
        self.progress_signal.emit(count)

    def run(self):
        if not PROCESSOR_AVAILABLE:
            self.error_signal.emit("Процессор звонков не доступен!")
            return
        try:
            self.log_signal.emit("🚀 Запуск обработки звонков...")
            process_call_list(
                self.login_url,
                self.username,
                self.password,
                self.call_comments,
                self.logger_func,
                self.stop_flag,
                self.progress_callback,
                repeat_mode=self.repeat_mode,
                # НОВЫЕ параметры
                use_call_duration=self.use_call_duration,
                duration_min=self.duration_min,
                duration_max=self.duration_max,
                use_timezones=self.use_timezones
            )
        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()


    def stop(self):
        self.log_signal.emit("⏹ Остановка...")
        self.stop_flag.set()


# =====================================================================
# MODE UI
# =====================================================================

class CallsMode(ModeBase):

    def __init__(self, parent=None):
        super().__init__(
            title="Обработка звонков",
            description="Автоматическая обработка очереди звонков",
            parent=parent
        )
        self.worker = None
        self.settings = get_settings_manager()
        self.init_mode_ui()

    # =================================================================
    # DARK FUTURISTIC UI — QT-SAFE
    # =================================================================

    def init_mode_ui(self):

        # ------------------------------------------------------------
        # HERO CARD
        # ------------------------------------------------------------
        hero = QWidget()
        hero.setObjectName("callHero")
        hero_l = QVBoxLayout(hero)
        hero_l.setContentsMargins(18, 18, 18, 14)
        hero_l.setSpacing(6)

        # shadow
        hero_shadow = QGraphicsDropShadowEffect(self)
        hero_shadow.setBlurRadius(40)
        hero_shadow.setOffset(0, 6)
        hero_shadow.setColor(QColor(0, 0, 0, 170))
        hero.setGraphicsEffect(hero_shadow)

        title = QLabel("📞 Обработка звонков")
        title.setFont(QFont("Segoe UI Semibold", 14))

        subtitle = QLabel(
            "Система автоматически обрабатывает очередь звонков и оставляет комментарии в карточках клиентов.\n"
            "Используются данные авторизации из настроек аккаунта."
        )
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setWordWrap(True)

        badge = QLabel("CALLFLOW ENGINE")
        badge.setFont(QFont("Segoe UI Semibold", 9))
        badge.setStyleSheet("""
            QLabel {
                color: #38bdf8;
                background-color: rgba(15,23,42,0.8);
                border: 1px solid rgba(56,189,248,0.55);
                border-radius: 999px;
                padding: 4px 10px;
            }
        """)

        hero_l.addWidget(title)
        hero_l.addWidget(subtitle)
        hero_l.addSpacing(4)
        hero_l.addWidget(badge)

        hero.setStyleSheet("""
            #callHero {
                background-color: #0a0f1a;
                border-radius: 18px;
                border: 1px solid rgba(56,189,248,0.55);
            }
            #callHero QLabel { color: #e5e7eb; }
        """)

        self.content_layout.addWidget(hero)

        # ------------------------------------------------------------
        # НОВАЯ СЕКЦИЯ: ДЛИТЕЛЬНОСТЬ ЗВОНКА
        # ------------------------------------------------------------
        duration_sec, duration_l = self.create_section(
            "⏱️ Длительность звонка",
            "Управление временем каждого звонка"
        )
        duration_sec.setObjectName("callDurationSection")
        duration_sec.setStyleSheet("""
            #callDurationSection {
                background-color: #020617;
                border-radius: 16px;
                border: 1px solid rgba(148,163,184,0.45);
            }
            #callDurationSection QLabel {
                color: #e5e7eb;
            }
            #callDurationSection QCheckBox {
                color: #e5e7eb;
                font-size: 10pt;
            }
            #callDurationSection QSpinBox {
                background-color: #0f172a;
                color: #e5e7eb;
                border-radius: 8px;
                border: 1px solid rgba(51,65,85,0.7);
                padding: 6px 10px;
                font-size: 10pt;
            }
            #callDurationSection QSpinBox:focus {
                border-color: #3b82f6;
            }
        """)

        duration_shadow = QGraphicsDropShadowEffect(self)
        duration_shadow.setBlurRadius(24)
        duration_shadow.setOffset(0, 4)
        duration_shadow.setColor(QColor(0, 0, 0, 150))
        duration_sec.setGraphicsEffect(duration_shadow)

        # Чекбокс включения длительности
        self.use_call_duration_checkbox = QCheckBox("✅ Использовать настраиваемую длительность звонка")
        self.use_call_duration_checkbox.setFont(QFont("Segoe UI Semibold", 10))
        self.use_call_duration_checkbox.toggled.connect(self.on_duration_checkbox_toggled)
        duration_l.addWidget(self.use_call_duration_checkbox)

        # Строка с мин/макс
        duration_row = QHBoxLayout()
        duration_row.setSpacing(15)

        # Минимум
        min_label = QLabel("⏬ Минимум секунд:")
        min_label.setFont(QFont("Segoe UI", 10))
        self.duration_min_spin = QSpinBox()
        self.duration_min_spin.setRange(1, 600)  # от 1 сек до 10 мин
        self.duration_min_spin.setValue(10)
        self.duration_min_spin.setSuffix(" сек")
        self.duration_min_spin.setMinimumWidth(100)

        duration_row.addWidget(min_label)
        duration_row.addWidget(self.duration_min_spin)

        # Максимум
        max_label = QLabel("⏫ Максимум секунд:")
        max_label.setFont(QFont("Segoe UI", 10))
        self.duration_max_spin = QSpinBox()
        self.duration_max_spin.setRange(1, 600)
        self.duration_max_spin.setValue(15)
        self.duration_max_spin.setSuffix(" сек")
        self.duration_max_spin.setMinimumWidth(100)

        duration_row.addWidget(max_label)
        duration_row.addWidget(self.duration_max_spin)
        duration_row.addStretch()

        duration_l.addLayout(duration_row)

        # Подсказка
        hint = QLabel(
            "💡 Звонок будет длиться случайное время от минимума до максимума.\n"
            "Пауза добавляется ПЕРЕД отправкой комментария."
        )
        hint.setFont(QFont("Segoe UI", 9))
        hint.setStyleSheet("color: #94a3b8; padding-left: 20px;")
        hint.setWordWrap(True)
        duration_l.addWidget(hint)

        self.content_layout.addWidget(duration_sec)

        # Изначально поля отключены
        self.duration_min_spin.setEnabled(False)
        self.duration_max_spin.setEnabled(False)

        # ------------------------------------------------------------
        # НОВАЯ СЕКЦИЯ: ЧАСОВЫЕ ПОЯСА
        # ------------------------------------------------------------
        tz_sec, tz_l = self.create_section(
            "🌍 Часовые пояса (ФЗ-230)",
            "Автоматический обзвон с учетом разрешенных часов"
        )
        tz_sec.setObjectName("callTimezoneSection")
        tz_sec.setStyleSheet("""
            #callTimezoneSection {
                background-color: #020617;
                border-radius: 16px;
                border: 1px solid rgba(148,163,184,0.45);
            }
            #callTimezoneSection QLabel {
                color: #e5e7eb;
            }
            #callTimezoneSection QCheckBox {
                color: #e5e7eb;
                font-size: 10pt;
            }
        """)

        tz_shadow = QGraphicsDropShadowEffect(self)
        tz_shadow.setBlurRadius(24)
        tz_shadow.setOffset(0, 4)
        tz_shadow.setColor(QColor(0, 0, 0, 150))
        tz_sec.setGraphicsEffect(tz_shadow)

        # Чекбокс включения часовых поясов
        self.use_timezones_checkbox = QCheckBox("✅ Учитывать часовые пояса при обзвоне")
        self.use_timezones_checkbox.setFont(QFont("Segoe UI Semibold", 10))
        tz_l.addWidget(self.use_timezones_checkbox)

        # Подсказка
        tz_hint = QLabel(
            "💡 Автоматически обзванивает клиентов по часовым поясам с учетом ФЗ-230:\n"
            "   • Будни: 8:00 - 22:00 по времени клиента\n"
            "   • Выходные: 9:00 - 20:00 по времени клиента\n"
            "   ⚠️ Работает только для обычного обзвона (не повторного)"
        )
        tz_hint.setFont(QFont("Segoe UI", 9))
        tz_hint.setStyleSheet("color: #94a3b8; padding-left: 20px;")
        tz_hint.setWordWrap(True)
        tz_l.addWidget(tz_hint)

        self.content_layout.addWidget(tz_sec)

        # ------------------------------------------------------------
        # COMMENT INPUT
        # ------------------------------------------------------------
        comment_sec, sec_l = self.create_section(
            "💬 Комментарии для звонков",
            "Каждая строка — отдельный вариант"
        )
        comment_sec.setObjectName("callCommentSection")
        comment_sec.setStyleSheet("""
            #callCommentSection {
                background-color: #020617;
                border-radius: 16px;
                border: 1px solid rgba(148,163,184,0.45);
            }
            #callCommentSection QLabel {
                color: #e5e7eb;
            }
            #callCommentSection QTextEdit {
                background-color: #0f172a;
                color: #e5e7eb;
                border-radius: 12px;
                border: 1px solid rgba(51,65,85,0.7);
                padding: 10px;
                font-size: 10.5pt;
            }
            #callCommentSection QTextEdit:focus {
                border-color: #3b82f6;
            }
        """)

        com_shadow = QGraphicsDropShadowEffect(self)
        com_shadow.setBlurRadius(24)
        com_shadow.setOffset(0, 4)
        com_shadow.setColor(QColor(0, 0, 0, 150))
        comment_sec.setGraphicsEffect(com_shadow)

        self.comment_text = QTextEdit()
        self.comment_text.setPlaceholderText(
            "Введите варианты комментариев:\n\n"
            "мт но\n"
            "не взял трубку\n"
            "обещал перезвонить"
        )
        self.comment_text.setMinimumHeight(130)
        sec_l.addWidget(self.comment_text)

        self.content_layout.addWidget(comment_sec)

        # ------------------------------------------------------------
        # LOG SECTION
        # ------------------------------------------------------------
        log_sec, log_l = self.create_section("📋 Лог работы")
        log_sec.setObjectName("callLogSection")

        log_sec.setStyleSheet("""
            #callLogSection {
                background-color: #020617;
                border-radius: 16px;
                border: 1px solid rgba(56,189,248,0.55);
            }
            #callLogSection QLabel { color: #e5e7eb; }
            QTextEdit {
                background-color: #0f172a;
                color: #e5e7eb;
                border-radius: 12px;
                border: 1px solid rgba(31,41,55,0.7);
                padding: 10px;
                font-family: Consolas;
                font-size: 10pt;
            }
        """)

        log_shadow = QGraphicsDropShadowEffect(self)
        log_shadow.setBlurRadius(26)
        log_shadow.setOffset(0, 5)
        log_shadow.setColor(QColor(0, 0, 0, 170))
        log_sec.setGraphicsEffect(log_shadow)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(220)
        log_l.addWidget(self.log_output)

        p_row = QHBoxLayout()
        self.progress_label = QLabel("Обработано клиентов: 0")
        self.progress_label.setStyleSheet("color: #93c5fd; font-size: 10.5pt;")
        p_row.addWidget(self.progress_label)
        p_row.addStretch()
        log_l.addLayout(p_row)

        self.content_layout.addWidget(log_sec)

        # ------------------------------------------------------------
        # BUTTONS
        # ------------------------------------------------------------
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        base_btn = """
            QPushButton {
                background-color: #020617;
                color: #e5e7eb;
                border-radius: 999px;
                padding: 9px 22px;
                font-weight: 600;
                font-size: 10pt;
                border: 1px solid rgba(148,163,184,0.65);
            }
            QPushButton:hover {
                color: #f8fafc;
                border-color: #38bdf8;
            }
            QPushButton:pressed {
                border-color: #22c55e;
            }
            QPushButton:disabled {
                color: #475569;
                border-color: #1e293b;
            }
        """

        self.start_btn = QPushButton("🚀 Начать")
        self.start_btn.clicked.connect(self.start_calls)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet(base_btn + """
            QPushButton {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #22c55e,
                    stop:1 #15803d
                );
                border-color: rgba(34,197,94,0.9);
            }
            QPushButton:hover {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4ade80,
                    stop:1 #22c55e
                );
            }
        """)
        btn_row.addWidget(self.start_btn)

        # Кнопка повторного обзвона
        self.repeat_btn = QPushButton("🔁 Повторный обзвон")
        self.repeat_btn.clicked.connect(self.start_repeat_calls)
        self.repeat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.repeat_btn.setStyleSheet(base_btn + """
            QPushButton {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0ea5e9,
                    stop:1 #0369a1
                );
                border-color: rgba(14,165,233,0.9);
            }
            QPushButton:hover {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #38bdf8,
                    stop:1 #0ea5e9
                );
            }
        """)
        btn_row.addWidget(self.repeat_btn)

        self.stop_btn = QPushButton("⏹ Остановить")
        self.stop_btn.clicked.connect(self.stop_calls)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(base_btn + """
            QPushButton {
                background-color: #7f1d1d;
                color: #fecaca;
                border-color: rgba(248,113,113,0.85);
            }
            QPushButton:hover {
                background-color: #991b1b;
                border-color: #fca5a5;
            }
        """)
        btn_row.addWidget(self.stop_btn)

        clear_btn = QPushButton("🧹 Очистить лог")
        clear_btn.clicked.connect(lambda: self.log_output.clear())
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(base_btn)
        btn_row.addWidget(clear_btn)

        self.content_layout.addLayout(btn_row)

        # ------------------------------------------------------------
        # PROCESSOR WARNING
        # ------------------------------------------------------------
        if not PROCESSOR_AVAILABLE:
            warn = QLabel(
                "⚠️ Процессор звонков не найден!\n"
                "Проверь файл core/calls_processor.py"
            )
            warn.setWordWrap(True)
            warn.setStyleSheet("""
                color: #fca5a5;
                background-color: rgba(127,29,29,0.55);
                border: 1px solid #b91c1c;
                border-radius: 10px;
                padding: 8px 10px;
            """)
            self.content_layout.insertWidget(0, warn)

        # ------------------------------------------------------------
        # 🔥 ЗАГРУЗКА СОХРАНЁННЫХ НАСТРОЕК
        # ------------------------------------------------------------
        s = self.settings.get_call_settings()
        self.comment_text.setText(s.get("comments_text", ""))
        
        # НОВОЕ: Загрузка настроек длительности
        self.use_call_duration_checkbox.setChecked(s.get("use_call_duration", False))
        self.duration_min_spin.setValue(s.get("duration_min", 10))
        self.duration_max_spin.setValue(s.get("duration_max", 15))
        
        # Загрузка настройки часовых поясов
        self.use_timezones_checkbox.setChecked(s.get("use_timezones", False))


    # =================================================================
    # НОВАЯ ФУНКЦИЯ: Включение/отключение полей длительности
    # =================================================================
    def on_duration_checkbox_toggled(self, checked):
        """Включение/отключение полей длительности звонка"""
        self.duration_min_spin.setEnabled(checked)
        self.duration_max_spin.setEnabled(checked)


    # =================================================================
    # LOGIC
    # =================================================================

    def add_log(self, msg):
        self.log_output.append(msg)
        bar = self.log_output.verticalScrollBar()
        bar.setValue(bar.maximum())

    def update_progress(self, count):
        self.progress_label.setText(f"Обработано клиентов: {count}")

    def start_calls(self):
        login_url = self.settings.get_login_url()
        username = self.settings.get_username()
        password = self.settings.get_password()

        if not all([login_url, username, password]):
            QMessageBox.warning(self, "Ошибка", "Сначала настройте аккаунт!")
            return

        txt = self.comment_text.toPlainText().strip()
        if not txt:
            QMessageBox.warning(self, "Ошибка", "Введите комментарии!")
            return

        if not PROCESSOR_AVAILABLE:
            QMessageBox.critical(self, "Ошибка", "Процессор недоступен!")
            return

        # Валидация длительности
        if self.use_call_duration_checkbox.isChecked():
            min_dur = self.duration_min_spin.value()
            max_dur = self.duration_max_spin.value()
            if min_dur > max_dur:
                QMessageBox.warning(
                    self, 
                    "Ошибка", 
                    f"Минимум ({min_dur} сек) не может быть больше максимума ({max_dur} сек)!"
                )
                return

        comments = [line.strip() for line in txt.splitlines() if line.strip()]

        # ============================================================
        # 🔥 СОХРАНЕНИЕ НАСТРОЕК ЗВОНКОВ
        # ============================================================
        self.settings.set_call_settings({
            "comments_text": self.comment_text.toPlainText(),
            "use_call_duration": self.use_call_duration_checkbox.isChecked(),
            "duration_min": self.duration_min_spin.value(),
            "duration_max": self.duration_max_spin.value(),
            "use_timezones": self.use_timezones_checkbox.isChecked(),
        })

        # ============================================================
        # ОЧИСТКА ЛОГА + ПОДГОТОВКА
        # ============================================================
        self.log_output.clear()
        self.progress_label.setText("Обработано клиентов: 0")

        # создаём worker с НОВЫМИ параметрами
        self.worker = CallsWorker(
            login_url, 
            username, 
            password, 
            comments,
            repeat_mode=False,
            use_call_duration=self.use_call_duration_checkbox.isChecked(),
            duration_min=self.duration_min_spin.value(),
            duration_max=self.duration_max_spin.value(),
            use_timezones=self.use_timezones_checkbox.isChecked()
        )

        # подключение сигналов
        self.worker.log_signal.connect(self.add_log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_worker_finished)
        self.worker.error_signal.connect(self.on_worker_error)

        # UI
        self.start_btn.setEnabled(False)
        self.repeat_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.add_log("=" * 60)
        self.add_log("🚀 Запуск обработки звонков...")
        if self.use_call_duration_checkbox.isChecked():
            self.add_log(f"⏱️ Длительность звонка: {self.duration_min_spin.value()}-{self.duration_max_spin.value()} сек")
        if self.use_timezones_checkbox.isChecked():
            self.add_log("🌍 Учет часовых поясов включен (ФЗ-230)")
        self.add_log("=" * 60)

        self.worker.start()

        # Регистрируем worker в главном окне для корректного закрытия
        if hasattr(self.parent(), 'register_worker'):
            self.parent().register_worker(self.worker)


    def start_repeat_calls(self):
        """Запуск повторного обзвона - без установки даты"""
        login_url = self.settings.get_login_url()
        username = self.settings.get_username()
        password = self.settings.get_password()

        if not all([login_url, username, password]):
            QMessageBox.warning(self, "Ошибка", "Сначала настройте аккаунт!")
            return

        txt = self.comment_text.toPlainText().strip()
        if not txt:
            QMessageBox.warning(self, "Ошибка", "Введите комментарии!")
            return

        if not PROCESSOR_AVAILABLE:
            QMessageBox.critical(self, "Ошибка", "Процессор недоступен!")
            return

        # Валидация длительности
        if self.use_call_duration_checkbox.isChecked():
            min_dur = self.duration_min_spin.value()
            max_dur = self.duration_max_spin.value()
            if min_dur > max_dur:
                QMessageBox.warning(
                    self, 
                    "Ошибка", 
                    f"Минимум ({min_dur} сек) не может быть больше максимума ({max_dur} сек)!"
                )
                return

        comments = [line.strip() for line in txt.splitlines() if line.strip()]

        # Сохранение настроек
        self.settings.set_call_settings({
            "comments_text": self.comment_text.toPlainText(),
            "use_call_duration": self.use_call_duration_checkbox.isChecked(),
            "duration_min": self.duration_min_spin.value(),
            "duration_max": self.duration_max_spin.value(),
            "use_timezones": self.use_timezones_checkbox.isChecked(),
        })

        # Очистка лога
        self.log_output.clear()
        self.progress_label.setText("Обработано клиентов: 0")

        # создаём worker с repeat_mode=True и НОВЫМИ параметрами
        self.worker = CallsWorker(
            login_url, 
            username, 
            password, 
            comments, 
            repeat_mode=True,
            use_call_duration=self.use_call_duration_checkbox.isChecked(),
            duration_min=self.duration_min_spin.value(),
            duration_max=self.duration_max_spin.value(),
            use_timezones=self.use_timezones_checkbox.isChecked()
        )

        # подключение сигналов
        self.worker.log_signal.connect(self.add_log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_worker_finished)
        self.worker.error_signal.connect(self.on_worker_error)

        # UI
        self.start_btn.setEnabled(False)
        self.repeat_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.add_log("=" * 60)
        self.add_log("🔁 Запуск ПОВТОРНОГО обзвона (без фильтра по дате)...")
        if self.use_call_duration_checkbox.isChecked():
            self.add_log(f"⏱️ Длительность звонка: {self.duration_min_spin.value()}-{self.duration_max_spin.value()} сек")
        if self.use_timezones_checkbox.isChecked():
            self.add_log("🌍 Учет часовых поясов включен (ФЗ-230)")
        self.add_log("=" * 60)

        self.worker.start()

        # Регистрируем worker в главном окне
        if hasattr(self.parent(), 'register_worker'):
            self.parent().register_worker(self.worker)


    def stop_calls(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()

    def on_worker_finished(self):
        self.start_btn.setEnabled(True)
        self.repeat_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.add_log("=" * 60)
        self.add_log("✅ Выполнено")
        self.add_log("=" * 60)

    def on_worker_error(self, msg):
        self.add_log(f"❌ ОШИБКА: {msg}")
        QMessageBox.critical(self, "Ошибка", msg)