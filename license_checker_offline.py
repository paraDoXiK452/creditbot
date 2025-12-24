# -*- coding: utf-8 -*-
"""
🔐 License Checker - проверка лицензий ОФЛАЙН (ИСПРАВЛЕННЫЙ)
Проверяет license.key с RSA подписью
ИСПРАВЛЕНИЕ: Файлы ищутся РЯДОМ с EXE, а не в текущей папке!
"""

import os
import json
import sys
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from hwid_generator import get_hwid


def normalize_phone(phone):
    """
    Нормализует номер телефона для сравнения
    
    Examples:
        79123456789 -> 79123456789
        9123456789 -> 79123456789
        +79123456789 -> 79123456789
        8-912-345-67-89 -> 79123456789
    
    Args:
        phone: Номер телефона в любом формате
    
    Returns:
        str: Нормализованный номер (только цифры, начинается с 7)
    """
    if not phone:
        return ""
    
    # Убираем всё кроме цифр
    digits = ''.join(c for c in str(phone) if c.isdigit())
    
    # Если начинается с 8, заменяем на 7
    if digits.startswith('8') and len(digits) == 11:
        digits = '7' + digits[1:]
    
    # Если не начинается с 7 и длина 10 цифр, добавляем 7
    if not digits.startswith('7') and len(digits) == 10:
        digits = '7' + digits
    
    return digits


# ПУБЛИЧНЫЙ КЛЮЧ RSA (встроен в программу)
# ВАЖНО: После генерации ключей вставь сюда содержимое public_key.pem
PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtBIKKsmeI/io0b9a5FD0
1tlHd8hv9GiiF8fvUK4Glqy7Ikc2EvwhfNV6ZOS4bQqc/wYpF5aUip1U5QnA4ifp
wC5qbSsZBCzqyNAnoR9sAPfQvzTpO7NAiLAEM7QMWRgJEc9ooi/sDuhj/329NraK
5Sft8UTQ7/yclZ1IfQ9MZOMoiFVvnWfvFyEpkJ2E1evaLYO9/wd4wcdrjl/9b3EZ
N+lp8L4/d11GgE8mth9kpb+tATawTfDk0trdTXUncYrqljnsdYAhzxMaVnB/EF8v
1MTvi+7oRprM2H8nukBJ8XMlxApxpK2D78Q20wEKgK4kLOAzizltmrkzDk/i7N7e
qQIDAQAB
-----END PUBLIC KEY-----"""


class LicenseChecker:
    """Проверка лицензий"""
    
    def __init__(self, license_file="license.key"):
        """
        Инициализация проверки лицензий
        
        Args:
            license_file: Имя файла лицензии (ищется рядом с программой!)
        """
        # Определяем папку программы (работает и для EXE, и для Python)
        if getattr(sys, 'frozen', False):
            # Скомпилированный EXE - папка где лежит exe
            app_dir = os.path.dirname(sys.executable)
        else:
            # Обычный Python скрипт - папка где лежит скрипт
            app_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Файл лицензии РЯДОМ с программой
        self.license_file = os.path.join(app_dir, license_file)
        
        print(f"🔍 Ищу license.key в: {self.license_file}")  # Для отладки
        
        self.public_key = None
        self.load_public_key()
    
    def load_public_key(self):
        """Загружает публичный ключ"""
        try:
            self.public_key = serialization.load_pem_public_key(
                PUBLIC_KEY_PEM,
                backend=default_backend()
            )
        except Exception as e:
            print(f"❌ Ошибка загрузки публичного ключа: {e}")
            self.public_key = None
    
    def check_license(self, current_phone=None):
        """
        Проверяет лицензию
        
        Args:
            current_phone: Номер телефона из настроек программы (для проверки привязки)
        
        Returns:
            dict: {"valid": True/False, "message": "...", "data": {...}}
        """
        # Проверяем наличие файла
        if not os.path.exists(self.license_file):
            return {
                "valid": False,
                "message": "Файл лицензии не найден",
                "data": None
            }
        
        # Читаем файл
        try:
            with open(self.license_file, 'r', encoding='utf-8') as f:
                license_data = json.load(f)
        except Exception as e:
            return {
                "valid": False,
                "message": f"Ошибка чтения лицензии: {e}",
                "data": None
            }
        
        # Проверяем наличие всех полей
        required_fields = ['name', 'phone', 'hwid', 'expires', 'signature']
        for field in required_fields:
            if field not in license_data:
                return {
                    "valid": False,
                    "message": f"Повреждённая лицензия: нет поля '{field}'",
                    "data": None
                }
        
        # Получаем HWID текущего компьютера
        current_hwid = get_hwid()
        
        # Проверяем HWID
        if license_data['hwid'] != current_hwid:
            return {
                "valid": False,
                "message": f"Лицензия привязана к другому компьютеру!\n\n"
                          f"HWID лицензии: {license_data['hwid']}\n"
                          f"HWID этого ПК: {current_hwid}",
                "data": None
            }
        
        
        # Проверяем номер телефона (если передан)
        if current_phone:
            license_phone_normalized = normalize_phone(license_data.get('phone', ''))
            current_phone_normalized = normalize_phone(current_phone)
            
            if license_phone_normalized != current_phone_normalized:
                return {
                    "valid": False,
                    "message": f"Лицензия привязана к другому номеру телефона!\n\n"
                              f"Номер в лицензии: {license_data.get('phone', 'неизвестен')}\n"
                              f"Номер в настройках: {current_phone}\n\n"
                              f"Для работы с другим номером получите новую лицензию.",
                    "data": None
                }
        
        # Проверяем подпись
        data_string = f"{license_data['name']}|{license_data['phone']}|{license_data['hwid']}|{license_data['expires']}"
        signature = bytes.fromhex(license_data['signature'])
        
        try:
            self.public_key.verify(
                signature,
                data_string.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
        except Exception as e:
            return {
                "valid": False,
                "message": "Неверная подпись лицензии! Файл подделан или повреждён.",
                "data": None
            }
        
        # Проверяем срок действия
        if license_data['expires'] != "FOREVER":
            try:
                expires = datetime.strptime(license_data['expires'], "%Y-%m-%d %H:%M:%S")
                
                if datetime.now() > expires:
                    return {
                        "valid": False,
                        "message": f"Лицензия истекла {expires.strftime('%d.%m.%Y')}",
                        "data": license_data
                    }
                
                # Считаем дни до окончания
                days_left = (expires - datetime.now()).days
                
                return {
                    "valid": True,
                    "message": f"✅ Добро пожаловать, {license_data['name']}!\n"
                              f"Дней до окончания: {days_left}",
                    "data": license_data,
                    "days_left": days_left
                }
            
            except ValueError:
                return {
                    "valid": False,
                    "message": "Неверный формат даты в лицензии",
                    "data": None
                }
        
        # Вечная лицензия
        return {
            "valid": True,
            "message": f"✅ Добро пожаловать, {license_data['name']}!\n(Вечная лицензия)",
            "data": license_data,
            "type": "forever"
        }


# =============================================================================
# ТЕСТИРОВАНИЕ
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🔐 ТЕСТ ПРОВЕРКИ ЛИЦЕНЗИИ")
    print("=" * 70)
    
    # Показываем HWID этого компа
    current_hwid = get_hwid()
    print(f"\n🔐 HWID этого компьютера: {current_hwid}")
    
    # Проверяем лицензию
    checker = LicenseChecker()
    result = checker.check_license()
    
    print(f"\n📋 РЕЗУЛЬТАТ:")
    print(f"Валидна: {result['valid']}")
    print(f"Сообщение: {result['message']}")
    
    if result['data']:
        print(f"\n📄 ДАННЫЕ ЛИЦЕНЗИИ:")
        for key, value in result['data'].items():
            if key != 'signature':  # Не показываем подпись (длинная)
                print(f"  {key}: {value}")
    
    print("\n" + "=" * 70)