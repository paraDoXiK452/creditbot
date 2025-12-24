"""
🧭 Sidebar — Dark Futuristic with real Qt effects (PyQt6-safe)
Премиальная боковая панель с тенями, без неподдерживаемых CSS-свойств
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from config import MODE_CONFIG, SIDEBAR_WIDTH


class Sidebar(QWidget):
    """Премиум-sidebar в стиле Dark Futuristic, совместимый с PyQt6"""

    mode_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_mode = None
        self.mode_buttons = {}
        self.init_ui()

    # =====================================================================
    # UI
    # =====================================================================

    def init_ui(self):
        self.setMinimumWidth(SIDEBAR_WIDTH)
        self.setMaximumWidth(260)

        self.setObjectName("FuturisticSidebar")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 20, 14, 20)
        layout.setSpacing(12)

        # ------------------------------------------------------------
        # HEADER
        # ------------------------------------------------------------
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)

        title = QLabel("🤖 Bot Control")
        title.setFont(QFont("Segoe UI Semibold", 15))
        title.setStyleSheet("color: #e2e8f0;")

        subtitle = QLabel("Control Panel")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet("color: #64748b;")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header_layout.addSpacing(8)

        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        header_widget.setObjectName("SidebarHeader")
        layout.addWidget(header_widget)

        # Тень под хедером (реальный Qt-эффект)
        header_shadow = QGraphicsDropShadowEffect(self)
        header_shadow.setBlurRadius(24)
        header_shadow.setOffset(0, 4)
        header_shadow.setColor(QColor(15, 23, 42, 180))
        header_widget.setGraphicsEffect(header_shadow)

        # ------------------------------------------------------------
        # BUTTONS
        # ------------------------------------------------------------
        for mode_key, config in MODE_CONFIG.items():
            btn = self.create_mode_button(mode_key, config["icon"], config["name"])
            self.mode_buttons[mode_key] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # ------------------------------------------------------------
        # FOOTER
        # ------------------------------------------------------------
        footer = QLabel("© 2025 Bot Control")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setFont(QFont("Segoe UI", 9))
        footer.setObjectName("SidebarFooter")
        layout.addWidget(footer)

        # Лёгкая тень под футером
        footer_shadow = QGraphicsDropShadowEffect(self)
        footer_shadow.setBlurRadius(18)
        footer_shadow.setOffset(0, -2)
        footer_shadow.setColor(QColor(15, 23, 42, 160))
        footer.setGraphicsEffect(footer_shadow)

        # Тень вокруг всей панели
        panel_shadow = QGraphicsDropShadowEffect(self)
        panel_shadow.setBlurRadius(30)
        panel_shadow.setOffset(0, 0)
        panel_shadow.setColor(QColor(15, 23, 42, 220))
        self.setGraphicsEffect(panel_shadow)

        self.apply_styles()

    # =====================================================================
    # BUTTONS
    # =====================================================================

    def create_mode_button(self, mode_key, icon, text):
        btn = QPushButton(f"{icon}  {text}")
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setMinimumHeight(40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 10))

        btn.clicked.connect(lambda: self.on_mode_clicked(mode_key))
        btn.setProperty("active", False)

        return btn

    # =====================================================================

    def on_mode_clicked(self, mode_key):
        self.set_active_mode(mode_key)
        self.mode_changed.emit(mode_key)

    def set_active_mode(self, mode_key):
        self.current_mode = mode_key

        for key, btn in self.mode_buttons.items():
            btn.setProperty("active", key == mode_key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # =====================================================================
    # STYLES (Qt-safe, без transition / text-shadow / backdrop-filter)
    # =====================================================================

    def apply_styles(self):
        """Dark Futuristic без неподдерживаемых CSS-свойств, с реальными Qt-эффектами"""

        self.setStyleSheet("""
            #FuturisticSidebar {
                background-color: #020617;
                border-right: 1px solid rgba(30, 64, 175, 0.5);
            }

            #FuturisticSidebar QLabel {
                background: transparent;
            }

            #SidebarHeader {
                background-color: #020617;
            }

            #SidebarFooter {
                color: #475569;
                padding: 6px;
            }

            #FuturisticSidebar QPushButton {
                text-align: left;
                padding: 9px 14px;
                border-radius: 10px;
                background-color: #020617;
                color: #cbd5e1;
                border: 1px solid rgba(148,163,184,0.25);
            }

            #FuturisticSidebar QPushButton:hover {
                background-color: #0b1120;
                border-color: rgba(148,163,184,0.5);
                color: #f9fafb;
            }

            #FuturisticSidebar QPushButton:pressed {
                background-color: #020617;
                border-color: #38bdf8;
            }

            #FuturisticSidebar QPushButton[active="true"] {
                background-color: #0f172a;
                color: #e0f2fe;
                border: 1px solid rgba(56,189,248,0.8);
                font-weight: 600;
            }
        """)

    # =====================================================================

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.apply_styles()