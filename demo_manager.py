# -*- coding: utf-8 -*-
"""
🎮 Demo Manager - управление демо-режимом (АВТОМАТИЧЕСКАЯ ПОДПИСЬ)
• Демо на 7 дней, только 1 раз на компьютер
• RSA подпись создается АВТОМАТИЧЕСКИ при активации
• Приватный ключ встроен в программу для удобства
• Запись в реестр Windows для защиты от удаления файла
• Проверка подписи при каждом чтении demo.key
• Файлы ищутся РЯДОМ с EXE, а не в текущей папке
"""

import os
import json
import sys
import winreg
from datetime import datetime, timedelta
from hwid_generator import get_hwid

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️ cryptography не установлена, демо-режим работает без защиты!")


class DemoManager:
    """Управление защищённым демо-режимом с автоматической RSA подписью"""
    
    # Реестр Windows для хранения информации о демо
    REGISTRY_PATH = r"Software\MaxCreditBot\Demo"
    
    # ПУБЛИЧНЫЙ КЛЮЧ (для проверки подписи)
    # Такой же как в license_checker_offline.py
    PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtBIKKsmeI/io0b9a5FD0
1tlHd8hv9GiiF8fvUK4Glqy7Ikc2EvwhfNV6ZOS4bQqc/wYpF5aUip1U5QnA4ifp
wC5qbSsZBCzqyNAnoR9sAPfQvzTpO7NAiLAEM7QMWRgJEc9ooi/sDuhj/329NraK
5Sft8UTQ7/yclZ1IfQ9MZOMoiFVvnWfvFyEpkJ2E1evaLYO9/wd4wcdrjl/9b3EZ
N+lp8L4/d11GgE8mth9kpb+tATawTfDk0trdTXUncYrqljnsdYAhzxMaVnB/EF8v
1MTvi+7oRprM2H8nukBJ8XMlxApxpK2D78Q20wEKgK4kLOAzizltmrkzDk/i7N7e
qQIDAQAB
-----END PUBLIC KEY-----"""
    
    # ПРИВАТНЫЙ КЛЮЧ (для создания подписи)
    # ✅ Приватный ключ встроен для автоматической подписи demo.key
    PRIVATE_KEY_PEM = b"""-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQC0EgoqyZ4j+KjR
v1rkUPTW2Ud3yG/0aKIXx+9QrgaWrLsiRzYS/CF81Xpk5LhtCpz/BikXlpSKnVTl
CcDiJ+nALmptKxkELOrI0CehH2wA99C/NOk7s0CIsAQztAxZGAkRz2iiL+wO6GP/
fb02torlJ+3xRNDv/JyVnUh9D0xk4yiIVW+dZ+8XISmQnYTV69otg73/B3jBx2uO
X/1vcRk36Wnwvj93XUaATya2H2Slv60BNrBN8OTS2t1NdSdxiuqWOex1gCHPExpW
cH8QXy/UxO+L7uhGmszYfye6QEnxcyXECnGkrYPvxDbTAQqAriQs4DOLOW2auTMO
T+Ls3t6pAgMBAAECggEAP0h3ukHRCeNBsTUGxGaPJVKHA1m1vrdm/+SL/laqihl6
SrmsD0/8lNqRgRPAnNG2CwonNtr8qRpR04xx9QkB5UBqtqMGz6jZemltA/r/AfgV
rJzzur9sVp1FXMZR8J250kCKDTW6SCLzwb522NueRJqbzMbahvzIKuxzpT/TIUD7
qj2rQvOG92HuQroPyGtFiVmF8aX1o1lDa1eK2wcWJWHjEMrfdQo8laSV1pVwtbse
0G+IxQIfubkpLaM2sPkbF6GaXFxAA5tYjan9UwAThWkwBie3V/2z2Z5Xue2H5LsV
V1lvEOugdR+l1jhs7GejF1PfpZpQbm6g1siRt1XZ4QKBgQD1DEZe04QjKgWQq66u
AMxb/M8jDLB8u4wli0oOyuYcHE+Is2VqrpofhYocG8kEE5o4QdNen5YHToEmnTjG
r3Y+y7BOS29C0FvUHEGgCZlv08c4XcGy9m/SeQtPUupbJd1h0AHH/x40BT7T7aJE
Cc108JB4zzHdFNh+aS9Kk0DJowKBgQC8HlKVXHFsqSnC/Y9mf9Ck0akkeGMsph8Z
gEB0tIbipiNBgoyrK7YQIOc8oSXVu1zNczO7zQAGjh8sE2vm5DpqsZZ9Mp4dr1y1
MBtdU3M/uHgY/9ovW9llWdOCDz8mKsj1z2maU4u9dPfLC3J7Abg7S7TA8UVL9SB4
HpN5UXETQwKBgCO4K1XNPTim+nKxI+BHS4KpIkR4qA02hWI/oIbxeoNkeQ9zHvhj
BSJNI+me/zkx5kwHBFmJp6PfBKJtToZfszvKEyQGiOxTVN9hUwuR+qS7WRHVUNPW
akxiyoxAiNrKdS+501ikznFExni77eg/CYzfOB/0C8+vJzOd/3++YTZDAoGAaAGz
0xSbOWKFzmL2R8tfBeFNTPaqjmMCSs0X1e6BrQoB8BRHxdOTA3PNpT3Ld1Hxyz1o
WurKmtU08t+CBtQkYBzzgSDdPrhX321Lk9uxmodZDylV7l0v4tM5F21qkqWRGiak
0khiuErVPZOEpfGbdF01AH/kukw6uW7eRnL6u5UCgYBR2Ek6rSkixyw+rgFwAoVS
iAoTwKtN1ndzrunisaoiSez/4q/us1xOi84gRBKGH0weh/AgVmsFWKwfGcXaoJ+v
x4ury3kOPnIrTd9d2cxp6V+O+RkaAoCnKXR/+F/gHYGDl0V4vdwn3DaDJUZv9mwa
1bQwjCJlcmN3IQmicJKMjA==
-----END PRIVATE KEY-----"""
    
    def __init__(self, demo_file="demo.key"):
        """
        Инициализация демо-менеджера
        
        Args:
            demo_file: Имя файла для хранения подписанного демо (ищется рядом с программой!)
        """
        # Определяем папку программы (работает и для EXE, и для Python)
        if getattr(sys, 'frozen', False):
            # Скомпилированный EXE - папка где лежит exe
            app_dir = os.path.dirname(sys.executable)
        else:
            # Обычный Python скрипт - папка где лежит скрипт
            app_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Файл демо РЯДОМ с программой
        self.demo_file = os.path.join(app_dir, demo_file)
        
        print(f"🔍 Ищу demo.key в: {self.demo_file}")  # Для отладки
        
        self.demo_days = 7  # Демо на 7 дней
        self.public_key = None
        self.private_key = None
        
        # Загружаем ключи
        self.load_keys()
    
    def load_keys(self):
        """Загружает публичный и приватный ключи для подписи и проверки"""
        if not CRYPTO_AVAILABLE:
            print("⚠️ cryptography недоступна - подписи работать не будут")
            return
        
        # Загружаем публичный ключ (для проверки)
        try:
            self.public_key = serialization.load_pem_public_key(
                self.PUBLIC_KEY_PEM,
                backend=default_backend()
            )
            print("✅ Публичный ключ загружен")
        except Exception as e:
            print(f"❌ Ошибка загрузки публичного ключа: {e}")
            self.public_key = None
        
        # Загружаем приватный ключ (для создания подписи)
        try:
            self.private_key = serialization.load_pem_private_key(
                self.PRIVATE_KEY_PEM,
                password=None,
                backend=default_backend()
            )
            print("✅ Приватный ключ загружен")
        except Exception as e:
            print(f"❌ Ошибка загрузки приватного ключа: {e}")
            print("⚠️ Проверь что ты вставил содержимое private_key.pem в PRIVATE_KEY_PEM!")
            self.private_key = None
    
    def _get_registry_value(self, name, default=None):
        """Получить значение из реестра Windows"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_PATH, 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, name)
            winreg.CloseKey(key)
            return value
        except WindowsError:
            return default
    
    def _set_registry_value(self, name, value):
        """Записать значение в реестр Windows"""
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_PATH)
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, str(value))
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"⚠️ Ошибка записи в реестр: {e}")
            return False
    
    def is_demo_available(self):
        """
        Проверяет доступен ли демо-режим на этом компьютере
        
        Returns:
            bool: True если демо доступно, False если уже использовалось
        """
        current_hwid = get_hwid()
        
        # Проверяем реестр (ГЛАВНАЯ ЗАЩИТА!)
        registry_used = self._get_registry_value("used", "0")
        registry_hwid = self._get_registry_value("hwid", "")
        
        if registry_used == "1":
            # Демо уже использовалось
            if registry_hwid == current_hwid:
                return False  # На этом компе демо было
            else:
                # HWID изменился - возможно другой комп или подмена
                # Для безопасности считаем что демо недоступно
                return False
        
        # Дополнительно проверяем файл (если реестр пуст)
        if os.path.exists(self.demo_file):
            try:
                demo_info = self._read_and_verify_demo_file()
                if demo_info and demo_info.get('hwid') == current_hwid:
                    # Файл есть, HWID совпадает, подпись валидна - демо использовалось
                    # Обновляем реестр
                    self._set_registry_value("used", "1")
                    self._set_registry_value("hwid", current_hwid)
                    return False
            except:
                pass
        
        return True  # Демо доступно
    
    def activate_demo(self):
        """
        Активирует демо-режим с АВТОМАТИЧЕСКОЙ RSA подписью
        Создает demo.key с подписью прямо при активации!
        
        Returns:
            dict: {"success": True/False, "message": "...", "expires": datetime}
        """
        # Проверяем доступность демо
        if not self.is_demo_available():
            return {
                "success": False,
                "message": "❌ Демо-режим уже использовался на этом компьютере!",
                "expires": None
            }
        
        current_hwid = get_hwid()
        started = datetime.now()
        expires = started + timedelta(days=self.demo_days)
        
        # Данные демо
        demo_data = {
            "hwid": current_hwid,
            "started": started.strftime("%Y-%m-%d %H:%M:%S"),
            "expires": expires.strftime("%Y-%m-%d %H:%M:%S"),
            "days": self.demo_days,
            "type": "demo"
        }
        
        # === АВТОМАТИЧЕСКАЯ ПОДПИСЬ ===
        if CRYPTO_AVAILABLE and self.private_key:
            try:
                # Создаём строку для подписи
                data_string = f"{demo_data['hwid']}|{demo_data['started']}|{demo_data['expires']}"
                
                # ПОДПИСЫВАЕМ данные приватным ключом
                signature = self.private_key.sign(
                    data_string.encode(),
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                
                # Добавляем подпись в данные
                demo_data["signature"] = signature.hex()
                
                print("✅ Demo.key подписан автоматически!")
                
            except Exception as e:
                print(f"⚠️ Не удалось создать подпись: {e}")
                print("   Demo.key будет создан БЕЗ подписи")
        else:
            print("⚠️ Приватный ключ недоступен, demo.key создается БЕЗ подписи")
        
        # Сохраняем файл (с подписью если удалось создать)
        try:
            with open(self.demo_file, 'w', encoding='utf-8') as f:
                json.dump(demo_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ Ошибка создания файла демо: {e}",
                "expires": None
            }
        
        # ВАЖНО: Записываем в реестр Windows!
        self._set_registry_value("used", "1")
        self._set_registry_value("hwid", current_hwid)
        self._set_registry_value("expires", expires.strftime("%Y-%m-%d %H:%M:%S"))
        self._set_registry_value("started", started.strftime("%Y-%m-%d %H:%M:%S"))
        
        return {
            "success": True,
            "message": f"✅ Демо-режим активирован на {self.demo_days} дней!\n"
                      f"Действует до: {expires.strftime('%d.%m.%Y %H:%M')}\n\n"
                      f"⚠️ Демо можно использовать только 1 раз на компьютер!",
            "expires": expires
        }
    
    def _read_and_verify_demo_file(self):
        """
        Читает и ПРОВЕРЯЕТ ПОДПИСЬ файла demo.key
        
        Returns:
            dict или None: Данные демо если подпись валидна, None если файла нет или подпись неверная
        """
        if not os.path.exists(self.demo_file):
            return None
        
        try:
            with open(self.demo_file, 'r', encoding='utf-8') as f:
                demo_data = json.load(f)
        except Exception as e:
            print(f"⚠️ Ошибка чтения демо-файла: {e}")
            return None
        
        # Если нет подписи - файл создан БЕЗ защиты (допускаем для обратной совместимости)
        if 'signature' not in demo_data:
            print("⚠️ Demo-файл без подписи (старая версия или ошибка)")
            return demo_data
        
        # Проверяем подпись
        if not CRYPTO_AVAILABLE or not self.public_key:
            print("⚠️ Не могу проверить подпись демо-файла (нет cryptography или ключа)")
            return demo_data
        
        # Формируем строку для проверки подписи (такую же как при создании)
        data_string = f"{demo_data.get('hwid', '')}|{demo_data.get('started', '')}|{demo_data.get('expires', '')}"
        
        try:
            signature = bytes.fromhex(demo_data['signature'])
            
            self.public_key.verify(
                signature,
                data_string.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # Подпись валидна!
            print("✅ Подпись demo-файла проверена")
            return demo_data
            
        except Exception as e:
            print(f"❌ Неверная подпись demo-файла! Файл подделан: {e}")
            return None  # Подпись неверная - не доверяем файлу
    
    def check_demo(self):
        """
        Проверяет статус демо-режима
        Использует реестр как главный источник (защита от удаления файла)
        ПРОВЕРЯЕТ ПОДПИСЬ при чтении файла!
        
        Returns:
            dict: {"valid": True/False, "message": "...", "days_left": int}
        """
        current_hwid = get_hwid()
        
        # СНАЧАЛА проверяем реестр (главная защита)
        registry_used = self._get_registry_value("used", "0")
        registry_hwid = self._get_registry_value("hwid", "")
        registry_expires = self._get_registry_value("expires", "")
        
        # Если в реестре есть информация - используем её
        if registry_used == "1" and registry_hwid and registry_expires:
            # Проверяем HWID
            if registry_hwid != current_hwid:
                return {
                    "valid": False,
                    "message": "❌ Демо активировано на другом компьютере",
                    "days_left": 0
                }
            
            # Проверяем срок
            try:
                expires = datetime.strptime(registry_expires, "%Y-%m-%d %H:%M:%S")
                
                if datetime.now() > expires:
                    return {
                        "valid": False,
                        "message": f"❌ Демо-период истёк {expires.strftime('%d.%m.%Y')}",
                        "days_left": 0
                    }
                
                # Демо активно
                days_left = (expires - datetime.now()).days + 1
                
                # ВАЖНО: Если файла demo.key нет - пересоздаем его с подписью!
                # Это нужно если пользователь обновил программу или удалил файл
                if not os.path.exists(self.demo_file):
                    print("⚠️ Файл demo.key отсутствует, пересоздаю с подписью из registry...")
                    
                    # Получаем дату начала из registry
                    registry_started = self._get_registry_value("started", "")
                    if not registry_started:
                        # Если даты начала нет - вычисляем её (expires - 7 дней)
                        started = expires - timedelta(days=self.demo_days)
                        registry_started = started.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Создаем данные для файла
                    demo_data = {
                        "hwid": current_hwid,
                        "started": registry_started,
                        "expires": registry_expires
                    }
                    
                    # Подписываем файл если есть приватный ключ
                    if CRYPTO_AVAILABLE and self.private_key:
                        try:
                            data_string = f"{current_hwid}|{registry_started}|{registry_expires}"
                            signature = self.private_key.sign(
                                data_string.encode(),
                                padding.PSS(
                                    mgf=padding.MGF1(hashes.SHA256()),
                                    salt_length=padding.PSS.MAX_LENGTH
                                ),
                                hashes.SHA256()
                            )
                            demo_data["signature"] = signature.hex()
                            print("✅ Файл demo.key пересоздан с подписью!")
                        except Exception as e:
                            print(f"⚠️ Не удалось подписать: {e}")
                    
                    # Сохраняем файл
                    try:
                        with open(self.demo_file, 'w', encoding='utf-8') as f:
                            json.dump(demo_data, f, ensure_ascii=False, indent=2)
                        print(f"✅ Файл demo.key восстановлен: {self.demo_file}")
                    except Exception as e:
                        print(f"⚠️ Не удалось создать файл: {e}")
                
                return {
                    "valid": True,
                    "message": f"✅ Демо-режим активен (осталось дней: {days_left})",
                    "days_left": days_left
                }
            except ValueError:
                pass  # Падаем к проверке файла
        
        # Если реестр пуст - проверяем файл С ПРОВЕРКОЙ ПОДПИСИ
        demo_data = self._read_and_verify_demo_file()
        
        if not demo_data:
            return {
                "valid": False,
                "message": "Демо-режим не активирован",
                "days_left": 0
            }
        
        # Проверяем HWID
        if demo_data.get('hwid') != current_hwid:
            return {
                "valid": False,
                "message": "❌ Демо активировано на другом компьютере",
                "days_left": 0
            }
        
        # Проверяем срок
        try:
            expires = datetime.strptime(demo_data['expires'], "%Y-%m-%d %H:%M:%S")
            
            if datetime.now() > expires:
                return {
                    "valid": False,
                    "message": f"❌ Демо-период истёк {expires.strftime('%d.%m.%Y')}",
                    "days_left": 0
                }
            
            # Демо активно - обновляем реестр (синхронизация)
            days_left = (expires - datetime.now()).days + 1
            
            self._set_registry_value("used", "1")
            self._set_registry_value("hwid", current_hwid)
            self._set_registry_value("expires", demo_data['expires'])
            
            return {
                "valid": True,
                "message": f"✅ Демо-режим активен (осталось дней: {days_left})",
                "days_left": days_left
            }
        
        except ValueError:
            return {
                "valid": False,
                "message": "❌ Неверный формат даты в демо-файле",
                "days_left": 0
            }


# =============================================================================
# ТЕСТИРОВАНИЕ
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🎮 ТЕСТ ЗАЩИЩЁННОГО ДЕМО-РЕЖИМА С АВТОПОДПИСЬЮ")
    print("=" * 70)
    
    manager = DemoManager()
    
    # Проверяем доступность демо
    print(f"\n1. Демо доступно: {manager.is_demo_available()}")
    
    # Проверяем текущий статус
    status = manager.check_demo()
    print(f"\n2. Текущий статус:")
    print(f"   Валидно: {status['valid']}")
    print(f"   Сообщение: {status['message']}")
    
    # Если демо доступно - можно активировать
    if manager.is_demo_available():
        print(f"\n3. Активация демо с автоматической подписью...")
        result = manager.activate_demo()
        print(f"   Успех: {result['success']}")
        print(f"   Сообщение: {result['message']}")
    
    # Проверяем реестр
    print(f"\n4. Проверка реестра:")
    print(f"   used: {manager._get_registry_value('used')}")
    print(f"   hwid: {manager._get_registry_value('hwid')}")
    print(f"   expires: {manager._get_registry_value('expires')}")
    
    print("\n" + "=" * 70)