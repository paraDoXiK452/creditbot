"""
💬 Режим комментариев (Futuristic Dark Corporate UI, QT-SAFE)
Массовая отправка комментариев по списку
ЛОГИКА НЕ ИЗМЕНЕНА — только премиальный интерфейс + реальные Qt-эффекты
"""

from PyQt6.QtWidgets import (
    QLabel, QTextEdit, QLineEdit, QFileDialog, QPushButton,
    QHBoxLayout, QVBoxLayout, QMessageBox, QCheckBox, QWidget,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import threading

from .base import ModeBase
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from settings_manager import get_settings_manager

try:
    from core.comments_processor import process_comments
    PROCESSOR_AVAILABLE = True
except ImportError:
    PROCESSOR_AVAILABLE = False
    print("⚠️ comments_processor не найден!")


# ============================================================
# WORKER (логика без изменений)
# ============================================================

class CommentsWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, login_url, username, password, comments, delay_from, delay_to, **kwargs):
        super().__init__()
        self.login_url = login_url
        self.username = username
        self.password = password
        self.comments = comments
        self.delay_from = delay_from
        self.delay_to = delay_to
        self.kwargs = kwargs
        self.stop_flag = threading.Event()
        self._total_sent = 0

    def logger_func(self, message):
        self.log_signal.emit(message)
        if "Всего в сессии:" in message:
            try:
                count = int(message.split("Всего в сессии:")[-1].strip())
                self._total_sent = count
                self.progress_signal.emit(count)
            except:
                pass

    def run(self):
        if not PROCESSOR_AVAILABLE:
            self.error_signal.emit("Процессор комментариев не доступен!")
            return

        try:
            self.log_signal.emit("🚀 Запуск процессора комментариев...")
            
            process_comments(
                self.login_url,
                self.username,
                self.password,
                self.comments,
                self.delay_from,
                self.delay_to,
                self.stop_flag,
                self.logger_func,
                **self.kwargs
            )
            self.log_signal.emit(
                f"✅ Обработка завершена! Отправлено комментариев: {self._total_sent}"
            )
        except Exception as e:
            self.error_signal.emit(f"Ошибка: {str(e)}")
        finally:
            self.finished_signal.emit()

    def stop(self):
        self.log_signal.emit("⏹️ Остановка...")
        self.stop_flag.set()


# ============================================================
# UI (QT-SAFE, с реальными эффектами)
# ============================================================

class CommentsMode(ModeBase):

    def __init__(self, parent=None):
        super().__init__(
            title="Комментарии",
            description="Массовая отправка комментариев по списку",
            parent=parent
        )
        self.settings = get_settings_manager()
        self.worker = None
        self.init_mode_ui()

    # =====================================================================================
    # DARK FUTURISTIC CORPORATE REDESIGN (без неподдерживаемого CSS)
    # =====================================================================================

    def init_mode_ui(self):

        # ---------------------------------------------------------------------
        # HERO CARD — крупная карточка сверху с тенью
        # ---------------------------------------------------------------------
        hero_card = QWidget()
        hero_card.setObjectName("commentsHeroCard")
        hero_layout = QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(18, 18, 18, 14)
        hero_layout.setSpacing(6)

        # Тень hero
        hero_shadow = QGraphicsDropShadowEffect(self)
        hero_shadow.setBlurRadius(36)
        hero_shadow.setOffset(0, 6)
        hero_shadow.setColor(QColor(0, 0, 0, 190))
        hero_card.setGraphicsEffect(hero_shadow)

        title_label = QLabel("💬 Массовая отправка комментариев")
        title_label.setFont(QFont("Segoe UI Semibold", 14))

        subtitle = QLabel(
            "Введите текст комментария, настройте фильтры и бот сам зайдёт во все договоры.\n"
            "Используется авторизация из глобальных настроек."
        )
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setWordWrap(True)

        badge = QLabel("AUTO COMMENT ENGINE")
        badge.setFont(QFont("Segoe UI Semibold", 9))

        hero_layout.addWidget(title_label)
        hero_layout.addWidget(subtitle)
        hero_layout.addSpacing(4)
        hero_layout.addWidget(badge)

        hero_card.setStyleSheet("""
            #commentsHeroCard {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #020617,
                    stop:1 #111827
                );
                border-radius: 16px;
                border: 1px solid rgba(56, 189, 248, 0.55);
            }
            #commentsHeroCard QLabel {
                color: #e5e7eb;
            }
        """)

        badge.setStyleSheet("""
            QLabel {
                color: #38bdf8;
                background-color: rgba(15,23,42,0.8);
                border-radius: 999px;
                padding: 4px 10px;
                border: 1px solid rgba(56,189,248,0.55);
            }
        """)

        self.content_layout.addWidget(hero_card)

        # ---------------------------------------------------------------------
        # ВВОД ТЕКСТА КОММЕНТАРИЯ
        # ---------------------------------------------------------------------
        comment_section, comment_layout = self.create_section(
            "📝 Текст комментария"
        )
        comment_section.setObjectName("commentInputSection")
        comment_section.setStyleSheet("""
            #commentInputSection {
                background-color: #020617;
                border-radius: 16px;
                border: 1px solid rgba(148,163,184,0.5);
            }
            #commentInputSection QLabel {
                color: #e5e7eb;
            }
            #commentInputSection QTextEdit {
                background-color: #0f172a;
                color: #e2e8f0;
                border-radius: 12px;
                border: 1px solid rgba(51,65,85,0.7);
                padding: 10px;
                font-size: 10.5pt;
            }
            #commentInputSection QTextEdit:focus {
                border: 1px solid #3b82f6;
                background-color: #1e293b;
            }
        """)

        # Лёгкая тень блока ввода
        comment_shadow = QGraphicsDropShadowEffect(self)
        comment_shadow.setBlurRadius(24)
        comment_shadow.setOffset(0, 4)
        comment_shadow.setColor(QColor(0, 0, 0, 160))
        comment_section.setGraphicsEffect(comment_shadow)

        self.comment_text = QTextEdit()
        self.comment_text.setPlaceholderText("Введите один или несколько комментариев (каждый с новой строки)...")
        self.comment_text.setMinimumHeight(110)
        comment_layout.addWidget(self.comment_text)

        self.content_layout.addWidget(comment_section)

        # ---------------------------------------------------------------------
        # НАСТРОЙКИ
        # ---------------------------------------------------------------------
        settings_section, settings_layout = self.create_section("⚙️ Настройки")
        settings_section.setObjectName("commentSettingsSection")
        settings_section.setStyleSheet("""
            #commentSettingsSection {
                background-color: #020617;
                border-radius: 16px;
                border: 1px solid rgba(99,102,241,0.55);
            }
            #commentSettingsSection QLabel {
                color: #e5e7eb;
            }
            #commentSettingsSection QLineEdit {
                background-color: #0f172a;
                color: #e2e8f0;
                border-radius: 10px;
                padding: 6px 10px;
                border: 1px solid rgba(51,65,85,0.6);
                font-size: 10pt;
            }
            #commentSettingsSection QLineEdit:focus {
                border: 1px solid #3b82f6;
            }
            #commentSettingsSection QCheckBox {
                color: #e5e7eb;
                font-size: 10.5pt;
            }
        """)

        settings_shadow = QGraphicsDropShadowEffect(self)
        settings_shadow.setBlurRadius(24)
        settings_shadow.setOffset(0, 4)
        settings_shadow.setColor(QColor(0, 0, 0, 150))
        settings_section.setGraphicsEffect(settings_shadow)

        # --- задержка ---
        delay_row = QHBoxLayout()
        delay_row.addWidget(QLabel("Задержка между договорами (мин):"))

        self.delay_from = QLineEdit("2")
        self.delay_from.setMaximumWidth(60)
        delay_row.addWidget(self.delay_from)

        delay_row.addWidget(QLabel("—"))

        self.delay_to = QLineEdit("5")
        self.delay_to.setMaximumWidth(60)
        delay_row.addWidget(self.delay_to)

        delay_row.addStretch()
        settings_layout.addLayout(delay_row)

        # --- поиск по дням просрочки ---
        delay_search_row = QHBoxLayout()
        self.use_delay_search = QCheckBox("Искать по дням просрочки:")

        delay_search_row.addWidget(self.use_delay_search)
        delay_search_row.addWidget(QLabel("от"))

        self.search_delay_from = QLineEdit()
        self.search_delay_from.setMaximumWidth(60)
        delay_search_row.addWidget(self.search_delay_from)

        delay_search_row.addWidget(QLabel("до"))
        self.search_delay_to = QLineEdit()
        self.search_delay_to.setMaximumWidth(60)
        delay_search_row.addWidget(self.search_delay_to)

        delay_search_row.addStretch()
        settings_layout.addLayout(delay_search_row)

        # --- чекбокс ---
        self.skip_commented = QCheckBox("Пропускать уже прокомментированные")
        settings_layout.addWidget(self.skip_commented)

        # --- использовать старые комменты ---
        self.use_old_comments = QCheckBox("Копировать ценные комментарии из истории")
        settings_layout.addWidget(self.use_old_comments)

        self.content_layout.addWidget(settings_section)

        # ---------------------------------------------------------------------
        # ЛОГ
        # ---------------------------------------------------------------------
        log_section, log_layout = self.create_section("📋 Лог работы")
        log_section.setObjectName("commentLogSection")
        log_section.setStyleSheet("""
            #commentLogSection {
                background-color: #020617;
                border-radius: 16px;
                border: 1px solid rgba(56,189,248,0.55);
            }
            #commentLogSection QLabel {
                color: #e5e7eb;
            }
            QTextEdit {
                background-color: #0f172a;
                color: #e5e7eb;
                border: 1px solid #1f2937;
                border-radius: 12px;
                padding: 10px;
                font-family: 'Consolas';
                font-size: 10pt;
            }
            QScrollBar:vertical {
                background: #020617;
                width: 10px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #22d3ee,
                    stop:1 #6366f1
                );
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #38bdf8;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
        """)

        log_shadow = QGraphicsDropShadowEffect(self)
        log_shadow.setBlurRadius(26)
        log_shadow.setOffset(0, 5)
        log_shadow.setColor(QColor(0, 0, 0, 170))
        log_section.setGraphicsEffect(log_shadow)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(200)
        log_layout.addWidget(self.log_output)

        # --- статус ---
        progress_row = QHBoxLayout()
        self.progress_label = QLabel("Отправлено комментариев: 0")
        self.progress_label.setFont(QFont("Segoe UI Semibold", 10))
        self.progress_label.setStyleSheet("color: #93c5fd;")
        progress_row.addWidget(self.progress_label)
        progress_row.addStretch()

        log_layout.addLayout(progress_row)

        self.content_layout.addWidget(log_section)

        # ---------------------------------------------------------------------
        # КНОПКИ
        # ---------------------------------------------------------------------
        actions_row = QHBoxLayout()
        actions_row.addStretch()

        btn_base = """
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
                border-color: #38bdf8;
                color: #f9fafb;
            }
            QPushButton:pressed {
                border-color: #22c55e;
            }
            QPushButton:disabled {
                color: #4b5563;
                border-color: rgba(31,41,55,0.8);
                background-color: #020617;
            }
        """

        # START
        self.start_btn = QPushButton("🚀 Начать отправку")
        self.start_btn.clicked.connect(self.start_comments)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet(btn_base + """
            QPushButton {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #22c55e,
                    stop:1 #15803d
                );
                border-color: rgba(34,197,94,0.85);
            }
            QPushButton:hover {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4ade80,
                    stop:1 #22c55e
                );
            }
        """)
        actions_row.addWidget(self.start_btn)

        # STOP
        self.stop_btn = QPushButton("⏹ Остановить")
        self.stop_btn.clicked.connect(self.stop_comments)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setStyleSheet(btn_base + """
            QPushButton {
                background-color: #7f1d1d;
                color: #fca5a5;
                border-color: rgba(248,113,113,0.8);
            }
            QPushButton:hover {
                background-color: #991b1b;
                border-color: #fecaca;
            }
        """)
        actions_row.addWidget(self.stop_btn)

        # CLEAR LOG
        clear_log_btn = QPushButton("🧹 Очистить лог")
        clear_log_btn.clicked.connect(lambda: self.log_output.clear())
        clear_log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_log_btn.setStyleSheet(btn_base)
        actions_row.addWidget(clear_log_btn)

        self.content_layout.addLayout(actions_row)

        # ---------------------------------------------------------------------
        # ЗАГРУЗКА НАСТРОЕК КОММЕНТАРИЕВ
        # ---------------------------------------------------------------------
        s = self.settings.get_comment_settings()

        self.comment_text.setText(s.get("text", ""))

        self.delay_from.setText(s.get("delay_from", "2"))
        self.delay_to.setText(s.get("delay_to", "5"))

        self.use_delay_search.setChecked(s.get("use_delay_search", False))
        self.search_delay_from.setText(s.get("search_delay_from", ""))
        self.search_delay_to.setText(s.get("search_delay_to", ""))

        self.skip_commented.setChecked(s.get("skip_commented", False))
        self.use_old_comments.setChecked(s.get("use_old_comments", False))


        # ---------------------------------------------------------------------
        # WARNING IF PROCESSOR MISSING
        # ---------------------------------------------------------------------
        if not PROCESSOR_AVAILABLE:
            warning = QLabel(
                "⚠️ Процессор комментариев не найден!\n"
                "Убедитесь, что файл comments_processor.py находится в корне."
            )
            warning.setWordWrap(True)
            warning.setStyleSheet("""
                color: #fca5a5;
                background-color: rgba(127,29,29,0.5);
                border: 1px solid #b91c1c;
                border-radius: 10px;
                padding: 8px 10px;
            """)
            self.content_layout.insertWidget(0, warning)

    # ============================================================
    # ЛОГИКА (без изменений)
    # ============================================================

    def add_log(self, message):
        self.log_output.append(message)
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_progress(self, count):
        self.progress_label.setText(f"Отправлено комментариев: {count}")

    def start_comments(self):

        # ---------------------------------------------
        # СОХРАНЕНИЕ НАСТРОЕК КОММЕНТАРИЕВ
        # ---------------------------------------------
        self.settings.set_comment_settings({
            "text": self.comment_text.toPlainText(),
            "delay_from": self.delay_from.text(),
            "delay_to": self.delay_to.text(),
            "use_delay_search": self.use_delay_search.isChecked(),
            "search_delay_from": self.search_delay_from.text(),
            "search_delay_to": self.search_delay_to.text(),
            "skip_commented": self.skip_commented.isChecked(),
            "use_old_comments": self.use_old_comments.isChecked(),
        })

        login_url = self.settings.get_login_url()
        username = self.settings.get_username()
        password = self.settings.get_password()

        if not all([login_url, username, password]):
            QMessageBox.warning(
                self,
                "Ошибка",
                "Сначала настройте аккаунт!"
            )
            return

        if not self.comment_text.toPlainText().strip():
            QMessageBox.warning(self, "Ошибка", "Введите текст комментария!")
            return

        # задержки
        try:
            delay_from = int(self.delay_from.text())
            delay_to = int(self.delay_to.text())
            if delay_from < 0 or delay_to < 0 or delay_from > delay_to:
                raise ValueError()
        except:
            QMessageBox.warning(self, "Ошибка", "Неверная задержка!")
            return

        if not PROCESSOR_AVAILABLE:
            QMessageBox.critical(self, "Ошибка", "Процессор недоступен!")
            return

        comments = [
            c.strip() for c in self.comment_text.toPlainText().splitlines() if c.strip()
        ]

        if not comments:
            QMessageBox.warning(self, "Ошибка", "Нет комментариев!")
            return

        self.add_log(f"📝 Загружено комментариев: {len(comments)}")

        kwargs = {}
        if self.use_delay_search.isChecked():
            kwargs["use_delay_search"] = True
            if self.search_delay_from.text():
                kwargs["search_delay_from"] = self.search_delay_from.text()
            if self.search_delay_to.text():
                kwargs["search_delay_to"] = self.search_delay_to.text()

        if self.use_old_comments.isChecked():
            kwargs["use_old_comments"] = True
        
        # ВАЖНО: Передаём skip_commented
        kwargs["skip_commented"] = self.skip_commented.isChecked()

        # очистка
        self.log_output.clear()
        self.progress_label.setText("Отправлено комментариев: 0")

        # создаём worker
        self.worker = CommentsWorker(
            login_url,
            username,
            password,
            comments,
            delay_from * 60,
            delay_to * 60,
            **kwargs
        )

        self.worker.log_signal.connect(self.add_log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_worker_finished)
        self.worker.error_signal.connect(self.on_worker_error)

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.add_log("=" * 60)
        self.add_log("🚀 Запуск обработки комментариев...")
        self.add_log("=" * 60)

        self.worker.start()

        # Регистрируем worker в главном окне для корректного закрытия
        if hasattr(self.parent(), 'register_worker'):
            self.parent().register_worker(self.worker)


    def stop_comments(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.add_log("⏹️ Команда остановки отправлена...")

    def on_worker_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.add_log("=" * 60)
        self.add_log("✅ Обработка завершена")
        self.add_log("=" * 60)

    def on_worker_error(self, msg):
        self.add_log(f"❌ ОШИБКА: {msg}")
        QMessageBox.critical(self, "Ошибка", msg)