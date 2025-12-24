"""
🎨 Главное окно — Dark Futuristic (QT-SAFE EDITION)
С реальными графическими эффектами (shadow), без неподдерживаемых CSS
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QStackedWidget, QFrame, QGraphicsDropShadowEffect,
    QApplication, QMessageBox, QDialog, QPushButton, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

# Импорт системы лицензирования (офлайн)
from license_dialog_offline import LicenseDialog

# Импорт системы автообновления
from updater import UpdateChecker, UpdateDownloader, CURRENT_VERSION, execute_update_bat

from config import *
from ui.sidebar import Sidebar
from ui.widgets.log_widget import LogWidget
from ui.modes import (
    AccountSettingsMode,
    BankruptcyMode,
    CommentsMode,
    CallsMode,
    WriteoffsMode,
    PaymentLinksMode,
    PasswordResetMode,
    EmailAIMode,
    OnlineStatsMode,  # ← Режим онлайн-статистики
    BackgroundTasksMode
)


# =============================================================================
# ДИАЛОГ ОБНОВЛЕНИЯ
# =============================================================================

class UpdateDialog(QDialog):
    """Диалог проверки и установки обновлений"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Обновление CreditBot")
        self.setFixedSize(450, 250)  # Увеличено для лучшего отображения текста
        self.setModal(True)
        
        self.checker = None
        self.downloader = None
        self.download_url = None
        self.version = None
        self.bat_path = None  # ← НОВОЕ: путь к BAT файлу
        
        self.setup_ui()
    
    def setup_ui(self):
        """Создание интерфейса диалога"""
        # Устанавливаем светлый фон с чёрным текстом для отличной видимости
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: black;
                font-size: 13pt;
                font-weight: bold;
                background-color: white;
                padding: 10px;
            }
            QPushButton {
                color: black;
                background-color: #e0e0e0;
                border: 1px solid #999;
                padding: 10px;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #0078d4;
                color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        self.label = QLabel("Проверка обновлений...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setMinimumHeight(100)  # Минимальная высота для отображения текста
        layout.addWidget(self.label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.btn_update = QPushButton("Обновить")
        self.btn_update.setVisible(False)
        self.btn_update.clicked.connect(self.start_update)
        layout.addWidget(self.btn_update)
        
        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.reject)
        layout.addWidget(self.btn_close)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def check_updates(self):
        """Запуск проверки обновлений"""
        self.checker = UpdateChecker()
        self.checker.update_available.connect(self.on_update_available)
        self.checker.no_update.connect(self.on_no_update)
        self.checker.error.connect(self.on_error)
        self.checker.start()
    
    def on_update_available(self, version, url):
        """Обработка доступного обновления"""
        self.download_url = url
        self.version = version
        self.label.setText(f"Доступна новая версия: {version}\n"
                          f"Текущая версия: {CURRENT_VERSION}\n\n"
                          f"Нажмите 'Обновить' для установки")
        self.label.adjustSize()  # Принудительное обновление размера
        self.btn_update.setVisible(True)
    
    def on_no_update(self):
        """Обработка отсутствия обновлений"""
        self.label.setText(f"У вас установлена последняя версия\n({CURRENT_VERSION})")
        self.label.adjustSize()
    
    def on_error(self, error_msg):
        """Обработка ошибки проверки"""
        self.label.setText(f"Ошибка проверки обновлений:\n{error_msg}")
        self.label.adjustSize()
    
    def start_update(self):
        """Начало скачивания и установки обновления"""
        self.btn_update.setEnabled(False)
        self.btn_close.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.label.setText("Скачивание обновления...")
        
        self.downloader = UpdateDownloader(self.download_url, self.version)
        self.downloader.progress.connect(self.progress_bar.setValue)
        self.downloader.finished.connect(self.on_download_finished)  # ✅ Новый метод
        self.downloader.error.connect(self.on_update_error)
        self.downloader.start()
    
    def on_download_finished(self, bat_path: str):
        """
        ✅ НОВЫЙ МЕТОД: Обработка завершения скачивания
        Теперь finished возвращает путь к BAT файлу
        """
        self.bat_path = bat_path
        self.label.setText("Обновление готово к установке!\n\n"
                          "Приложение будет закрыто и перезапущено.")
        self.progress_bar.setVisible(False)
        
        # Показываем MessageBox с подтверждением
        reply = QMessageBox.question(
            self,
            "Установка обновления",
            "Обновление готово к установке.\n"
            "Приложение будет закрыто и перезапущено.\n\n"
            "Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # ✅ Запускаем BAT из главного потока
            print(f"[UPDATE] Запуск обновления из главного потока...")
            print(f"[UPDATE] BAT файл: {self.bat_path}")
            execute_update_bat(self.bat_path)
        else:
            # Пользователь отменил установку
            self.btn_update.setEnabled(True)
            self.btn_close.setEnabled(True)
            self.label.setText("Установка обновления отменена.\n"
                              "Вы можете установить его позже.")
    
    def on_update_error(self, error_msg):
        """Обработка ошибки обновления"""
        self.btn_update.setEnabled(True)
        self.btn_close.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.label.setText(f"Ошибка обновления:\n{error_msg}")


# =============================================================================
# ГЛАВНОЕ ОКНО
# =============================================================================


class MainWindow(QMainWindow):
    """Главное окно приложения с эффектами"""

    def __init__(self):
        super().__init__()
        
        # ═════════════════════════════════════════════════════════════════
        # 🔐 ПРОВЕРКА ЛИЦЕНЗИИ (ОФЛАЙН)
        # ═════════════════════════════════════════════════════════════════
        
        from license_checker_offline import LicenseChecker
        from demo_manager import DemoManager
        
        # Проверяем лицензию и демо БЕЗ диалога
        license_checker = LicenseChecker()
        demo_manager = DemoManager()
        
        license_result = license_checker.check_license()
        demo_result = demo_manager.check_demo()
        
        # Если лицензия ИЛИ демо валидны - пропускаем диалог
        if license_result['valid']:
            print(f"✅ Лицензия активирована: {license_result['message']}")
        elif demo_result['valid']:
            print(f"✅ Демо активно: {demo_result['message']}")
        else:
            # Ни лицензии, ни демо нет - показываем диалог
            dialog = LicenseDialog(parent=self)
            
            if dialog.exec() != QDialog.DialogCode.Accepted:
                # Лицензия/демо не активированы - закрываем программу
                import sys
                print("❌ Лицензия не активирована. Программа закрывается.")
                sys.exit(0)
            
            print("✅ Лицензия/демо активированы")
        
        # ═════════════════════════════════════════════════════════════════
        # 🎨 ОБЫЧНАЯ ИНИЦИАЛИЗАЦИЯ
        # ═════════════════════════════════════════════════════════════════
        
        self.current_mode = "account_settings"
        self.active_workers = []  # Отслеживание активных worker-потоков
        
        # Модуль онлайн-статистики
        self.online_stats = None
        self.online_stats_thread = None
        
        self.init_ui()
        self.apply_style_effects()
        
        # Автозапуск online_statistics
        self.log_widget.log_info("🔄 Автозапуск online_statistics...")
        QTimer.singleShot(2000, self.start_online_stats_from_tg)  # Через 2 сек после запуска
        
        # Автопроверка обновлений (через 5 секунд после запуска)
        QTimer.singleShot(5000, self.check_updates_on_startup)

    # =====================================================================
    # UI
    # =====================================================================

    def init_ui(self):
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # === ЦЕНТРАЛЬНЫЙ КОНТЕЙНЕР ===
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === САЙДБАР ===
        self.sidebar = Sidebar(self)
        self.sidebar.mode_changed.connect(self.switch_mode)
        main_layout.addWidget(self.sidebar)

        # === ПРАВАЯ ЧАСТЬ ===
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # HEADER
        self.header = self.create_header()
        right_layout.addWidget(self.header)

        # STACKED WIDGET
        self.stacked_widget = QStackedWidget()
        right_layout.addWidget(self.stacked_widget, stretch=1)

        # LOG PANEL
        self.log_widget = LogWidget()
        right_layout.addWidget(self.log_widget)

        main_layout.addWidget(right, stretch=1)

        # === МОДЫ ===
        self.modes = {
            "account_settings": AccountSettingsMode(self),
            "bankruptcy": BankruptcyMode(self),
            "comments": CommentsMode(self),
            "calls": CallsMode(self),
            "writeoffs": WriteoffsMode(self),
            "payment_links": PaymentLinksMode(self),
            "password_reset": PasswordResetMode(self),
        }
        
        # Отладка: EmailAIMode
        print("✅ До EmailAIMode")
        try:
            self.modes["email_ai"] = EmailAIMode(self)
            print("✅ EmailAIMode создан!")
        except Exception as e:
            print(f"❌ Ошибка создания EmailAIMode: {e}")
            import traceback
            traceback.print_exc()
        
        # Режим онлайн-статистики
        print("✅ До OnlineStatsMode")
        try:
            self.modes["online_stats"] = OnlineStatsMode(self)
            print("✅ OnlineStatsMode создан!")
        except Exception as e:
            print(f"❌ Ошибка создания OnlineStatsMode: {e}")
            import traceback
            traceback.print_exc()
        
        self.modes["background_tasks"] = BackgroundTasksMode(self)

        for mode in self.modes.values():
            self.stacked_widget.addWidget(mode)

        self.status_bar = self.statusBar()
        self.update_status("Готов к работе")

        self.switch_mode("account_settings")
        
        # Регистрируем обработчики команд из Telegram
        self.register_telegram_commands()

    # =====================================================================
    # HEADER
    # =====================================================================

    def create_header(self):
        header = QFrame()
        header.setObjectName("mainHeader")
        header.setFixedHeight(72)

        # ТЕНЬ HEADER (реальный Qt эффект)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(22)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 170))
        header.setGraphicsEffect(shadow)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(22, 15, 22, 15)
        layout.setSpacing(10)

        self.header_label = QLabel()
        self.header_label.setFont(QFont("Segoe UI Semibold", 17))

        layout.addWidget(self.header_label)
        layout.addStretch()
        
        # Кнопка проверки обновлений
        self.btn_check_updates = QPushButton("🔄 Обновления")
        self.btn_check_updates.setToolTip("Проверить наличие новой версии программы")
        self.btn_check_updates.setFixedSize(130, 36)
        self.btn_check_updates.clicked.connect(self.check_for_updates)
        layout.addWidget(self.btn_check_updates)

        return header

    # =====================================================================
    # SWITCH
    # =====================================================================

    def switch_mode(self, mode_name):
        if mode_name not in self.modes:
            return

        self.current_mode = mode_name
        config = MODE_CONFIG[mode_name]

        widget = self.modes[mode_name]
        self.stacked_widget.setCurrentWidget(widget)

        self.header_label.setText(f"{config['icon']}  {config['name']}")
        self.update_status(f"Режим: {config['name']}")

        self.log_widget.log_info(f"Переключен режим → {config['name']}")

    # =====================================================================
    # STATUS BAR
    # =====================================================================

    def update_status(self, message):
        self.status_bar.showMessage(message)

    # =====================================================================
    # QT-SAFE STYLE
    # =====================================================================

    def apply_style_effects(self):
        """QT SAFE PREMIUM STYLE — без transition/backdrop/text-shadow"""

        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a0f1a;
            }

            /* HEADER */
            #mainHeader {
                background-color: #0f172a;
                border-bottom: 1px solid rgba(148,163,184,0.23);
            }

            QLabel {
                color: #e5e7eb;
            }

            QStatusBar {
                background-color: #0f172a;
                color: #94a3b8;
                border-top: 1px solid rgba(148,163,184,0.25);
                padding-left: 10px;
                font-size: 11px;
            }
        """)

    # =====================================================================

    def register_worker(self, worker):
        """Регистрация активного worker-потока"""
        self.active_workers.append(worker)
        # Удаляем из списка после завершения
        worker.finished.connect(lambda: self._unregister_worker(worker))
    
    def _unregister_worker(self, worker):
        """Удаление завершенного worker из списка"""
        if worker in self.active_workers:
            self.active_workers.remove(worker)
    def register_telegram_commands(self):
        """Регистрация обработчиков команд из Telegram бота"""
        try:
            from status_manager import get_status_manager
            from PyQt6.QtCore import QTimer
            
            sm = get_status_manager()
            
            # Используем QTimer.singleShot для безопасного вызова из другого потока
            # Комментарии
            sm.register_command_callback("start_comments", 
                lambda: QTimer.singleShot(0, self.start_comments_from_tg))
            sm.register_command_callback("stop_comments", 
                lambda: QTimer.singleShot(0, self.stop_comments_from_tg))
            
            # Звонки
            sm.register_command_callback("start_calls", 
                lambda: QTimer.singleShot(0, self.start_calls_from_tg))
            sm.register_command_callback("stop_calls", 
                lambda: QTimer.singleShot(0, self.stop_calls_from_tg))
            
            # Списания
            sm.register_command_callback("start_writeoffs", 
                lambda: QTimer.singleShot(0, self.start_writeoffs_from_tg))
            sm.register_command_callback("stop_writeoffs", 
                lambda: QTimer.singleShot(0, self.stop_writeoffs_from_tg))
            
            # Ссылки на оплату
            sm.register_command_callback("start_payment_links", 
                lambda: QTimer.singleShot(0, self.start_payment_links_from_tg))
            sm.register_command_callback("stop_payment_links", 
                lambda: QTimer.singleShot(0, self.stop_payment_links_from_tg))
            
            # Банкротство
            sm.register_command_callback("start_bankruptcy", 
                lambda: QTimer.singleShot(0, self.start_bankruptcy_from_tg))
            sm.register_command_callback("stop_bankruptcy", 
                lambda: QTimer.singleShot(0, self.stop_bankruptcy_from_tg))
            
            # Сброс паролей
            sm.register_command_callback("start_password_reset", 
                lambda: QTimer.singleShot(0, self.start_password_reset_from_tg))
            sm.register_command_callback("stop_password_reset", 
                lambda: QTimer.singleShot(0, self.stop_password_reset_from_tg))
            
            # Остановить всё
            sm.register_command_callback("stop_all", 
                lambda: QTimer.singleShot(0, self.stop_all_from_tg))
            
            # Онлайн-статистика
            sm.register_command_callback("start_online_stats", 
                lambda: QTimer.singleShot(0, self.start_online_stats_from_tg))
            sm.register_command_callback("stop_online_stats", 
                lambda: QTimer.singleShot(0, self.stop_online_stats_from_tg))
            
            print("✅ Telegram команды зарегистрированы")
        except Exception as e:
            print(f"⚠️ Не удалось зарегистрировать TG команды: {e}")
    
    def start_comments_from_tg(self):
        """Запуск комментариев из Telegram"""
        print("🤖 TG команда: Запуск комментариев")
        self.switch_mode("comments")
        # Вызываем метод напрямую вместо click()
        self.modes["comments"].start_comments()
    
    def stop_comments_from_tg(self):
        """Остановка комментариев из Telegram"""
        print("🤖 TG команда: Остановка комментариев")
        # Вызываем метод напрямую
        self.modes["comments"].stop_comments()
    
    def start_calls_from_tg(self):
        """Запуск звонков из Telegram"""
        print("🤖 TG команда: Запуск звонков")
        self.switch_mode("calls")
        # Вызываем метод напрямую
        self.modes["calls"].start_calls()
    
    def stop_calls_from_tg(self):
        """Остановка звонков из Telegram"""
        print("🤖 TG команда: Остановка звонков")
        # Вызываем метод напрямую
        self.modes["calls"].stop_calls()
    
    def start_writeoffs_from_tg(self):
        """Запуск списаний из Telegram"""
        print("🤖 TG команда: Запуск списаний")
        self.switch_mode("writeoffs")
        # Вызываем метод напрямую
        self.modes["writeoffs"].start_writeoffs()
    
    def stop_writeoffs_from_tg(self):
        """Остановка списаний из Telegram"""
        print("🤖 TG команда: Остановка списаний")
        # Вызываем метод напрямую
        self.modes["writeoffs"].stop_writeoffs()
    
    def start_payment_links_from_tg(self):
        """Запуск отправки ссылок на оплату из Telegram"""
        print("🤖 TG команда: Запуск отправки ссылок на оплату")
        self.switch_mode("payment_links")
        # Вызываем метод напрямую
        self.modes["payment_links"].start_payment_links()
    
    def stop_payment_links_from_tg(self):
        """Остановка отправки ссылок на оплату из Telegram"""
        print("🤖 TG команда: Остановка отправки ссылок на оплату")
        # Вызываем метод напрямую
        self.modes["payment_links"].stop_payment_links()
    
    def start_bankruptcy_from_tg(self):
        """Запуск банкротства из Telegram (файл уже загружен)"""
        import os
        print("🤖 TG команда: Запуск банкротства")
        
        # Переключаемся на режим банкротства
        self.switch_mode("bankruptcy")
        
        # Путь к загруженному файлу
        file_path = os.path.join("shared", "bankruptcy_file.xlsx")
        
        if not os.path.exists(file_path):
            print("❌ Файл банкротства не найден!")
            return
        
        # Устанавливаем путь к файлу в режиме
        self.modes["bankruptcy"].file_path = file_path
        
        # Запускаем обработку
        self.modes["bankruptcy"].start_bankruptcy()
    
    def start_password_reset_from_tg(self):
        """Запуск сброса паролей из Telegram (файл уже загружен)"""
        import os
        print("🤖 TG команда: Запуск сброса паролей")
        
        # Переключаемся на режим
        self.switch_mode("password_reset")
        
        # Путь к загруженному файлу
        file_path = os.path.join("shared", "password_reset_file.xlsx")
        
        if not os.path.exists(file_path):
            print("❌ Файл сброса паролей не найден!")
            return
        
        # Устанавливаем путь к файлу
        self.modes["password_reset"].file_path = file_path
        
        # Запускаем обработку
        self.modes["password_reset"].start_password_reset()
    
    def stop_bankruptcy_from_tg(self):
        """Остановка банкротства из Telegram"""
        print("🤖 TG команда: Остановка банкротства")
        self.modes["bankruptcy"].stop_check()
    
    def stop_password_reset_from_tg(self):
        """Остановка сброса паролей из Telegram"""
        print("🤖 TG команда: Остановка сброса паролей")
        self.modes["password_reset"].stop_reset()
    
    def stop_all_from_tg(self):
        """Остановка всех режимов из Telegram"""
        print("🤖 TG команда: Остановка всех режимов")
        for mode_name in ["comments", "calls", "writeoffs", "payment_links"]:
            mode = self.modes[mode_name]
            if hasattr(mode, 'stop_comments'):
                mode.stop_comments()
            elif hasattr(mode, 'stop_calls'):
                mode.stop_calls()
            elif hasattr(mode, 'stop_writeoffs'):
                mode.stop_writeoffs()
            elif hasattr(mode, 'stop_payment_links'):
                mode.stop_payment_links()
    
    def start_online_stats_from_tg(self):
        """Запуск онлайн-статистики из Telegram"""
        print("🤖 TG команда: Запуск онлайн-статистики")
        
        try:
            # Получаем настройки из settings_manager
            from settings_manager import get_settings_manager
            settings = get_settings_manager()
            url = settings.get_login_url()  # ← исправлено
            phone = settings.get_username()  # ← исправлено
            password = settings.get_password()
            
            if not all([url, phone, password]):
                print("❌ Не заполнены данные авторизации")
                self.log_widget.log_error("❌ Не заполнены данные авторизации для онлайн-статистики")
                return
            
            # Импортируем модуль онлайн-статистики
            try:
                from online_statistics import OnlineStatistics
            except ImportError:
                print("❌ Модуль online_statistics.py не найден")
                self.log_widget.log_error("❌ Модуль online_statistics.py не найден")
                return
            
            # Проверяем, не запущен ли уже
            if self.online_stats and self.online_stats.is_running:
                print("⚠️ Онлайн-статистика уже запущена")
                self.log_widget.log_warning("⚠️ Онлайн-статистика уже запущена")
                return
            
            # Создаём экземпляр модуля статистики
            # telegram_bot больше не нужен - используется telegram_manager
            self.online_stats = OnlineStatistics(
                url=url,
                phone=phone,
                password=password
            )
            
            # Запускаем в отдельном потоке
            import threading
            self.online_stats_thread = threading.Thread(
                target=self._run_online_stats,
                daemon=True
            )
            self.online_stats_thread.start()
            
            print("✅ Онлайн-статистика запущена")
            self.log_widget.log_success("✅ Онлайн-статистика запущена в фоновом режиме")
            
        except Exception as e:
            print(f"❌ Ошибка запуска онлайн-статистики: {e}")
            self.log_widget.log_error(f"❌ Ошибка запуска онлайн-статистики: {e}")
            import traceback
            traceback.print_exc()
    
    def _run_online_stats(self):
        """Запуск онлайн-статистики в отдельном потоке"""
        import asyncio
        
        try:
            # Создаём новый event loop для этого потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Запускаем мониторинг
            self.online_stats.is_running = True
            loop.run_until_complete(self.online_stats.monitoring_loop())
        except Exception as e:
            print(f"❌ Ошибка в потоке онлайн-статистики: {e}")
            import traceback
            traceback.print_exc()
    
    def stop_online_stats_from_tg(self):
        """Остановка онлайн-статистики из Telegram"""
        print("🤖 TG команда: Остановка онлайн-статистики")
        
        if self.online_stats:
            self.online_stats.stop()
            self.log_widget.log_info("🛑 Команда остановки онлайн-статистики отправлена")
            print("✅ Команда остановки отправлена")
        else:
            self.log_widget.log_warning("⚠️ Онлайн-статистика не запущена")
            print("⚠️ Онлайн-статистика не запущена")
    
    
    # =====================================================================
    # АВТООБНОВЛЕНИЕ
    # =====================================================================
    
    def check_for_updates(self):
        """Открывает диалог проверки обновлений"""
        dialog = UpdateDialog(self)
        dialog.check_updates()
        dialog.exec()
    
    def check_updates_on_startup(self):
        """Автоматическая проверка при запуске (в фоне)"""
        from settings_manager import get_settings_manager
        from datetime import datetime, timedelta
        
        settings_manager = get_settings_manager()
        
        # Проверяем настройку автообновления
        if not settings_manager.get('app.auto_check_updates', True):
            return
        
        # Проверяем не чаще раза в день
        last_check = settings_manager.get('app.last_update_check', '')
        
        if last_check:
            try:
                last_dt = datetime.fromisoformat(last_check)
                if datetime.now() - last_dt < timedelta(days=1):
                    return  # Недавно проверяли
            except:
                pass
        
        # Проверяем в фоне
        checker = UpdateChecker()
        
        def on_update_found(version, url):
            reply = QMessageBox.question(
                self,
                "Обновление доступно",
                f"Доступна новая версия {version}\nУстановить сейчас?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.check_for_updates()
        
        checker.update_available.connect(on_update_found)
        
        # Сохраняем время проверки
        settings_manager.set('app.last_update_check', datetime.now().isoformat())
        
        checker.start()
    
    # =====================================================================
    # ЗАКРЫТИЕ ОКНА
    # =====================================================================
    
    def closeEvent(self, event):
        """Простая проверка - не даем закрыть пока есть активные задачи"""
        
        # Проверяем активные workers
        active_count = sum(1 for w in self.active_workers if w.isRunning())
        
        if active_count > 0:
            # Есть активные задачи - блокируем закрытие
            QMessageBox.warning(
                self,
                "Задачи выполняются",
                f"Активных задач: {active_count}\n\n"
                "Пожалуйста, остановите все задачи перед закрытием приложения.\n"
                "Используйте кнопку '⏹ Остановить' в активных режимах."
            )
            event.ignore()  # НЕ закрываем окно
        else:
            # Останавливаем онлайн-статистику если она запущена
            if self.online_stats and self.online_stats.is_running:
                print("🛑 Остановка онлайн-статистики перед закрытием...")
                self.online_stats.stop()
            
            # Убиваем все браузеры программы
            try:
                from process_manager import kill_all_browsers
                kill_all_browsers()
                print("🔪 Все браузеры программы завершены")
            except Exception as e:
                print(f"⚠️ Ошибка при завершении браузеров: {e}")
            
            # Нет активных задач - закрываем
            event.accept()
            print("✅ Программа закрыта")