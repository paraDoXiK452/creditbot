# -*- coding: utf-8 -*-
"""
🔧 Process Manager - глобальный менеджер процессов браузеров
Отслеживает и убивает ТОЛЬКО браузеры запущенные программой
Расположение: C:\\Users\\Самурай\\Desktop\\AutoComment\\bot_control_app\\process_manager.py
"""

import psutil
import logging

logger = logging.getLogger(__name__)


class ProcessManager:
    """Менеджер для отслеживания процессов браузеров"""
    
    def __init__(self):
        """Инициализация менеджера"""
        self.tracked_pids = set()
        logger.info("✅ ProcessManager инициализирован")
    
    def register_driver(self, driver):
        """
        Регистрирует Selenium WebDriver и все его дочерние процессы
        
        Args:
            driver: Экземпляр Selenium WebDriver (Chrome/Firefox/etc)
        """
        try:
            # Получаем PID драйвера (chromedriver.exe)
            if hasattr(driver, 'service') and hasattr(driver.service, 'process'):
                driver_pid = driver.service.process.pid
                self.tracked_pids.add(driver_pid)
                logger.info(f"📌 Зарегистрирован драйвер PID: {driver_pid}")
                
                # Находим все дочерние процессы (chrome.exe)
                try:
                    parent = psutil.Process(driver_pid)
                    children = parent.children(recursive=True)
                    
                    for child in children:
                        self.tracked_pids.add(child.pid)
                        logger.debug(f"  └─ Дочерний процесс PID: {child.pid} ({child.name()})")
                    
                    if children:
                        logger.info(f"  ✅ Найдено дочерних процессов: {len(children)}")
                
                except psutil.NoSuchProcess:
                    logger.warning(f"  ⚠️ Процесс {driver_pid} уже завершён")
                except Exception as e:
                    logger.warning(f"  ⚠️ Не удалось получить дочерние процессы: {e}")
            
            else:
                logger.warning("⚠️ Driver не содержит service.process")
        
        except Exception as e:
            logger.error(f"❌ Ошибка регистрации драйвера: {e}")
    
    def unregister_pid(self, pid):
        """
        Удаляет PID из отслеживания
        
        Args:
            pid: ID процесса для удаления
        """
        if pid in self.tracked_pids:
            self.tracked_pids.discard(pid)
            logger.debug(f"🗑️ PID {pid} удалён из отслеживания")
    
    def kill_all(self):
        """
        Убивает ВСЕ отслеживаемые процессы браузеров + их дочерние процессы
        Используется при закрытии программы
        """
        if not self.tracked_pids:
            logger.info("ℹ️ Нет процессов для завершения")
            return
        
        logger.info(f"🔪 Завершение процессов (зарегистрировано: {len(self.tracked_pids)})...")
        
        # ВАЖНО: Собираем ВСЕ процессы ПЕРЕД убийством
        # (включая дочерние процессы которые появились ПОСЛЕ регистрации)
        all_pids_to_kill = set()
        
        for pid in self.tracked_pids.copy():
            # Добавляем родительский процесс
            all_pids_to_kill.add(pid)
            
            # Ищем ТЕКУЩИЕ дочерние процессы
            try:
                parent = psutil.Process(pid)
                children = parent.children(recursive=True)
                
                for child in children:
                    all_pids_to_kill.add(child.pid)
                
                if children:
                    logger.debug(f"  ├─ PID {pid} имеет {len(children)} дочерних процессов")
            
            except psutil.NoSuchProcess:
                # Процесс уже завершён - это нормально
                pass
            except Exception as e:
                logger.debug(f"  ⚠️ Не удалось получить дочерние процессы PID {pid}: {e}")
        
        logger.info(f"  📊 Всего процессов для убийства (включая дочерние): {len(all_pids_to_kill)}")
        
        killed_count = 0
        failed_count = 0
        
        # Убиваем ВСЕ найденные процессы
        for pid in all_pids_to_kill:
            try:
                process = psutil.Process(pid)
                process_name = process.name()
                
                # Убиваем процесс
                process.kill()
                
                # Ждём завершения
                process.wait(timeout=3)
                
                logger.debug(f"  ✅ Убит процесс PID {pid} ({process_name})")
                killed_count += 1
            
            except psutil.NoSuchProcess:
                # Процесс уже завершён
                logger.debug(f"  ℹ️ PID {pid} уже не существует")
                killed_count += 1
            
            except psutil.TimeoutExpired:
                logger.warning(f"  ⚠️ PID {pid} не завершился за 3 секунды, force kill...")
                try:
                    # Пробуем убить более жёстко
                    psutil.Process(pid).kill()
                    killed_count += 1
                except:
                    failed_count += 1
            
            except Exception as e:
                logger.error(f"  ❌ Ошибка при завершении PID {pid}: {e}")
                failed_count += 1
        
        logger.info(f"✅ Завершено успешно: {killed_count}, Ошибок: {failed_count}")
        
        # Очищаем множество
        self.tracked_pids.clear()
    
    def get_tracked_count(self):
        """
        Возвращает количество отслеживаемых процессов
        
        Returns:
            int: Количество процессов
        """
        return len(self.tracked_pids)
    
    def cleanup_dead_processes(self):
        """
        Очищает список от уже завершённых процессов
        """
        dead_pids = []
        
        for pid in self.tracked_pids:
            try:
                # Проверяем существует ли процесс
                psutil.Process(pid)
            except psutil.NoSuchProcess:
                dead_pids.append(pid)
        
        for pid in dead_pids:
            self.tracked_pids.discard(pid)
        
        if dead_pids:
            logger.debug(f"🧹 Очищено мёртвых процессов: {len(dead_pids)}")


# =============================================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# =============================================================================

_process_manager_instance = None


def get_process_manager():
    """
    Возвращает глобальный экземпляр ProcessManager
    Создаёт его при первом вызове (singleton)
    
    Returns:
        ProcessManager: Глобальный менеджер процессов
    """
    global _process_manager_instance
    
    if _process_manager_instance is None:
        _process_manager_instance = ProcessManager()
    
    return _process_manager_instance


# =============================================================================
# УДОБНЫЕ ФУНКЦИИ ДЛЯ ИСПОЛЬЗОВАНИЯ В ПРОЦЕССОРАХ
# =============================================================================

def register_driver(driver):
    """
    Регистрирует WebDriver в глобальном менеджере
    
    Args:
        driver: Экземпляр Selenium WebDriver
    
    Example:
        from process_manager import register_driver
        
        driver = webdriver.Chrome(service=service)
        register_driver(driver)  # Регистрируем для автоматического убийства
    """
    manager = get_process_manager()
    manager.register_driver(driver)


def kill_all_browsers():
    """
    Убивает ВСЕ браузеры запущенные программой
    Используется при закрытии программы
    
    Example:
        from process_manager import kill_all_browsers
        
        def closeEvent(self, event):
            kill_all_browsers()  # Убиваем все браузеры
            event.accept()
    """
    manager = get_process_manager()
    manager.kill_all()


def get_browsers_count():
    """
    Возвращает количество отслеживаемых процессов браузеров
    
    Returns:
        int: Количество процессов
    """
    manager = get_process_manager()
    return manager.get_tracked_count()


def cleanup_dead_processes():
    """
    Очищает список от уже завершённых процессов
    Полезно вызывать периодически для очистки
    """
    manager = get_process_manager()
    manager.cleanup_dead_processes()


# =============================================================================
# ТЕСТИРОВАНИЕ
# =============================================================================

if __name__ == "__main__":
    # Настройка логирования для теста
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🧪 Тест ProcessManager")
    print("=" * 60)
    
    # Тест создания менеджера
    pm = get_process_manager()
    print(f"✅ Менеджер создан: {pm}")
    print(f"📊 Отслеживается процессов: {pm.get_tracked_count()}")
    
    # Тест с фейковым PID
    class FakeDriver:
        class FakeService:
            class FakeProcess:
                pid = 99999  # Несуществующий PID
            process = FakeProcess()
        service = FakeService()
    
    fake_driver = FakeDriver()
    pm.register_driver(fake_driver)
    print(f"📊 После регистрации: {pm.get_tracked_count()}")
    
    # Очистка
    pm.cleanup_dead_processes()
    print(f"📊 После очистки: {pm.get_tracked_count()}")
    
    print("=" * 60)
    print("✅ Тест завершён")