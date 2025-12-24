# -*- coding: utf-8 -*-
"""
🔐 License Dialog - диалог активации с демо-режимом
Проверка license.key или активация демо на 7 дней
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                             QMessageBox, QHBoxLayout, QTextEdit)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from license_checker_offline import LicenseChecker
from demo_manager import DemoManager
from hwid_generator import get_hwid
from settings_manager import get_settings_manager


class LicenseDialog(QDialog):
    """Диалог активации лицензии"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.license_checker = LicenseChecker()
        self.demo_manager = DemoManager()
        self.license_valid = False
        
        self.setup_ui()
        self.check_license_or_demo()
    
    def setup_ui(self):
        """Настройка интерфейса"""
        self.setWindowTitle("🔐 Активация программы")
        self.setFixedSize(600, 400)
        self.setModal(True)
        
        # Окно всегда поверх
        self.setWindowFlags(
            self.windowFlags() | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowSystemMenuHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        
        # Центрируем на экране
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - 600) // 2
        y = (screen.height() - 400) // 2
        self.move(x, y)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Заголовок
        title = QLabel("Активация программы")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # HWID
        hwid_label = QLabel(f"🔐 HWID этого компьютера:")
        layout.addWidget(hwid_label)
        
        self.hwid_text = QTextEdit()
        self.hwid_text.setPlainText(get_hwid())
        self.hwid_text.setMaximumHeight(60)
        self.hwid_text.setReadOnly(True)
        self.hwid_text.setStyleSheet("""
            QTextEdit {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                padding: 5px;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.hwid_text)
        
        # Инструкция
        info = QLabel(
            "📋 Инструкция:\n"
            "1. Скопируйте HWID и отправьте администратору\n"
            "2. Получите файл license.key\n"
            "3. Положите файл рядом с программой\n"
            "4. Нажмите 'Активировать'\n\n"
            "ИЛИ используйте демо-режим на 7 дней"
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Статус
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        
        self.activate_btn = QPushButton("✅ Активировать")
        self.activate_btn.clicked.connect(self.check_license)
        self.activate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.demo_btn = QPushButton("🎮 Демо режим (7 дней)")
        self.demo_btn.clicked.connect(self.activate_demo)
        self.demo_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        
        self.cancel_btn = QPushButton("❌ Выход")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        
        btn_layout.addWidget(self.activate_btn)
        btn_layout.addWidget(self.demo_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        # Поднимаем на передний план
        self.raise_()
        self.activateWindow()
    
    def check_license_or_demo(self):
        """Проверяет лицензию или демо при запуске"""
        # Сначала проверяем лицензию
        # Получаем номер из настроек
        sm = get_settings_manager()
        current_phone = sm.get_username()  # username это номер телефона
        
        result = self.license_checker.check_license(current_phone=current_phone)
        
        if result['valid']:
            # Лицензия валидна - молча закрываем диалог
            self.license_valid = True
            self.accept()
            return
        
        # Лицензии нет - проверяем демо
        demo_status = self.demo_manager.check_demo()
        
        if demo_status['valid']:
            # Демо активно - молча закрываем диалог
            self.license_valid = True
            self.accept()
            return
        
        # Ни лицензии, ни демо - показываем диалог
        self.status_label.setText(
            "⚠️ Лицензия не найдена\n"
            "Активируйте лицензию или используйте демо-режим"
        )
        self.status_label.setStyleSheet("color: orange;")
    
    def check_license(self):
        """Проверка лицензии"""
        self.status_label.setText("⏳ Проверка лицензии...")
        self.status_label.setStyleSheet("color: blue;")
        
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        # Получаем номер из настроек
        sm = get_settings_manager()
        current_phone = sm.get_username()  # username это номер телефона
        
        result = self.license_checker.check_license(current_phone=current_phone)
        
        if result['valid']:
            # Лицензия валидна
            self.license_valid = True
            self.status_label.setText(result['message'])
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            
            QMessageBox.information(
                self,
                "✅ Активация успешна",
                result['message']
            )
            
            self.accept()
        else:
            # Лицензия не валидна
            self.license_valid = False
            self.status_label.setText(result['message'])
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            
            QMessageBox.critical(
                self,
                "❌ Ошибка активации",
                result['message'] + "\n\nПоложите файл license.key рядом с программой."
            )
    
    def activate_demo(self):
        """Активация демо-режима"""
        # Проверяем доступность демо
        if not self.demo_manager.is_demo_available():
            QMessageBox.warning(
                self,
                "⚠️ Демо недоступно",
                "Демо-режим уже использовался на этом компьютере!\n\n"
                "Для получения полной версии свяжитесь с администратором."
            )
            return
        
        # Подтверждение активации
        reply = QMessageBox.question(
            self,
            "🎮 Активация демо-режима",
            "Активировать демо-режим на 7 дней?\n\n"
            "⚠️ ВНИМАНИЕ: Демо можно активировать только ОДИН РАЗ на этом компьютере!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Активируем демо
        result = self.demo_manager.activate_demo()
        
        if result['success']:
            self.license_valid = True
            self.status_label.setText(result['message'])
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            
            QMessageBox.information(
                self,
                "✅ Демо активировано",
                result['message']
            )
            
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "❌ Ошибка",
                result['message']
            )


# =============================================================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# =============================================================================

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    dialog = LicenseDialog()
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        print("✅ Лицензия/демо активирована!")
    else:
        print("❌ Активация отменена")
        sys.exit(1)
    
    sys.exit(0)