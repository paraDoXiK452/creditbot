"""
💼 Режим проверки банкротства
Загрузка Excel, проверка ФИО через сайт
"""

from PyQt6.QtWidgets import (
    QLabel, QFileDialog, QPushButton,
    QHBoxLayout, QMessageBox, QTextEdit, QWidget, QVBoxLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import threading
import os

from .base import ModeBase

# Импортируем процессор банкротства
try:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from core.bankruptcy_processor import check_bankruptcy_list
    PROCESSOR_AVAILABLE = True
except ImportError:
    PROCESSOR_AVAILABLE = False
    print("⚠️ bankruptcy_processor не найден!")


class BankruptcyWorker(QThread):
    """Рабочий поток для проверки банкротства"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(str)  # Путь к результату
    error_signal = pyqtSignal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.stop_flag = threading.Event()

    def logger_func(self, message):
        """Функция логирования для процессора"""
        self.log_signal.emit(message)

    def progress_callback(self, current, total):
        """Колбек для обновления прогресса"""
        self.progress_signal.emit(current, total)

    def run(self):
        """Запуск обработки"""
        if not PROCESSOR_AVAILABLE:
            self.error_signal.emit("Процессор банкротства не доступен!")
            return

        try:
            self.log_signal.emit("🚀 Запуск проверки банкротства...")
            result_file = check_bankruptcy_list(
                self.file_path,
                self.logger_func,
                self.stop_flag,
                self.progress_callback
            )
            if result_file:
                self.finished_signal.emit(result_file)
            else:
                self.finished_signal.emit("")
        except Exception as e:
            self.error_signal.emit(f"Ошибка: {str(e)}")
        finally:
            if not self.stop_flag.is_set():
                self.finished_signal.emit("")

    def stop(self):
        """Остановка обработки"""
        self.log_signal.emit("⏹️ Остановка...")
        self.stop_flag.set()


class BankruptcyMode(ModeBase):
    """Режим проверки банкротства (dark + neon wow UI)"""

    def __init__(self, parent=None):
        super().__init__(
            title="Проверка банкротства",
            description="Массовая проверка ФИО в реестре банкротов",
            parent=parent
        )
        self.selected_file = None
        self.file_path = None  # Путь к файлу из TG
        self.worker = None
        self.init_mode_ui()

    def init_mode_ui(self):
        """Инициализация UI режима (только UI, логика 1в1)"""

        # ========== HERO-БЛОК С ВАУ-ЭФФЕКТОМ ==========
        hero_card = QWidget()
        hero_card.setObjectName("bankruptcyHeroCard")
        hero_layout = QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(18, 16, 18, 16)
        hero_layout.setSpacing(6)

        title_label = QLabel("💼 Проверка банкротства")
        title_font = QFont("Segoe UI Semibold", 14)
        title_label.setFont(title_font)

        subtitle_label = QLabel(
            "Загрузи Excel с ФИО — бот сам проверит свежие дела о банкротстве "
            "и вернёт файл с результатами."
        )
        subtitle_label.setWordWrap(True)
        subtitle_label.setFont(QFont("Segoe UI", 10))

        hero_badge = QLabel("LIVE • kad.arbitr.ru")
        hero_badge.setAlignment(Qt.AlignmentFlag.AlignLeft)
        hero_badge.setFont(QFont("Segoe UI Semibold", 9))

        hero_layout.addWidget(title_label)
        hero_layout.addWidget(subtitle_label)
        hero_layout.addSpacing(4)
        hero_layout.addWidget(hero_badge)

        hero_card.setStyleSheet("""
            #bankruptcyHeroCard {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #020617,
                    stop:0.45 #020617,
                    stop:1 #111827
                );
                border-radius: 16px;
                border: 1px solid rgba(59, 130, 246, 0.55); /* blue-500 */
            }
            #bankruptcyHeroCard QLabel {
                color: #e5e7eb;
            }
        """)
        hero_badge.setStyleSheet("""
            QLabel {
                color: #f97316;
                background-color: rgba(15, 23, 42, 0.9);
                border-radius: 999px;
                padding: 4px 10px;
                border: 1px solid rgba(248, 113, 113, 0.65);
            }
        """)

        self.content_layout.addWidget(hero_card)

        # ========== НЕОНОВЫЙ ФАЙЛ-БЛОК ==========
        file_section, file_layout = self.create_section(
            "📂 Входной Excel-файл",
            "Файл с колонкой 'ФИО' (и при наличии — адресом). "
            "Будет создан новый файл с результатами."
        )
        file_section.setObjectName("bankruptcyFileSection")
        file_section.setStyleSheet("""
            #bankruptcyFileSection {
                background-color: #020617;
                border-radius: 14px;
                border: 1px solid rgba(148, 163, 184, 0.6); /* slate-400 */
            }
            #bankruptcyFileSection QLabel {
                color: #e5e7eb;
            }
        """)

        file_row = QHBoxLayout()
        file_row.setContentsMargins(0, 4, 0, 0)
        file_row.setSpacing(10)

        self.file_label = QLabel("Файл не выбран")
        self.file_label.setStyleSheet("color: #6b7280;")  # gray-500
        self.file_label.setFont(QFont("Segoe UI", 10))
        self.file_label.setMinimumWidth(220)

        choose_btn = QPushButton("Выбрать Excel…")
        choose_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        choose_btn.setMinimumWidth(150)
        choose_btn.setFont(QFont("Segoe UI Semibold", 10))
        choose_btn.clicked.connect(self.choose_file)
        choose_btn.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563eb,
                    stop:1 #7c3aed
                );
                color: #f9fafb;
                border-radius: 999px;
                padding: 8px 18px;
                border: 1px solid rgba(191, 219, 254, 0.65);
            }
            QPushButton:hover {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6,
                    stop:1 #8b5cf6
                );
                border-color: #bfdbfe;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
                border-color: #93c5fd;
            }
            QPushButton:disabled {
                background-color: #020617;
                color: #4b5563;
                border-color: #111827;
            }
        """)

        file_row.addWidget(self.file_label, stretch=1)
        file_row.addWidget(choose_btn, stretch=0, alignment=Qt.AlignmentFlag.AlignRight)
        file_layout.addLayout(file_row)

        self.content_layout.addWidget(file_section)

        # ========== ЛОГ-БЛОК (TERMINAL-СТИЛЬ) ==========
        log_section, log_layout = self.create_section(
            "📋 Лог работы",
            "Онлайн-лог действий: запросы к сайту, найденные дела, ошибки."
        )
        log_section.setObjectName("bankruptcyLogSection")
        log_section.setStyleSheet("""
            #bankruptcyLogSection {
                background-color: #020617;
                border-radius: 16px;
                border: 1px solid rgba(79, 70, 229, 0.6); /* indigo-600 */
            }
            #bankruptcyLogSection QLabel {
                color: #e5e7eb;
            }
        """)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(230)
        self.log_output.setFont(QFont("Consolas", 9))
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #020617;
                color: #e5e7eb;
                font-family: 'Consolas', 'JetBrains Mono', monospace;
                font-size: 9.5pt;
                border-radius: 12px;
                border: 1px solid #111827;
                padding: 10px;
            }
            QTextEdit::viewport {
                background-color: #020617;
            }
            QTextEdit QScrollBar:vertical {
                background: #020617;
                width: 10px;
                margin: 4px 0 4px 0;
                border-radius: 5px;
            }
            QTextEdit QScrollBar::handle:vertical {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #22d3ee,
                    stop:1 #6366f1
                );
                min-height: 24px;
                border-radius: 4px;
            }
            QTextEdit QScrollBar::handle:vertical:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #38bdf8,
                    stop:1 #818cf8
                );
            }
            QTextEdit QScrollBar::add-line:vertical,
            QTextEdit QScrollBar::sub-line:vertical {
                background: none;
                height: 0px;
            }
        """)
        log_layout.addWidget(self.log_output)

        progress_row = QHBoxLayout()
        progress_row.setContentsMargins(0, 4, 0, 0)

        self.progress_label = QLabel("Проверено: 0/0")
        self.progress_label.setFont(QFont("Segoe UI Semibold", 10))
        self.progress_label.setStyleSheet("color: #93c5fd;")  # blue-300

        progress_row.addWidget(self.progress_label)
        progress_row.addStretch()

        log_layout.addLayout(progress_row)
        self.content_layout.addWidget(log_section)

        # ========== КНОПКИ ДЕЙСТВИЙ ==========
        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 4, 0, 0)
        actions_row.setSpacing(10)
        actions_row.addStretch()

        base_btn_style = """
            QPushButton {
                background-color: #020617;
                color: #e5e7eb;
                border-radius: 999px;
                padding: 9px 20px;
                font-size: 10pt;
                font-weight: 600;
                border: 1px solid rgba(148, 163, 184, 0.7);
            }
            QPushButton:hover {
                background-color: #020617;
                border-color: #38bdf8;
                color: #f9fafb;
            }
            QPushButton:pressed {
                background-color: #020617;
                border-color: #22c55e;
            }
            QPushButton:disabled {
                background-color: #020617;
                color: #4b5563;
                border-color: #111827;
            }
        """

        self.start_btn = QPushButton("🚀 Начать проверку")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setFont(QFont("Segoe UI Semibold", 10))
        self.start_btn.clicked.connect(self.start_check)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet(base_btn_style + """
            QPushButton {
                background-color: qradialgradient(
                    cx:0.3, cy:0.3, radius:1.0,
                    fx:0.3, fy:0.3,
                    stop:0 #22c55e,
                    stop:1 #15803d
                );
                color: #ecfdf5;
                border-radius: 999px;
                padding: 9px 24px;
                border: 1px solid rgba(34, 197, 94, 0.9);
            }
            QPushButton:hover {
                background-color: qradialgradient(
                    cx:0.3, cy:0.3, radius:1.0,
                    fx:0.3, fy:0.3,
                    stop:0 #4ade80,
                    stop:1 #22c55e
                );
                border-color: #bbf7d0;
            }
            QPushButton:disabled {
                background-color: #022c22;
                color: #16a34a;
                border-color: #064e3b;
            }
        """)
        actions_row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹ Остановить")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setFont(QFont("Segoe UI Semibold", 10))
        self.stop_btn.clicked.connect(self.stop_check)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(base_btn_style + """
            QPushButton {
                background-color: #111827;
                color: #fecaca;
                border-radius: 999px;
                padding: 9px 18px;
                border: 1px solid rgba(248, 113, 113, 0.85);
            }
            QPushButton:hover {
                background-color: #7f1d1d;
                border-color: #fca5a5;
            }
            QPushButton:pressed {
                background-color: #450a0a;
                border-color: #ef4444;
            }
            QPushButton:disabled {
                background-color: #020617;
                color: #4b5563;
                border-color: #111827;
            }
        """)
        actions_row.addWidget(self.stop_btn)

        clear_log_btn = QPushButton("🧹 Очистить лог")
        clear_log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_log_btn.setFont(QFont("Segoe UI", 10))
        clear_log_btn.clicked.connect(lambda: self.log_output.clear())
        clear_log_btn.setStyleSheet(base_btn_style)
        actions_row.addWidget(clear_log_btn)

        self.content_layout.addLayout(actions_row)

        # ========== ПРЕДУПРЕЖДЕНИЕ, ЕСЛИ НЕТ ПРОЦЕССОРА ==========
        if not PROCESSOR_AVAILABLE:
            warning = QLabel(
                "⚠️ Процессор банкротства не найден!\n"
                "Убедитесь, что файл bankruptcy_processor.py находится в корне проекта."
            )
            warning.setWordWrap(True)
            warning.setStyleSheet("""
                color: #fca5a5;
                font-weight: 600;
                background-color: rgba(127, 29, 29, 0.55);
                border: 1px solid #b91c1c;
                border-radius: 10px;
                padding: 8px 10px;
            """)
            self.content_layout.insertWidget(0, warning)

    def add_log(self, message):
        """Добавление сообщения в лог"""
        self.log_output.append(message)
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_progress(self, current, total):
        """Обновление счетчика прогресса"""
        self.progress_label.setText(f"Проверено: {current}/{total}")

    def choose_file(self):
        """Выбор Excel файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите Excel файл",
            "",
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )

        if file_path:
            self.selected_file = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.file_label.setStyleSheet("color: #4ade80;")  # green-400
            self.start_btn.setEnabled(True)

    def start_check(self):
        """Запуск проверки"""
        # Если файл уже установлен из TG - используем его
        if self.file_path and os.path.exists(self.file_path):
            file_to_use = self.file_path
            self.add_log(f"📎 Используем файл из TG: {os.path.basename(file_to_use)}")
        elif self.selected_file:
            file_to_use = self.selected_file
        else:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите файл!")
            return

        if not PROCESSOR_AVAILABLE:
            QMessageBox.critical(
                self,
                "Ошибка",
                "Процессор банкротства недоступен!\n"
                "Проверьте наличие файла bankruptcy_processor.py"
            )
            return

        self.log_output.clear()
        self.progress_label.setText("Проверено: 0/0")

        self.worker = BankruptcyWorker(file_to_use)
        self.worker.log_signal.connect(self.add_log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_worker_finished)
        self.worker.error_signal.connect(self.on_worker_error)

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # Регистрируем worker в главном окне для корректного закрытия
        if hasattr(self.parent(), 'register_worker'):
            self.parent().register_worker(self.worker)

        self.add_log("=" * 60)
        self.add_log("🚀 Запуск проверки банкротства...")
        self.add_log("=" * 60)
        self.worker.start()

    def stop_check(self):
        """Остановка проверки"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.add_log("⏹️ Команда остановки отправлена...")

    def on_worker_finished(self, result_file):
        """Обработка завершения работы"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.add_log("=" * 60)

        if result_file:
            self.add_log("✅ Проверка завершена!")
            self.add_log(f"📄 Результаты сохранены: {result_file}")
            
            # Отправляем файл в Telegram если запущено через TG
            if self.file_path and os.path.exists(self.file_path):
                self.add_log("📤 Отправка результатов в Telegram...")
                self.send_result_to_telegram(result_file)

            reply = QMessageBox.question(
                self,
                "Проверка завершена",
                f"Результаты сохранены в:\n{result_file}\n\nОткрыть файл?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                import subprocess
                import platform
                if platform.system() == 'Windows':
                    os.startfile(result_file)
                elif platform.system() == 'Darwin':
                    subprocess.call(['open', result_file])
                else:
                    subprocess.call(['xdg-open', result_file])
        else:
            self.add_log("✅ Проверка завершена (нет данных для сохранения)")

        self.add_log("=" * 60)
    
    def send_result_to_telegram(self, file_path):
        """Отправка файла результатов в Telegram"""
        try:
            import asyncio
            from telegram_bot.tg_bot import TelegramBot
            from settings_manager import get_settings_manager
            
            settings = get_settings_manager()
            token = settings.get_telegram_token()
            chat_id = settings.get_telegram_chat_id()
            
            if not token or not chat_id:
                self.add_log("⚠️ TG настройки не заполнены")
                return
            
            # Создаём bot instance
            bot = TelegramBot(token, chat_id)
            
            # Отправляем файл асинхронно
            async def send():
                from telegram import Bot
                bot_instance = Bot(token)
                with open(file_path, 'rb') as f:
                    await bot_instance.send_document(
                        chat_id=chat_id,
                        document=f,
                        caption=f"💼 <b>Результаты проверки банкротства</b>\n\n📄 {os.path.basename(file_path)}",
                        parse_mode='HTML'
                    )
            
            # Запускаем в новом event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(send())
            loop.close()
            
            self.add_log("✅ Результаты отправлены в Telegram")
        except Exception as e:
            self.add_log(f"❌ Ошибка отправки в TG: {e}")
            print(f"Ошибка отправки файла в TG: {e}")


    def on_worker_error(self, error_msg):
        """Обработка ошибки"""
        self.add_log(f"❌ ОШИБКА: {error_msg}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.critical(self, "Ошибка", f"Произошла ошибка:\n{error_msg}")
    
    # Алиас для TG команды
    def start_bankruptcy(self):
        """Алиас для start_check (используется из TG)"""
        self.start_check()
