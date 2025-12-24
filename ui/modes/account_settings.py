"""
⚙️ Настройки аккаунта — Dark Futuristic Corporate UI
Современный премиальный интерфейс, единый стиль с модулем банкротств
"""

from PyQt6.QtWidgets import (
    QLabel, QLineEdit, QPushButton, QHBoxLayout, QMessageBox,
    QWidget, QVBoxLayout, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import sys
import os

from .base import ModeBase

# Импортируем менеджер настроек
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from settings_manager import get_settings_manager


class AccountSettingsMode(ModeBase):
    """Режим настроек аккаунта (премиальный dark UI)"""

    def __init__(self, parent=None):
        super().__init__(
            title="Настройки аккаунта",
            description="Глобальные данные авторизации для всех режимов",
            parent=parent
        )
        self.settings = get_settings_manager()
        self.init_mode_ui()

    def init_mode_ui(self):
        """Инициализация UI в стиле Dark Futuristic Corporate"""

        # =======================================================
        # HERO-КАРТОЧКА — крупный блок с красивым оформлением
        # =======================================================
        hero_card = QWidget()
        hero_card.setObjectName("settingsHeroCard")
        hero_layout = QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(18, 18, 18, 16)
        hero_layout.setSpacing(6)

        title_label = QLabel("⚙️ Настройки аккаунта")
        title_label.setFont(QFont("Segoe UI Semibold", 14))

        subtitle = QLabel(
            "Эти данные используются для входа на сайт во всех режимах.\n"
            "Настройки сохраняются локально и действуют глобально."
        )
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setWordWrap(True)

        badge = QLabel("GLOBAL AUTH")
        badge.setFont(QFont("Segoe UI Semibold", 9))
        badge.setAlignment(Qt.AlignmentFlag.AlignLeft)

        hero_layout.addWidget(title_label)
        hero_layout.addWidget(subtitle)
        hero_layout.addSpacing(4)
        hero_layout.addWidget(badge)

        hero_card.setStyleSheet("""
            #settingsHeroCard {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #020617,
                    stop:0.45 #020617,
                    stop:1 #111827
                );
                border-radius: 16px;
                border: 1px solid rgba(59, 130, 246, 0.55);
            }
            #settingsHeroCard QLabel {
                color: #e5e7eb;
            }
        """)

        badge.setStyleSheet("""
            QLabel {
                color: #38bdf8;
                background-color: rgba(15, 23, 42, 0.9);
                border-radius: 999px;
                padding: 5px 10px;
                border: 1px solid rgba(56, 189, 248, 0.55);
            }
        """)

        self.content_layout.addWidget(hero_card)

        # =======================================================
        # БЛОК АВТОРИЗАЦИИ — красивые поля, ровные карточки
        # =======================================================
        auth_section, auth_layout = self.create_section(
            "🔐 Данные входа",
            "Заполните логин, пароль и URL портала"
        )
        auth_section.setObjectName("authSettingsSection")

        auth_section.setStyleSheet("""
            #authSettingsSection {
                background-color: #020617;
                border-radius: 14px;
                border: 1px solid rgba(148, 163, 184, 0.6);
            }
            #authSettingsSection QLabel {
                color: #e5e7eb;
                font-size: 10.5pt;
            }
            #authSettingsSection QLineEdit {
                background-color: #0f172a;
                color: #e2e8f0;
                border-radius: 10px;
                padding: 8px 10px;
                border: 1px solid rgba(51,65,85,0.7);
                font-size: 10.5pt;
            }
            #authSettingsSection QLineEdit:focus {
                border: 1px solid #3b82f6;
                background-color: #1e293b;
            }
        """)

        # === URL ===
        url_row = QHBoxLayout()
        url_label = QLabel("URL входа:")
        self.login_url = QLineEdit()
        self.login_url.setText(self.settings.get_login_url())
        url_row.addWidget(url_label)
        url_row.addWidget(self.login_url, stretch=1)
        auth_layout.addLayout(url_row)

        # === ЛОГИН ===
        login_row = QHBoxLayout()
        login_row.addWidget(QLabel("Телефон:"))
        self.username = QLineEdit()
        self.username.setPlaceholderText("79001234567")
        self.username.setText(self.settings.get_username())
        login_row.addWidget(self.username, stretch=1)
        auth_layout.addLayout(login_row)

        # === ПАРОЛЬ ===
        pass_row = QHBoxLayout()
        pass_row.addWidget(QLabel("Пароль:"))
        self.password = QLineEdit()
        self.password.setText(self.settings.get_password())
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        pass_row.addWidget(self.password, stretch=1)
        auth_layout.addLayout(pass_row)

        # === КНОПКА "Показать пароль" ===
        show_pass_row = QHBoxLayout()
        show_pass_row.addStretch()

        self.show_password_btn = QPushButton("👁 Показать пароль")
        self.show_password_btn.setCheckable(True)
        self.show_password_btn.clicked.connect(self.toggle_password_visibility)
        self.show_password_btn.setMaximumWidth(200)
        self.show_password_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_password_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f172a;
                color: #94a3b8;
                border-radius: 10px;
                padding: 6px 12px;
                border: 1px solid rgba(51,65,85,0.6);
            }
            QPushButton:hover {
                background-color: #1e293b;
                color: #e2e8f0;
                border-color: #38bdf8;
            }
            QPushButton:checked {
                background-color: #1e293b;
                color: #4ade80;
                border-color: #22c55e;
            }
        """)

        show_pass_row.addWidget(self.show_password_btn)
        auth_layout.addLayout(show_pass_row)

        self.content_layout.addWidget(auth_section)

        # =======================================================
        # БЛОК TELEGRAM — настройки бота
        # =======================================================
        telegram_section, telegram_layout = self.create_section(
            "📱 Telegram Bot",
            "Управление и уведомления через Telegram"
        )
        telegram_section.setObjectName("telegramSettingsSection")

        telegram_section.setStyleSheet("""
            #telegramSettingsSection {
                background-color: #020617;
                border-radius: 14px;
                border: 1px solid rgba(34, 197, 94, 0.6);
            }
            #telegramSettingsSection QLabel {
                color: #e5e7eb;
                font-size: 10.5pt;
            }
            #telegramSettingsSection QLineEdit {
                background-color: #0f172a;
                color: #e2e8f0;
                border-radius: 10px;
                padding: 8px 10px;
                border: 1px solid rgba(51,65,85,0.7);
                font-size: 10.5pt;
            }
            #telegramSettingsSection QLineEdit:focus {
                border: 1px solid #22c55e;
                background-color: #1e293b;
            }
            #telegramSettingsSection QCheckBox {
                color: #e5e7eb;
                font-size: 10pt;
            }
        """)

        # === API TOKEN ===
        token_row = QHBoxLayout()
        token_label = QLabel("API Token:")
        self.tg_token = QLineEdit()
        self.tg_token.setPlaceholderText("1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
        self.tg_token.setText(self.settings.get_telegram_token())
        token_row.addWidget(token_label)
        token_row.addWidget(self.tg_token, stretch=1)
        telegram_layout.addLayout(token_row)

        # === CHAT ID ===
        chat_row = QHBoxLayout()
        chat_row.addWidget(QLabel("Chat ID:"))
        self.tg_chat_id = QLineEdit()
        self.tg_chat_id.setPlaceholderText("123456789")
        self.tg_chat_id.setText(self.settings.get_telegram_chat_id())
        chat_row.addWidget(self.tg_chat_id, stretch=1)
        telegram_layout.addLayout(chat_row)

        # === ЧЕКБОКСЫ УВЕДОМЛЕНИЙ ===
        self.tg_notify_errors = QCheckBox("✉️ Уведомления об ошибках")
        self.tg_notify_errors.setChecked(self.settings.get_telegram_notify_errors())
        telegram_layout.addWidget(self.tg_notify_errors)

        self.tg_notify_complete = QCheckBox("✅ Уведомления о завершении")
        self.tg_notify_complete.setChecked(self.settings.get_telegram_notify_complete())
        telegram_layout.addWidget(self.tg_notify_complete)

        self.tg_notify_stats = QCheckBox("📊 Периодическая статистика")
        self.tg_notify_stats.setChecked(self.settings.get_telegram_notify_stats())
        telegram_layout.addWidget(self.tg_notify_stats)

        self.content_layout.addWidget(telegram_section)


        # =======================================================
        # СТАТУС — красивый индикатор состояния аккаунта
        # =======================================================
        status_section, status_layout = self.create_section("📊 Статус")
        status_section.setObjectName("statusSection")

        status_section.setStyleSheet("""
            #statusSection {
                background-color: #020617;
                border-radius: 14px;
                border: 1px solid rgba(79, 70, 229, 0.6);
            }
            #statusSection QLabel {
                color: #e5e7eb;
            }
        """)

        self.status_label = QLabel()
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        self.update_status_label()

        self.content_layout.addWidget(status_section)

        # =======================================================
        # КНОПКИ ДЕЙСТВИЙ — премиальные неоновые кнопки
        # =======================================================
        actions_row = QHBoxLayout()
        actions_row.addStretch()

        base_btn_style = """
            QPushButton {
                background-color: #020617;
                color: #e5e7eb;
                border-radius: 999px;
                padding: 9px 22px;
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
        """

        # === Сохранить ===
        save_btn = QPushButton("💾 Сохранить")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(base_btn_style + """
            QPushButton {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #22c55e,
                    stop:1 #16a34a
                );
                color: #ecfdf5;
                border: 1px solid rgba(34, 197, 94, 0.9);
            }
            QPushButton:hover {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4ade80,
                    stop:1 #22c55e
                );
                border-color: #bbf7d0;
            }
        """)
        save_btn.clicked.connect(self.save_settings)
        actions_row.addWidget(save_btn)

        # === Очистить ===
        clear_btn = QPushButton("🗑 Очистить")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(base_btn_style + """
            QPushButton {
                background-color: #7f1d1d;
                color: #fecaca;
                border: 1px solid rgba(248,113,113,0.85);
            }
            QPushButton:hover {
                background-color: #991b1b;
                border-color: #fca5a5;
            }
        """)
        clear_btn.clicked.connect(self.clear_settings)
        actions_row.addWidget(clear_btn)

        self.content_layout.addLayout(actions_row)

    # =======================================================
    # ЛОГИКА (не изменена)
    # =======================================================
    def toggle_password_visibility(self):
        if self.show_password_btn.isChecked():
            self.password.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_password_btn.setText("🙈 Скрыть пароль")
        else:
            self.password.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_password_btn.setText("👁 Показать пароль")

    def update_status_label(self):
        username = self.settings.get_username()
        if username:
            self.status_label.setText(f"✅ Аккаунт настроен: {username}")
            self.status_label.setStyleSheet("color: #4ade80; font-weight: 600;")
        else:
            self.status_label.setText("⚠️ Аккаунт не настроен")
            self.status_label.setStyleSheet("color: #fbbf24; font-weight: 600;")

    def save_settings(self):
        login_url = self.login_url.text().strip()
        username = self.username.text().strip()
        password = self.password.text()

        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните логин и пароль!")
            return

        self.settings.set_account(login_url, username, password)
        
        # Сохранение Telegram настроек
        self.settings.set_telegram_settings(
            token=self.tg_token.text().strip(),
            chat_id=self.tg_chat_id.text().strip(),
            notify_errors=self.tg_notify_errors.isChecked(),
            notify_complete=self.tg_notify_complete.isChecked(),
            notify_stats=self.tg_notify_stats.isChecked()
        )
        self.update_status_label()

        QMessageBox.information(
            self,
            "Успех",
            "Настройки сохранены!"
        )

    def clear_settings(self):
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите очистить настройки?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.username.clear()
            self.password.clear()
            self.settings.set_account(
                "https://www.max.credit/manager/login",
                "",
                ""
            )
            self.update_status_label()
            QMessageBox.information(self, "Успех", "Настройки очищены!")