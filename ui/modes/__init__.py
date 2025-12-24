"""
Все режимы работы приложения
"""
from .base import ModeBase
from .bankruptcy import BankruptcyMode
from .comments import CommentsMode
from .calls import CallsMode
from .account_settings import AccountSettingsMode
from .writeoffs import WriteoffsMode
from .password_reset import PasswordResetMode
from .payment_links import PaymentLinksMode
from .email_ai_mode import EmailAIMode
from .online_stats_mode import OnlineStatsMode  # ← Режим онлайн-статистики

# Остальные режимы как простые заглушки для запуска
class BackgroundTasksMode(ModeBase):
    """Режим фоновых задач"""
    
    def __init__(self, parent=None):
        super().__init__(
            title="Фоновые задачи",
            description="Управление запущенными задачами",
            parent=parent
        )
        from PyQt6.QtWidgets import QLabel
        label = QLabel("Фоновые задачи\n\nЗдесь будут отображаться запущенные задачи")
        label.setWordWrap(True)
        self.content_layout.addWidget(label)

__all__ = [
    'AccountSettingsMode',
    'BankruptcyMode',
    'CommentsMode',
    'CallsMode',
    'WriteoffsMode',
    'PaymentLinksMode',
    'PasswordResetMode',
    'EmailAIMode',
    'OnlineStatsMode',  # ← Режим онлайн-статистики
    'BackgroundTasksMode'
]