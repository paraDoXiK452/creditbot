# -*- coding: utf-8 -*-
"""
📞 Автоматизация Zoiper через UI Automation
Управление VoIP звонками без ручного вмешательства
"""

import pyautogui
import pygetwindow as gw
import subprocess
import time
import os
import sys
import shutil
from pathlib import Path

# Windows API для закрепления окна поверх всех окон
try:
    import win32gui
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("⚠️ pywin32 не установлен. Функция 'поверх всех окон' недоступна.")


def resource_path(relative_path):
    """
    Получить абсолютный путь к ресурсу.
    Работает и в dev-режиме, и в скомпилированном EXE.
    
    В PyInstaller ресурсы распаковываются во временную папку sys._MEIPASS
    """
    try:
        # PyInstaller создаёт временную папку и сохраняет путь в _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # В dev-режиме используем текущую директорию
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


class ZoiperAutomation:
    """Класс для автоматизации Zoiper через PyAutoGUI"""
    
    def __init__(self, zoiper_path=None, assets_path="zoiper_assets"):
        """
        Инициализация
        
        Args:
            zoiper_path: Путь к Zoiper5.exe (если None - ищет в стандартных местах)
            assets_path: Папка с картинками кнопок
        """
        self.zoiper_path = zoiper_path or self._find_zoiper()
        
        # КРИТИЧНО: Используем resource_path для правильной работы в EXE
        self.assets_path = Path(resource_path(assets_path))
        
        print(f"🔍 Инициализация ZoiperAutomation")
        print(f"📂 Путь к assets: {self.assets_path}")
        print(f"📂 Assets существует: {self.assets_path.exists()}")
        
        self.window = None
        
        # Настройки PyAutoGUI
        pyautogui.FAILSAFE = True  # Аварийная остановка - курсор в угол экрана
        pyautogui.PAUSE = 0.5      # Пауза между действиями
        
        # Пути к картинкам кнопок
        self.btn_continue = self.assets_path / "zoiper_continue.png"
        self.btn_grid = self.assets_path / "zoiper_grid.png"
        self.btn_dial = self.assets_path / "zoiper_dial.png"
        self.btn_hangup = self.assets_path / "zoiper_hangup.png"
        self.btn_mute = self.assets_path / "zoiper_mute.png"
        
        # ДИАГНОСТИКА: Проверяем все файлы
        required_files = [
            ("Continue button", self.btn_continue),
            ("Grid button", self.btn_grid),
            ("Dial button", self.btn_dial),
            ("Hangup button", self.btn_hangup),
            ("Mute button", self.btn_mute)
        ]
        
        missing_files = []
        for name, filepath in required_files:
            if filepath.exists():
                print(f"   ✅ {name}: {filepath.name}")
            else:
                print(f"   ❌ {name}: {filepath.name} НЕ НАЙДЕН!")
                missing_files.append(filepath.name)
        
        if missing_files:
            print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: Не найдено файлов: {len(missing_files)}")
            print(f"📂 Содержимое папки {self.assets_path}:")
            if self.assets_path.exists():
                items = list(self.assets_path.iterdir())
                if items:
                    for item in items:
                        print(f"   - {item.name}")
                else:
                    print(f"   (пусто)")
            else:
                print(f"   ❌ Папка вообще не существует!")
            
            raise FileNotFoundError(f"Отсутствуют файлы ресурсов: {', '.join(missing_files)}")
        
        print(f"✅ Все ресурсы на месте ({len(required_files)} файлов)\n")
        
        # Временная папка для workaround кириллицы в OpenCV
        self.temp_dir = Path(os.getenv('TEMP')) / 'zoiper_temp_images'
        self.temp_dir.mkdir(exist_ok=True)
        print(f"📁 Временная папка: {self.temp_dir}")
    
    def _locate_button_safe(self, image_path, confidence=None):
        """
        WORKAROUND для OpenCV + кириллица в пути
        
        OpenCV не умеет читать файлы из путей с русскими буквами в скомпилированных EXE.
        Копируем картинку во временную папку (без кириллицы) и ищем оттуда.
        
        Args:
            image_path: Path объект с путём к картинке
            confidence: Уровень совпадения (0.0-1.0) или None для точного поиска
        
        Returns:
            Box object или None
        """
        try:
            # Создаём временную копию с ASCII именем
            temp_filename = f"btn_{image_path.stem}.png"
            temp_path = self.temp_dir / temp_filename
            
            # Копируем файл (если ещё не скопирован или устарел)
            if not temp_path.exists() or temp_path.stat().st_mtime < image_path.stat().st_mtime:
                shutil.copy2(str(image_path), str(temp_path))
            
            # Ищем через временный файл
            if confidence is not None:
                result = pyautogui.locateOnScreen(str(temp_path), confidence=confidence)
            else:
                result = pyautogui.locateOnScreen(str(temp_path))
            
            return result
            
        except Exception as e:
            print(f"⚠️ Ошибка поиска кнопки {image_path.name}: {e}")
            return None
    
    def _find_zoiper(self):
        """Поиск Zoiper в стандартных местах"""
        possible_paths = [
            r"C:\Program Files (x86)\Zoiper5\Zoiper5.exe",
            r"C:\Program Files\Zoiper5\Zoiper5.exe",
            r"C:\Users\{}\AppData\Local\Zoiper5\Zoiper5.exe".format(os.getenv('USERNAME'))
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def is_zoiper_running(self):
        """Проверка запущен ли Zoiper через процессы"""
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                if 'zoiper' in proc.info['name'].lower():
                    return True
            return False
        except:
            # Если psutil нет - проверяем окна
            try:
                windows = gw.getWindowsWithTitle("Zoiper")
                return len(windows) > 0
            except:
                return False
    
    def start_zoiper(self, wait_time=5):
        """
        Запуск Zoiper и прохождение начального экрана
        
        Args:
            wait_time: Время ожидания загрузки (секунды)
        
        Returns:
            bool: True если успешно запущен
        """
        if self.is_zoiper_running():
            print("✅ Zoiper уже запущен")
            self.window = gw.getWindowsWithTitle("Zoiper")[0]
            self.activate_window()  # Выводим окно на передний план
            self.pin_window_topmost()  # Закрепляем поверх всех окон
            return True
        
        if not self.zoiper_path:
            print("❌ Zoiper не найден. Укажите путь вручную.")
            return False
        
        print(f"🚀 Запуск Zoiper: {self.zoiper_path}")
        try:
            # ДИАГНОСТИКА 1: Проверяем файл кнопки
            print(f"📂 Путь к assets: {self.assets_path}")
            print(f"📂 Файл кнопки: {self.btn_continue}")
            print(f"📂 Файл существует: {self.btn_continue.exists()}")
            
            if not self.btn_continue.exists():
                print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Файл {self.btn_continue} не найден!")
                print(f"📂 Содержимое папки assets:")
                if self.assets_path.exists():
                    for item in self.assets_path.iterdir():
                        print(f"   - {item.name}")
                else:
                    print(f"   ❌ Папка {self.assets_path} вообще не существует!")
                return False
            
            subprocess.Popen([self.zoiper_path])
            time.sleep(wait_time)
            
            # Ищем кнопку "Continue as a Free user"
            print("🔍 Поиск кнопки 'Continue as a Free user'...")
            
            # ДИАГНОСТИКА 2: Проверяем opencv
            try:
                import cv2
                print(f"✅ OpenCV версия: {cv2.__version__}")
            except ImportError as e:
                print(f"⚠️ OpenCV не найден: {e}")
            
            # Используем безопасный поиск (workaround для кириллицы в скомпилированном EXE)
            button = self._locate_button_safe(self.btn_continue, confidence=0.8)
            
            if button:
                print("✅ Кнопка найдена, кликаем...")
                pyautogui.click(button)
                time.sleep(3)
                
                # Получаем окно Zoiper
                self.window = gw.getWindowsWithTitle("Zoiper")[0]
                self.activate_window()  # Выводим окно на передний план
                self.pin_window_topmost()  # Закрепляем поверх всех окон
                print("✅ Zoiper готов к работе")
                return True
            else:
                print("⚠️ Кнопка 'Continue' не найдена. Возможно Zoiper уже настроен.")
                windows = gw.getWindowsWithTitle("Zoiper")
                if windows:
                    self.window = windows[0]
                    self.activate_window()  # Выводим окно на передний план
                    self.pin_window_topmost()  # Закрепляем поверх всех окон
                    return True
                else:
                    print("❌ Окно Zoiper не найдено")
                    return False
                
        except Exception as e:
            print(f"❌ Ошибка запуска Zoiper: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def activate_window(self, aggressive=False):
        """
        Активация окна Zoiper (вывод на передний план)
        
        Args:
            aggressive: Если True - пробует 3 раза с паузами
        """
        if not self.window:
            windows = gw.getWindowsWithTitle("Zoiper")
            if windows:
                self.window = windows[0]
        
        if self.window:
            attempts = 3 if aggressive else 1
            for i in range(attempts):
                try:
                    self.window.activate()
                    time.sleep(0.3)
                    
                    # Проверяем что окно действительно активно
                    if self.window.isActive:
                        return True
                    
                    if aggressive and i < attempts - 1:
                        print(f"⚠️ Окно не активировалось, попытка {i+2}/{attempts}...")
                        time.sleep(0.5)
                except:
                    if aggressive and i < attempts - 1:
                        time.sleep(0.5)
                    pass
        return False
    
    def pin_window_topmost(self):
        """
        Закрепить окно Zoiper поверх всех окон (не сворачивается при клике)
        
        Returns:
            bool: True если успешно закреплено
        """
        if not WIN32_AVAILABLE:
            print("⚠️ pywin32 не установлен, закрепление недоступно")
            return False
        
        if not self.window:
            windows = gw.getWindowsWithTitle("Zoiper")
            if windows:
                self.window = windows[0]
        
        if self.window:
            try:
                hwnd = self.window._hWnd
                win32gui.SetWindowPos(
                    hwnd, 
                    win32con.HWND_TOPMOST,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
                )
                print("📌 Zoiper закреплён поверх всех окон")
                return True
            except Exception as e:
                print(f"⚠️ Не удалось закрепить окно: {e}")
                return False
        return False
    
    def unpin_window_topmost(self):
        """
        Открепить окно Zoiper от режима "поверх всех окон"
        
        Returns:
            bool: True если успешно откреплено
        """
        if not WIN32_AVAILABLE:
            return False
        
        if not self.window:
            windows = gw.getWindowsWithTitle("Zoiper")
            if windows:
                self.window = windows[0]
        
        if self.window:
            try:
                hwnd = self.window._hWnd
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_NOTOPMOST,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
                )
                print("📍 Zoiper откреплён (можно сворачивать)")
                return True
            except Exception as e:
                print(f"⚠️ Не удалось открепить окно: {e}")
                return False
        return False
    
    def is_call_active(self):
        """
        Проверка активен ли звонок (ищем красную кнопку отбоя)
        
        Returns:
            bool: True если звонок идет, False если слетел
        """
        try:
            # Активируем окно для надежности
            self.activate_window()
            time.sleep(0.3)
            
            # Ищем красную кнопку отбоя
            hangup_btn = self._locate_button_safe(self.btn_hangup, confidence=0.7)
            
            if hangup_btn:
                print("✅ Звонок активен (найдена кнопка отбоя)")
                return True
            else:
                print("❌ Звонок слетел (кнопка отбоя не найдена)")
                return False
        except Exception as e:
            print(f"⚠️ Ошибка проверки звонка: {e}")
            return False
    
    def restore_call(self):
        """
        Восстановление звонка на *88 если он слетел
        С защитой от случайного сворачивания окна + закрепление поверх всех окон
        
        Returns:
            bool: True если звонок восстановлен или уже был активен
        """
        print("🔄 Проверка и восстановление звонка...")
        
        # Закрепляем окно поверх всех окон на время операций
        self.pin_window_topmost()
        
        try:
            # Проверяем активен ли звонок
            if self.is_call_active():
                print("✅ Звонок уже активен, восстановление не требуется")
                return True
            
            # Звонок слетел - перезваниваем
            print("🔄 Звонок слетел, перезваниваем на *88...")
            
            # Агрессивно активируем окно перед набором (3 попытки)
            if not self.activate_window(aggressive=True):
                print("⚠️ Не удалось активировать окно Zoiper")
            time.sleep(0.5)
            
            if not self.dial_number("*88"):
                print("❌ Не удалось набрать *88")
                return False
            
            # Включаем мут через 2 секунды
            time.sleep(2)
            
            # Снова агрессивно активируем окно перед мутом
            if not self.activate_window(aggressive=True):
                print("⚠️ Не удалось активировать окно для мута")
            time.sleep(0.5)
            
            self.mute_call()
            print("✅ Звонок восстановлен (*88 на муте)")
            
            return True
            
        finally:
            # Всегда открепляем окно после завершения операций
            self.unpin_window_topmost()
    
    def open_dialpad(self):
        """
        Открыть циферблат (нажать на 9 точек)
        
        Returns:
            bool: True если успешно открыт
        """
        print("🔍 Открываем циферблат...")
        
        # Активируем окно
        self.activate_window()
        
        # Ищем иконку сетки (9 точек)
        grid_button = self._locate_button_safe(self.btn_grid, confidence=0.7)
        
        if grid_button:
            print("✅ Циферблат найден, кликаем...")
            pyautogui.click(grid_button)
            time.sleep(1)
            return True
        else:
            print("⚠️ Иконка циферблата не найдена")
            return False
    
    def dial_number(self, number):
        """
        Набрать номер и нажать Enter (упрощённая версия)
        
        Args:
            number: Номер для набора (строка, например "*88")
        
        Returns:
            bool: True если успешно набран
        """
        print(f"📞 Набираем номер: {number}")
        
        # Активируем окно Zoiper
        self.activate_window()
        time.sleep(0.5)
        
        # Кликаем в поле поиска вверху (примерно 120px от левого края, 80px от верха)
        if self.window:
            x = self.window.left + 120
            y = self.window.top + 80
            pyautogui.click(x, y)
            time.sleep(0.3)
            
            # Очищаем поле (на всякий случай)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
        
        # Набираем номер
        pyautogui.write(number, interval=0.1)
        time.sleep(0.3)
        
        # Жмём Enter
        print("✅ Нажимаем Enter для звонка...")
        pyautogui.press('enter')
        time.sleep(1)
        
        return True
    
    def mute_call(self):
        """
        Нажать кнопку Mute (отключить микрофон)
        
        Returns:
            bool: True если успешно нажата
        """
        print("🔇 Нажимаем Mute...")
        
        self.activate_window()
        time.sleep(0.5)
        
        try:
            mute_button = self._locate_button_safe(self.btn_mute, confidence=0.7)
            
            if mute_button:
                # Получаем центр кнопки
                center_x = mute_button.left + mute_button.width // 2
                center_y = mute_button.top + mute_button.height // 2
                
                print(f"✅ Mute найдена, кликаем по координатам ({center_x}, {center_y})")
                
                # Один клик
                pyautogui.click(center_x, center_y)
                time.sleep(0.5)
                
                print("✅ Mute нажата")
                return True
            else:
                print("⚠️ Кнопка Mute не найдена (пропускаем)")
                return False
        except Exception as e:
            print(f"⚠️ Ошибка поиска Mute (пропускаем): {e}")
            return False
    
    def end_call(self):
        """
        Завершить текущий звонок (нажать кнопку завершения)
        БЕЗ закрытия Zoiper - программа остаётся открытой
        
        Returns:
            bool: True если успешно завершён звонок
        """
        print("📴 Завершение текущего звонка...")
        
        try:
            # Активируем окно Zoiper
            self.activate_window()
            time.sleep(0.5)
            
            # Ищем кнопку завершения звонка (красная трубка)
            hangup_button = self._locate_button_safe(self.btn_hangup, confidence=0.8)
            
            if hangup_button:
                print("✅ Кнопка завершения найдена, нажимаем...")
                pyautogui.click(hangup_button)
                time.sleep(1)
                print("✅ Звонок завершён (Zoiper остался открытым)")
                return True
            else:
                print("⚠️ Кнопка завершения звонка не найдена")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка завершения звонка: {e}")
            return False
    
    def hangup(self):
        """
        Завершить звонок - закрыть Zoiper полностью
        
        Returns:
            bool: True если успешно завершён
        """
        print("📴 Завершаем звонок - закрываем Zoiper...")
        
        try:
            import psutil
            # Убиваем все процессы Zoiper
            for proc in psutil.process_iter(['name']):
                if 'zoiper' in proc.info['name'].lower():
                    proc.kill()
                    print("✅ Процесс Zoiper завершён")
            
            self.window = None
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"⚠️ Ошибка при завершении: {e}")
            return False
    
    def make_call(self, number, duration=30, mute=True):
        """
        Выполнить полный цикл звонка (упрощённая версия)
        
        Args:
            number: Номер для звонка
            duration: Длительность звонка (секунды)
            mute: Включить мут после звонка
        
        Returns:
            bool: True если звонок выполнен успешно
        """
        print(f"\n{'='*60}")
        print(f"📞 Звонок на номер: {number}")
        print(f"{'='*60}")
        
        # Набираем номер и жмём Enter
        if not self.dial_number(number):
            return False
        
        # Ждём 2 секунды чтобы звонок начался
        time.sleep(2)
        
        # Включаем мут
        if mute:
            self.mute_call()
        
        # Ждём заданное время (звонок идёт)
        print(f"⏰ Звонок идёт... Ожидание {duration} секунд...")
        time.sleep(duration)
        
        # Завершаем звонок (убиваем процесс)
        success = self.hangup()
        
        print(f"{'='*60}\n")
        return success
    
    def close_zoiper(self):
        """Закрыть Zoiper"""
        if self.window:
            try:
                self.window.close()
                print("✅ Zoiper закрыт")
            except:
                print("⚠️ Не удалось закрыть Zoiper")


# =============================================================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# =============================================================================

if __name__ == "__main__":
    # Создаём автоматизатор
    zoiper = ZoiperAutomation(
        zoiper_path=r"C:\Program Files (x86)\Zoiper5\Zoiper5.exe",  # Укажи свой путь
        assets_path="zoiper_assets"  # Папка с картинками кнопок
    )
    
    # Запускаем Zoiper
    if zoiper.start_zoiper():
        
        # Список номеров для обзвона
        numbers = [
            "*88",           # Тестовый номер
            # "+79991234567",
            # "+79997654321",
        ]
        
        # Обзваниваем
        for number in numbers:
            zoiper.make_call(
                number=number,
                duration=30,  # 30 секунд на звонок
                mute=True     # Отключить микрофон
            )
            
            # Пауза между звонками
            print("⏸ Пауза 5 секунд перед следующим звонком...")
            time.sleep(5)
        
        print("\n✅ Все звонки выполнены!")
        
        # Закрываем Zoiper (опционально)
        # zoiper.close_zoiper()