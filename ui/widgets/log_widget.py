"""
📝 Виджет логирования — Dark Futuristic Corporate UI (QT SAFE EDITION)
С реальными эффектами (drop shadow), без неподдерживаемых CSS свойств.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel, QFrame, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont, QTextCharFormat, QColor
from datetime import datetime


class LogWidget(QWidget):
    """Премиум-лог панель в фирменном стиле."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Интерфейс лог-панели"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === HEADER ЛОГОВ ===
        header_frame = QFrame()
        header_frame.setObjectName("logHeaderFrame")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(14, 8, 14, 8)
        header_layout.setSpacing(0)

        header = QLabel("Лог операций")
        header.setFont(QFont("Segoe UI Semibold", 11))
        header.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        header_layout.addWidget(header)

        # Стиль + реальные теневые эффекты
        header_frame.setStyleSheet("""
            #logHeaderFrame {
                background-color: #0f172a;
                border-top: 1px solid rgba(148,163,184,0.35);
                border-bottom: 1px solid rgba(30,41,59,0.7);
            }
            #logHeaderFrame QLabel {
                color: #e5e7eb;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 140))
        header_frame.setGraphicsEffect(shadow)

        layout.addWidget(header_frame)

        # === ТЕКСТОВОЕ ПОЛЕ ЛОГОВ ===
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setMinimumHeight(150)
        self.log_text.setMaximumHeight(280)

        # Аналог стеклянного эффекта через темные слои
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #020617;
                color: #e5e7eb;
                border: none;
                padding: 10px;
                font-family: "Consolas", "JetBrains Mono", monospace;
                font-size: 10pt;
            }
            QTextEdit::viewport {
                background-color: #020617;
            }

            /* Полностью QT-safe скроллбар */
            QScrollBar:vertical {
                background: #020617;
                width: 10px;
                margin: 2px 0 2px 0;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #38bdf8;
                min-height: 24px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #7dd3fc;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
        """)

        # Тень под всей лог-панелью
        text_shadow = QGraphicsDropShadowEffect(self)
        text_shadow.setBlurRadius(24)
        text_shadow.setOffset(0, -2)
        text_shadow.setColor(QColor(15, 23, 42, 180))
        self.log_text.setGraphicsEffect(text_shadow)

        layout.addWidget(self.log_text)

        # Цветовые форматы
        self.formats = {
            'info': self.create_format('#e5e7eb'),      # обычный
            'success': self.create_format('#4ade80'),   # зеленый
            'warning': self.create_format('#facc15'),   # желтый
            'error': self.create_format('#fb7185'),     # красный
            'time': self.create_format('#6b7280')       # timestamp
        }

    def create_format(self, color):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        return fmt

    # =====================================================================
    # ЛОГИРОВАНИЕ
    # =====================================================================

    @pyqtSlot(str, str)
    def log(self, message, level='info'):
        """Добавить сообщение в лог"""

        # Автоопределение категории
        if level == 'info':
            msg = message.lower()
            if any(word in msg for word in ['успех', 'завершено', 'готово', 'найдено']):
                level = 'success'
            elif any(word in msg for word in ['ошибка', 'не удалось', 'failed']):
                level = 'error'
            elif any(word in msg for word in ['предупреждение', 'warning']):
                level = 'warning'

        timestamp = datetime.now().strftime('%H:%M:%S')

        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        cursor.insertText(f"[{timestamp}] ", self.formats['time'])
        cursor.insertText(f"{message}\n", self.formats.get(level, self.formats['info']))

        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()

    def log_info(self, message):
        self.log(message, 'info')

    def log_success(self, message):
        self.log(message, 'success')

    def log_warning(self, message):
        self.log(message, 'warning')

    def log_error(self, message):
        self.log(message, 'error')

    def clear(self):
        self.log_text.clear()
