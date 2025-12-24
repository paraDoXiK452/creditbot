"""
🎨 Dark Futuristic Corporate Base Class (QT-SAFE)
Базовый класс для всех режимов, с премиальным дизайном и без неподдерживаемых CSS-свойств.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QScrollArea,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor


class ModeBase(QWidget):
    """Базовый класс Dark Futuristic UI для всех режимов"""

    def __init__(self, title="Режим", description="", parent=None):
        super().__init__(parent)
        self.title = title
        self.description = description
        self.init_base_ui()

    # =====================================================================
    # ГЛАВНАЯ ОСНОВА UI
    # =====================================================================
    def init_base_ui(self):
        """Создание скролл-контейнера + базовой сетки"""

        # Главный layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(22, 22, 22, 22)
        self.main_layout.setSpacing(15)

        # =====================================================
        # Скролл-область в фирменном дизайне
        # =====================================================
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #0a0f1a;
            }
            QScrollArea QWidget {
                background-color: #0a0f1a;
            }
            QScrollBar:vertical {
                background: #0a0f1a;
                width: 10px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #22d3ee,
                    stop:1 #6366f1
                );
                min-height: 40px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #38bdf8,
                    stop:1 #7c3aed
                );
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
                background: none;
            }
        """)

        # Контентная область
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 25)
        self.content_layout.setSpacing(18)

        scroll.setWidget(self.content_widget)
        self.main_layout.addWidget(scroll)

    # =====================================================================
    # СЕКЦИИ (универсальные премиальные карточки)
    # =====================================================================
    def create_section(self, title, description=""):
        """
        Создает премиальную секцию-карточку в стиле Dark Futuristic Corporate
        """

        section = QFrame()
        section.setObjectName("futuristicSection")

        section.setStyleSheet("""
            #futuristicSection {
                background-color: #020617;
                border: 1px solid rgba(148,163,184,0.45);
                border-radius: 16px;
            }
            #futuristicSection QLabel {
                color: #e5e7eb;
            }
        """)

        # Тень для секции (реальный Qt-эффект, без CSS-мусора)
        shadow = QGraphicsDropShadowEffect(section)
        shadow.setBlurRadius(26)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 170))
        section.setGraphicsEffect(shadow)

        layout = QVBoxLayout(section)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        # Заголовок
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI Semibold", 12))
        title_label.setStyleSheet("color: #f1f5f9;")
        layout.addWidget(title_label)

        # Описание
        if description:
            desc_label = QLabel(description)
            desc_label.setFont(QFont("Segoe UI", 10))
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #94a3b8;")
            layout.addWidget(desc_label)

        return section, layout

    # =====================================================================
    # КНОПКИ (универсальный дизайн)
    # =====================================================================
    def create_action_button(self, text, icon="", style="primary"):
        """
        Создает премиальную кнопку
        Styles: primary | success | warning | danger | neutral
        """

        btn = QPushButton(f"{icon} {text}".strip())
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(42)
        btn.setFont(QFont("Segoe UI Semibold", 10))

        styles = {
            "primary":  ("#2563eb", "#1d4ed8"),
            "success":  ("#22c55e", "#16a34a"),
            "warning":  ("#f59e0b", "#d97706"),
            "danger":   ("#ef4444", "#dc2626"),
            "neutral":  ("#334155", "#1e293b"),
        }
        c1, c2 = styles.get(style, styles["primary"])

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1,y2:0,
                    stop:0 {c1},
                    stop:1 {c2}
                );
                color: #f8fafc;
                border-radius: 999px;
                padding: 8px 22px;
                border: 1px solid rgba(15,23,42,0.9);
            }}
            QPushButton:hover {{
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1,y2:0,
                    stop:0 {self._lighten(c1)},
                    stop:1 {self._lighten(c2)}
                );
                border-color: rgba(56,189,248,0.9);
            }}
            QPushButton:pressed {{
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1,y2:0,
                    stop:0 {self._darken(c1)},
                    stop:1 {self._darken(c2)}
                );
            }}
            QPushButton:disabled {{
                background-color: #020617;
                color: #4b5563;
                border-color: #1f2937;
            }}
        """)

        return btn

    # =====================================================================
    # Цветовые функции
    # =====================================================================
    def _darken(self, hex_color, factor=0.8):
        """Утемняет цвет"""
        hex_color = hex_color.lstrip('#')
        r, g, b = [int(hex_color[i:i + 2], 16) for i in (0, 2, 4)]
        return "#{:02x}{:02x}{:02x}".format(
            int(r * factor), int(g * factor), int(b * factor)
        )

    def _lighten(self, hex_color, factor=1.25):
        """Осветляет цвет"""
        hex_color = hex_color.lstrip('#')
        r, g, b = [
            min(int(int(hex_color[i:i + 2], 16) * factor), 255)
            for i in (0, 2, 4)
        ]
        return "#{:02x}{:02x}{:02x}".format(r, g, b)
