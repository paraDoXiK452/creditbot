# -*- coding: utf-8 -*-
"""
⚙️ Менеджер настроек приложения (расширенный)
Сохранение и загрузка:

• Данных аккаунта
• Настроек комментариев
• Настроек звонков
• Настроек Email AI
"""

import json
import os


class SettingsManager:
    """Менеджер настроек приложения"""

    def __init__(self, settings_file="app_settings.json"):
        self.settings_file = settings_file
        self.settings = self.load_settings()

    # ======================================================================
    # БАЗОВАЯ ЛОГИКА
    # ======================================================================

    def load_settings(self):
        """Загрузка настроек из файла"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")
                return self.get_default_settings()
        return self.get_default_settings()

    def save_settings(self):
        """Сохранение настроек в файл"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
            return False

    def get_default_settings(self):
        """Настройки по умолчанию"""
        return {
            "account": {
                "login_url": "https://www.max.credit/manager/login",
                "username": "",
                "password": ""
            },
            "telegram": {
                "token": "",
                "chat_id": "",
                "notify_errors": True,
                "notify_complete": True,
                "notify_stats": False
            },
            "comments": {
                "text": "",
                "delay_from": "2",
                "delay_to": "5",
                "use_delay_search": False,
                "search_delay_from": "",
                "search_delay_to": "",
                "skip_commented": False
            },
            "calls": {
                "comments_text": "",
                "fz230": False,
                "date_until": ""
            },
            "email": {
                "gmail_email": "",
                "gmail_app_password": "",
                "ai_style": "medium",
                "check_interval": 60,
                "collector_name": "Руслан",
                "send_delay": 60,
                "max_clients": 0,
                "reply_delay": 120
            },
            "app": {
                "version": "1.1.0",
                "last_update_check": "",
                "auto_check_updates": True
            }
        }

    # Универсальный getter
    def get(self, key, default=None):
        keys = key.split('.')
        value = self.settings
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    # Универсальный setter
    def set(self, key, value):
        keys = key.split('.')
        current = self.settings
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
        self.save_settings()

    # ======================================================================
    # АККАУНТ
    # ======================================================================

    def get_login_url(self):
        return self.get('account.login_url', 'https://www.max.credit/manager/login')

    def get_username(self):
        return self.get('account.username', '')

    def get_password(self):
        return self.get('account.password', '')

    def set_account(self, login_url, username, password):
        self.set('account.login_url', login_url)
        self.set('account.username', username)
        self.set('account.password', password)

    # ======================================================================
    # КОММЕНТАРИИ
    # ======================================================================

    def get_comment_settings(self):
        return self.get("comments", {})

    def set_comment_settings(self, data: dict):
        for k, v in data.items():
            self.set(f"comments.{k}", v)

    # ======================================================================
    # ЗВОНКИ
    # ======================================================================

    def get_call_settings(self):
        return self.get("calls", {})

    def set_call_settings(self, data: dict):
        for k, v in data.items():
            self.set(f"calls.{k}", v)


    # ======================================================================
    # TELEGRAM
    # ======================================================================

    def get_telegram_token(self):
        return self.get("telegram.token", "")

    def get_telegram_chat_id(self):
        return self.get("telegram.chat_id", "")

    def get_telegram_notify_errors(self):
        return self.get("telegram.notify_errors", True)

    def get_telegram_notify_complete(self):
        return self.get("telegram.notify_complete", True)

    def get_telegram_notify_stats(self):
        return self.get("telegram.notify_stats", False)

    def set_telegram_settings(self, token="", chat_id="", notify_errors=True, 
                              notify_complete=True, notify_stats=False):
        """Сохранение всех Telegram настроек"""
        self.set("telegram.token", token)
        self.set("telegram.chat_id", chat_id)
        self.set("telegram.notify_errors", notify_errors)
        self.set("telegram.notify_complete", notify_complete)
        self.set("telegram.notify_stats", notify_stats)

    def get_telegram_settings(self):
        """Получение всех Telegram настроек"""
        return self.get("telegram", {})


    # ======================================================================
    # EMAIL AI (ОБНОВЛЕНО)
    # ======================================================================

    def get_email_settings(self):
        """Получение всех Email AI настроек"""
        email_settings = self.get("email", {})
        
        # Обеспечиваем наличие всех полей с значениями по умолчанию
        defaults = {
            "gmail_email": "",
            "gmail_app_password": "",
            "ai_style": "medium",
            "check_interval": 60,
            "collector_name": "Руслан",
            "send_delay": 60,
            "max_clients": 0,
            "reply_delay": 120
        }
        
        for key, default_value in defaults.items():
            if key not in email_settings:
                email_settings[key] = default_value
        
        return email_settings

    def set_email_settings(self, gmail_email="", gmail_app_password="", 
                          ai_style="medium", check_interval=60, 
                          collector_name="Руслан", send_delay=60, max_clients=0,
                          reply_delay=120):
        """Сохранение всех Email AI настроек"""
        self.set("email.gmail_email", gmail_email)
        self.set("email.gmail_app_password", gmail_app_password)
        self.set("email.ai_style", ai_style)
        self.set("email.check_interval", check_interval)
        self.set("email.collector_name", collector_name)
        self.set("email.send_delay", send_delay)
        self.set("email.max_clients", max_clients)
        self.set("email.reply_delay", reply_delay)



# Глобальный экземпляр
_settings_manager = None

def get_settings_manager():
    """Получить глобальный менеджер настроек"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager


def load_settings():
    """
    Загрузить настройки как словарь
    Используется в процессорах для простого доступа
    """
    manager = get_settings_manager()
    return manager.settings