# -*- coding: utf-8 -*-
"""
🔥 НАДЁЖНЫЙ АВТООБНОВЛЯТОР CREDITBOT - FIXED VERSION
✅ БЕЗ DEADLOCK - правильное разделение ответственности
✅ UpdateDownloader только скачивает и готовит BAT
✅ Главный поток останавливает приложение и запускает BAT
"""

import os
import sys
import time
import requests
import zipfile
import shutil
import subprocess
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal


# =========================
# ОЧИСТКА СТАРЫХ ВРЕМЕННЫХ ФАЙЛОВ
# =========================

def cleanup_old_temp_files():
    """
    Удаляет старые временные папки обновлений (старше 1 дня)
    """
    try:
        temp_base = Path(os.getenv("TEMP", "/tmp"))
        for folder in temp_base.glob("creditbot_update_*"):
            try:
                # Проверяем возраст папки
                folder_age = time.time() - folder.stat().st_mtime
                if folder_age > 86400:  # Старше 1 дня (24 часа)
                    shutil.rmtree(folder, ignore_errors=True)
                    print(f"[UPDATER] Удалена старая временная папка: {folder.name}")
            except Exception as e:
                print(f"[UPDATER] Не удалось удалить {folder.name}: {e}")
    except Exception as e:
        print(f"[UPDATER] Ошибка очистки временных файлов: {e}")


def stop_all_threads():
    """
    Корректно останавливает все активные QThread перед обновлением
    ⚠️ ВАЖНО: Вызывать ТОЛЬКО из главного потока!
    """
    try:
        from PyQt6.QtCore import QCoreApplication
        
        print("[UPDATER] Останавливаем все потоки...")
        
        # Получаем все активные потоки
        for thread in QThread.allThreads():
            # Пропускаем главный поток
            if thread is QThread.currentThread():
                continue
                
            thread_name = thread.objectName() or thread.__class__.__name__
            print(f"[UPDATER]   Останавливаем поток: {thread_name}")
            
            # ВАЖНО: Проверяем что это действительно QThread
            if not isinstance(thread, QThread):
                print(f"[UPDATER]   ⚠️ Поток {thread_name} не является QThread, пропускаем")
                continue
            
            # Пытаемся остановить поток корректно
            if hasattr(thread, 'stop'):
                try:
                    thread.stop()
                    print(f"[UPDATER]   Вызван метод stop() для {thread_name}")
                except Exception as e:
                    print(f"[UPDATER]   ⚠️ Ошибка при вызове stop(): {e}")
            
            # Отправляем сигнал завершения
            try:
                thread.quit()
            except Exception as e:
                print(f"[UPDATER]   ⚠️ Ошибка при вызове quit(): {e}")
            
            # Ждем завершения (максимум 3 секунды на поток)
            try:
                if not thread.wait(3000):
                    print(f"[UPDATER]   ⚠️ Поток {thread_name} не завершился за 3 сек")
                    # Пытаемся принудительно
                    thread.terminate()
                    thread.wait(1000)
                else:
                    print(f"[UPDATER]   ✓ Поток {thread_name} остановлен")
            except Exception as e:
                print(f"[UPDATER]   ⚠️ Ошибка при ожидании завершения: {e}")
        
        print("[UPDATER] Все потоки остановлены")
        return True
        
    except Exception as e:
        print(f"[UPDATER] Ошибка остановки потоков: {e}")
        return False


# =========================
# НАСТРОЙКИ
# =========================

GITHUB_REPO = "paraDoxiK452/creditbot"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

APP_NAME = "CreditBot"
EXE_PREFIX = "CreditBotV"      # CreditBotV1.3.1.exe
VERSION_FALLBACK = "0.0.0"     # ⬅️ ВАЖНО. НИКОГДА НЕ ПОДНИМАТЬ


# =========================
# ВЕРСИЯ
# =========================

def get_current_version() -> str:
    """
    Надёжно получает текущую версию.
    Если не удалось — возвращает 0.0.0 (обновление ВСЕГДА возможно)
    """
    try:
        if getattr(sys, "frozen", False):
            exe_name = Path(sys.executable).stem
            if exe_name.startswith(EXE_PREFIX):
                return exe_name.replace(EXE_PREFIX, "")
    except:
        pass

    return VERSION_FALLBACK


CURRENT_VERSION = get_current_version()


# =========================
# CHECKER
# =========================

class UpdateChecker(QThread):
    update_available = pyqtSignal(str, str)  # version, url
    no_update = pyqtSignal()
    error = pyqtSignal(str)

    def run(self):
        try:
            print(f"[UPDATER] Текущая версия: {CURRENT_VERSION}")

            r = requests.get(
                GITHUB_API_URL,
                timeout=10,
                headers={"User-Agent": "CreditBot-Updater"}
            )

            if r.status_code != 200:
                self.error.emit(f"GitHub error {r.status_code}")
                return

            data = r.json()
            latest_version = data["tag_name"].lstrip("v")

            print(f"[UPDATER] Последняя версия: {latest_version}")

            if self.is_newer(latest_version, CURRENT_VERSION):
                zip_url = None
                for asset in data.get("assets", []):
                    if asset["name"].endswith(".zip"):
                        zip_url = asset["browser_download_url"]
                        break

                if not zip_url:
                    self.error.emit("ZIP не найден в релизе")
                    return

                self.update_available.emit(latest_version, zip_url)
            else:
                self.no_update.emit()

        except Exception as e:
            self.error.emit(str(e))

    @staticmethod
    def is_newer(latest: str, current: str) -> bool:
        try:
            l = [int(x) for x in latest.split(".")]
            c = [int(x) for x in current.split(".")]
            while len(l) < 3: l.append(0)
            while len(c) < 3: c.append(0)
            return l > c
        except:
            return True  # ⬅️ если что-то пошло не так — ОБНОВЛЯЕМ


# =========================
# DOWNLOADER + BAT CREATOR
# =========================

class UpdateDownloader(QThread):
    """
    ✅ ИСПРАВЛЕНО: Теперь только скачивает и создает BAT файл
    ❌ НЕ останавливает потоки (это делает главное окно)
    ❌ НЕ запускает BAT (это делает главное окно)
    """
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)  # ← ИЗМЕНЕНО: теперь передает путь к BAT файлу
    error = pyqtSignal(str)

    def __init__(self, url: str, version: str):
        super().__init__()
        self.url = url
        self.version = version

        ts = int(time.time())
        self.temp_dir = Path(os.getenv("TEMP", "/tmp")) / f"creditbot_update_{ts}"
        self.log_file = self.temp_dir / "update.log"

    def run(self):
        try:
            self.temp_dir.mkdir(exist_ok=True)

            zip_path = self.temp_dir / "update.zip"
            extract_dir = self.temp_dir / "extracted"

            self._log("Скачивание обновления")
            self._download(zip_path)

            self._log("Распаковка")
            extract_dir.mkdir(exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(extract_dir)

            # ✅ Создаем BAT файл и возвращаем путь к нему
            bat_path = self._create_bat_file(extract_dir)
            self._log(f"BAT файл создан: {bat_path}")
            
            # ✅ Отправляем сигнал с путем к BAT файлу
            self.finished.emit(str(bat_path))

        except Exception as e:
            self.error.emit(str(e))

    # ---------- helpers ----------

    def _download(self, path: Path):
        r = requests.get(self.url, stream=True, timeout=30)
        r.raise_for_status()

        total = int(r.headers.get("content-length", 0))
        downloaded = 0

        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        self.progress.emit(int((downloaded / total) * 100))

    def _create_bat_file(self, extract_dir: Path) -> Path:
        """
        ✅ ИСПРАВЛЕНО: Использует robocopy, ren вместо rmdir, убивает Edge
        """
        if getattr(sys, "frozen", False):
            app_dir = os.path.abspath(os.path.dirname(sys.executable))
            current_exe = os.path.basename(sys.executable)
        else:
            app_dir = os.path.abspath(os.path.dirname(__file__))
            current_exe = "CreditBotV1.4.5.exe"
        
        batch = self.temp_dir / "update.bat"
        log_path = os.path.join(app_dir, "update.log")
        extract_dir_str = str(extract_dir.resolve())
        
        # ✅ ИСПРАВЛЕННЫЙ BAT с robocopy + ren + edge killer
        content = f"""@echo off
    chcp 65001 >nul
    echo ============================================ > "{log_path}"
    echo CREDITBOT UPDATE LOG >> "{log_path}"
    echo ============================================ >> "{log_path}"
    echo [%date% %time%] Начало обновления >> "{log_path}"
    echo Текущий exe: {current_exe} >> "{log_path}"
    echo Целевой exe: CreditBotV{self.version}.exe >> "{log_path}"
    echo. >> "{log_path}"

    REM ✅ Убиваем Edge/WebView который может держать dll
    echo [%date% %time%] Убиваем Edge/WebView >> "{log_path}"
    taskkill /F /IM msedge.exe >nul 2>&1
    taskkill /F /IM msedgewebview2.exe >nul 2>&1
    timeout /t 2 /nobreak >nul

    REM Ждем завершения Python
    echo [%date% %time%] Ожидание Python (10 сек)... >> "{log_path}"
    timeout /t 10 /nobreak >nul

    REM ✅ Переименовываем старый exe (не удаляем!)
    echo [%date% %time%] Переименование старого exe >> "{log_path}"
    if exist "{app_dir}\\{current_exe}" (
        ren "{app_dir}\\{current_exe}" "{current_exe}.old" >> "{log_path}" 2>&1
        if errorlevel 1 (
            echo ERROR: Не удалось переименовать exe >> "{log_path}"
            pause
            exit /b 1
        )
        echo OK: Старый exe переименован >> "{log_path}"
    )

    REM ✅ Копируем новый exe
    echo [%date% %time%] Копирование нового exe >> "{log_path}"
    copy /Y "{extract_dir_str}\\CreditBotV{self.version}.exe" "{app_dir}\\" >> "{log_path}" 2>&1
    if errorlevel 1 (
        echo ERROR: copy exe failed >> "{log_path}"
        goto RESTORE
    )
    echo OK: exe скопирован >> "{log_path}"

    REM ✅ КРИТИЧНО: Переименовываем старую _internal (НЕ удаляем!)
    echo [%date% %time%] Переименование старой _internal >> "{log_path}"
    if exist "{app_dir}\\_internal" (
        ren "{app_dir}\\_internal" "_internal.old" >> "{log_path}" 2>&1
        if errorlevel 1 (
            echo WARNING: Не удалось переименовать _internal >> "{log_path}"
        ) else (
            echo OK: _internal переименована >> "{log_path}"
        )
    )

    REM ✅ Используем ROBOCOPY вместо xcopy
    echo [%date% %time%] Копирование _internal (robocopy) >> "{log_path}"
    if exist "{extract_dir_str}\\_internal" (
        robocopy "{extract_dir_str}\\_internal" "{app_dir}\\_internal" /E /R:2 /W:1 /NFL /NDL >> "{log_path}" 2>&1
        
        REM robocopy errorlevel: 0-7 OK, 8+ error
        if errorlevel 8 (
            echo ERROR: robocopy failed >> "{log_path}"
            goto RESTORE
        )
        echo OK: _internal скопирована >> "{log_path}"
    ) else (
        echo WARNING: _internal не найдена в архиве >> "{log_path}"
    )

    REM Удаляем старый бэкап _internal
    echo [%date% %time%] Очистка старых бэкапов >> "{log_path}"
    if exist "{app_dir}\\_internal.old" (
        rmdir /S /Q "{app_dir}\\_internal.old" >> "{log_path}" 2>&1
    )
    if exist "{app_dir}\\{current_exe}.old" (
        del /F /Q "{app_dir}\\{current_exe}.old" >> "{log_path}" 2>&1
    )

    REM Проверка успешности
    echo [%date% %time%] Проверка результата >> "{log_path}"
    if exist "{app_dir}\\CreditBotV{self.version}.exe" (
        echo ============================================ >> "{log_path}"
        echo ОБНОВЛЕНИЕ УСПЕШНО ЗАВЕРШЕНО >> "{log_path}"
        echo ============================================ >> "{log_path}"
        
        start "" "{app_dir}\\CreditBotV{self.version}.exe"
        goto CLEANUP
    ) else (
        echo ERROR: Новый exe НЕ найден! >> "{log_path}"
        goto RESTORE
    )

    :RESTORE
    echo ============================================ >> "{log_path}"
    echo ОШИБКА! Восстановление... >> "{log_path}"
    echo ============================================ >> "{log_path}"

    REM Восстанавливаем exe
    if exist "{app_dir}\\{current_exe}.old" (
        if exist "{app_dir}\\CreditBotV{self.version}.exe" (
            del /F /Q "{app_dir}\\CreditBotV{self.version}.exe"
        )
        ren "{app_dir}\\{current_exe}.old" "{current_exe}" >> "{log_path}" 2>&1
        echo Старый exe восстановлен >> "{log_path}"
    )

    REM Восстанавливаем _internal
    if exist "{app_dir}\\_internal.old" (
        if exist "{app_dir}\\_internal" (
            rmdir /S /Q "{app_dir}\\_internal"
        )
        ren "{app_dir}\\_internal.old" "_internal" >> "{log_path}" 2>&1
        echo Старая _internal восстановлена >> "{log_path}"
        
        start "" "{app_dir}\\{current_exe}"
    )

    pause
    exit /b 1

    :CLEANUP
    echo [%date% %time%] Очистка временных файлов >> "{log_path}"
    timeout /t 2 /nobreak >nul
    rmdir /S /Q "{self.temp_dir}" 2>nul
    del "%~f0"
    """

        with open(batch, "w", encoding="cp866") as f:
            f.write(content)

        self._log("BAT файл создан (robocopy + ren)")
        return batch

# =========================
# ФУНКЦИЯ ЗАПУСКА BAT
# =========================

def execute_update_bat(bat_path: str):
    """
    ✅ ИСПРАВЛЕННАЯ ФУНКЦИЯ: Запуск BAT файла обновления
    Вызывается из главного потока ПОСЛЕ остановки всех QThread
    """
    print("[UPDATER] Запуск BAT файла обновления...")
    
    try:
        # Получаем приложение PyQt
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        
        if app:
            print("[UPDATER] Останавливаем все потоки...")
            stop_all_threads()
            
            print("[UPDATER] Закрываем все окна...")
            app.closeAllWindows()
            
            # Ждем завершения закрытия окон
            time.sleep(1)
            
            print("[UPDATER] Отправляем сигнал quit()...")
            app.quit()
            
            # Задержка для полного завершения процессов
            print("[UPDATER] Ожидание завершения процессов (3 сек)...")
            time.sleep(3)
        
        print(f"[UPDATER] Запуск BAT: {bat_path}")
        
        # ✅ ИСПРАВЛЕНО: Запуск через cmd /c (работает надежнее)
        subprocess.Popen(
            f'cmd /c start "" "{bat_path}"',
            shell=True,
            cwd=os.path.dirname(bat_path)
        )
        
        print("[UPDATER] BAT запущен, завершаем Python процесс...")
        
        # Принудительное завершение (увеличена задержка)
        time.sleep(2)
        os._exit(0)  # ✅ Более жесткий выход
        
    except Exception as e:
        print(f"[UPDATER] Ошибка запуска BAT: {e}")
        import traceback
        traceback.print_exc()

# =========================
# СИНХРОННАЯ ПРОВЕРКА
# =========================

def check_for_updates_sync():
    """
    Синхронная проверка обновлений (без QThread)
    """
    try:
        r = requests.get(GITHUB_API_URL, timeout=10,
                         headers={"User-Agent": "CreditBot-Updater"})
        if r.status_code != 200:
            return {"available": False}

        data = r.json()
        latest = data["tag_name"].lstrip("v")

        if UpdateChecker.is_newer(latest, CURRENT_VERSION):
            for asset in data.get("assets", []):
                if asset["name"].endswith(".zip"):
                    return {
                        "available": True,
                        "version": latest,
                        "url": asset["browser_download_url"]
                    }

        return {"available": False}
    except:
        return {"available": False, "error": True}


# =========================
# ИНИЦИАЛИЗАЦИЯ
# =========================

# Очищаем старые временные файлы при импорте модуля
cleanup_old_temp_files()