# -*- coding: utf-8 -*-
"""
📊 Status Manager - управление состоянием бота
Обновление bot_status.json и чтение bot_commands.json
"""

import json
import os
import threading
import time
from datetime import datetime
from typing import Optional, Callable


class StatusManager:
    """Менеджер состояния бота и команд из Telegram"""
    
    def __init__(self, shared_dir="shared"):
        self.shared_dir = shared_dir
        self.status_file = os.path.join(shared_dir, "bot_status.json")
        self.commands_file = os.path.join(shared_dir, "bot_commands.json")
        self.logs_file = os.path.join(shared_dir, "bot_logs.txt")
        
        # Создаём папку shared если её нет
        os.makedirs(shared_dir, exist_ok=True)
        
        # Инициализируем статус
        self.status = {
            "comments": {"running": False, "processed": 0, "last_error": None, "stop_requested": False},
            "calls": {"running": False, "processed": 0, "last_error": None, "stop_requested": False},
            "writeoffs": {"running": False, "processed": 0, "last_error": None, "stop_requested": False},
            "payment_links": {"running": False, "processed": 0, "last_error": None, "stop_requested": False},
            "online_stats": {"running": False, "clients_count": 0, "sbor": 0.0, "last_error": None, "stop_requested": False},
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Сохраняем начальный статус
        self.save_status()
        
        # Поток для чтения команд
        self.command_checker_thread = None
        self.command_checker_running = False
        self.command_callbacks = {}
    
    # =============================================================================
    # УПРАВЛЕНИЕ СТАТУСОМ
    # =============================================================================
    
    def update_mode_status(self, mode: str, running: bool = None, 
                          processed: int = None, last_error: str = None):
        """
        Обновляет статус конкретного режима
        
        Args:
            mode: "comments", "calls", "writeoffs"
            running: True/False/None (не обновлять)
            processed: число обработанных или None (не обновлять)
            last_error: текст ошибки или None (очистить)
        """
        if mode not in self.status:
            self.status[mode] = {"running": False, "processed": 0, "last_error": None}
        
        if running is not None:
            self.status[mode]["running"] = running
        
        if processed is not None:
            self.status[mode]["processed"] = processed
        
        if last_error is not None:
            self.status[mode]["last_error"] = last_error
        elif last_error == "":  # Явная очистка ошибки
            self.status[mode]["last_error"] = None
        
        self.status["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_status()
    
    def increment_processed(self, mode: str, count: int = 1):
        """Увеличивает счётчик обработанных"""
        if mode in self.status:
            self.status[mode]["processed"] = self.status[mode].get("processed", 0) + count
            self.status["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_status()
    
    # =============================================================================
    # УПРАВЛЕНИЕ ОСТАНОВКОЙ РЕЖИМОВ
    # =============================================================================
    
    def request_stop(self, mode: str):
        """
        Запрашивает остановку режима через флаг stop_requested
        Используется для остановки режимов извне (например из GUI)
        
        Args:
            mode: "comments", "calls", "writeoffs", "online_stats" и т.д.
        """
        if mode not in self.status:
            print(f"⚠️ Неизвестный режим: {mode}")
            return
        
        self.status[mode]["stop_requested"] = True
        self.status["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_status()
        print(f"🛑 Запрошена остановка режима: {mode}")
    
    def check_stop_requested(self, mode: str) -> bool:
        """
        Проверяет, запрошена ли остановка режима
        Вызывается внутри цикла режима
        
        Args:
            mode: "comments", "calls", "writeoffs", "online_stats" и т.д.
            
        Returns:
            True если запрошена остановка, False иначе
        """
        if mode in self.status:
            return self.status[mode].get("stop_requested", False)
        return False
    
    def clear_stop_request(self, mode: str):
        """
        Очищает флаг остановки после завершения режима
        
        Args:
            mode: "comments", "calls", "writeoffs", "online_stats" и т.д.
        """
        if mode in self.status:
            self.status[mode]["stop_requested"] = False
            self.status["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_status()
    
    # =============================================================================
    # СОХРАНЕНИЕ И ПОЛУЧЕНИЕ СТАТУСА
    # =============================================================================
    
    def save_status(self):
        """Сохраняет статус в JSON файл"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения статуса: {e}")
    
    def get_status(self):
        """Возвращает текущий статус"""
        return self.status.copy()
    
    # =============================================================================
    # УПРАВЛЕНИЕ КОМАНДАМИ (из Telegram)
    # =============================================================================
    
    def register_command_callback(self, command: str, callback: Callable):
        """
        Регистрирует callback для команды
        
        Args:
            command: "start_comments", "stop_comments", etc.
            callback: функция которая будет вызвана
        """
        self.command_callbacks[command] = callback
    
    def start_command_checker(self, interval: float = 2.0):
        """
        Запускает поток который проверяет bot_commands.json каждые N секунд
        
        Args:
            interval: интервал проверки в секундах (по умолчанию 2)
        """
        if self.command_checker_running:
            return
        
        self.command_checker_running = True
        self.command_checker_thread = threading.Thread(
            target=self._command_checker_loop,
            args=(interval,),
            daemon=True
        )
        self.command_checker_thread.start()
        print(f"✅ Command checker запущен (интервал: {interval}с)")
    
    def stop_command_checker(self):
        """Останавливает поток проверки команд"""
        self.command_checker_running = False
        if self.command_checker_thread:
            self.command_checker_thread.join(timeout=5)
        print("🛑 Command checker остановлен")
    
    def _command_checker_loop(self, interval: float):
        """Основной цикл проверки команд"""
        while self.command_checker_running:
            try:
                self._check_and_execute_command()
            except Exception as e:
                print(f"Ошибка в command_checker: {e}")
            
            time.sleep(interval)
    
    def _check_and_execute_command(self):
        """Проверяет и выполняет команду из bot_commands.json"""
        if not os.path.exists(self.commands_file):
            return
        
        try:
            with open(self.commands_file, 'r', encoding='utf-8') as f:
                command_data = json.load(f)
            
            command = command_data.get("command")
            executed = command_data.get("executed", False)
            
            # Если есть команда и она не выполнена
            if command and not executed:
                print(f"📨 Получена команда из TG: {command}")
                
                # Ищем callback для этой команды
                if command in self.command_callbacks:
                    try:
                        self.command_callbacks[command]()
                        print(f"✅ Команда {command} выполнена")
                    except Exception as e:
                        print(f"❌ Ошибка выполнения команды {command}: {e}")
                else:
                    print(f"⚠️ Не найден обработчик для команды: {command}")
                
                # Помечаем как выполненную
                command_data["executed"] = True
                with open(self.commands_file, 'w', encoding='utf-8') as f:
                    json.dump(command_data, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            print(f"Ошибка чтения команд: {e}")
    
    # =============================================================================
    # ЛОГИРОВАНИЕ
    # =============================================================================
    
    def add_log(self, message: str):
        """Добавляет сообщение в лог-файл"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"
        
        try:
            with open(self.logs_file, 'a', encoding='utf-8') as f:
                f.write(log_line)
        except Exception as e:
            print(f"Ошибка записи лога: {e}")
    
    def clear_logs(self):
        """Очищает файл логов"""
        try:
            with open(self.logs_file, 'w', encoding='utf-8') as f:
                f.write("")
        except:
            pass


# Глобальный экземпляр
_status_manager = None

def get_status_manager() -> StatusManager:
    """Получить глобальный менеджер статуса"""
    global _status_manager
    if _status_manager is None:
        _status_manager = StatusManager()
    return _status_manager