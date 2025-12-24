# -*- coding: utf-8 -*-
"""
🔐 HWID Generator - генерация уникального ID компьютера
Использует процессор + UUID материнки для создания уникального отпечатка
ПОДДЕРЖКА: Windows, macOS, Linux
"""

import hashlib
import platform
import subprocess
import uuid


def get_hwid():
    """
    Генерирует уникальный HWID компьютера
    
    Использует:
    - UUID материнской платы (самый стабильный)
    - ID процессора
    - Имя компьютера (дополнительно)
    
    Returns:
        str: HWID в формате "A3F2E1D4C5B6A7F8"
    """
    components = []
    
    # 1. UUID материнской платы (самое стабильное)
    try:
        if platform.system() == "Windows":
            # Windows: wmic csproduct get UUID
            result = subprocess.check_output(
                'wmic csproduct get UUID', 
                shell=True, 
                stderr=subprocess.DEVNULL
            ).decode()
            uuid_line = result.strip().split('\n')[-1].strip()
            if uuid_line and uuid_line != "UUID":
                components.append(uuid_line)
        
        elif platform.system() == "Darwin":  # macOS
            # macOS: system_profiler для Hardware UUID
            result = subprocess.check_output(
                ['system_profiler', 'SPHardwareDataType'],
                stderr=subprocess.DEVNULL
            ).decode()
            
            # Ищем Hardware UUID
            for line in result.split('\n'):
                if 'Hardware UUID' in line:
                    hw_uuid = line.split(':')[1].strip()
                    components.append(hw_uuid)
                    break
            
            # Ищем Serial Number как дополнительный компонент
            for line in result.split('\n'):
                if 'Serial Number' in line:
                    serial = line.split(':')[1].strip()
                    if serial and serial != "(system)":
                        components.append(serial)
                    break
        
        else:  # Linux
            # Пробуем /etc/machine-id
            try:
                with open('/etc/machine-id', 'r') as f:
                    machine_id = f.read().strip()
                    if machine_id:
                        components.append(machine_id)
            except:
                # Fallback: используем MAC адрес
                components.append(str(uuid.getnode()))
    except:
        pass
    
    # 2. ID процессора
    try:
        if platform.system() == "Windows":
            result = subprocess.check_output(
                'wmic cpu get ProcessorId', 
                shell=True,
                stderr=subprocess.DEVNULL
            ).decode()
            cpu_id = result.strip().split('\n')[-1].strip()
            if cpu_id and cpu_id != "ProcessorId":
                components.append(cpu_id)
        
        elif platform.system() == "Darwin":  # macOS
            # macOS: используем Processor Name как идентификатор
            result = subprocess.check_output(
                ['sysctl', '-n', 'machdep.cpu.brand_string'],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            if result:
                components.append(result)
    except:
        pass
    
    # 3. Имя компьютера (дополнительно)
    try:
        hostname = platform.node()
        if hostname:
            components.append(hostname)
    except:
        pass
    
    # Если ничего не получилось - используем MAC адрес
    if not components:
        components.append(str(uuid.getnode()))
    
    # Создаём хеш из всех компонентов
    combined = "|".join(components)
    hwid_hash = hashlib.sha256(combined.encode()).hexdigest()
    
    # Берём первые 16 символов и переводим в верхний регистр
    hwid = hwid_hash[:16].upper()
    
    return hwid


def get_hwid_components():
    """
    Возвращает компоненты HWID для отладки
    
    Returns:
        dict: Словарь с компонентами
    """
    components = {}
    os_type = platform.system()
    components['os'] = os_type
    
    # UUID материнской платы / Hardware UUID
    try:
        if os_type == "Windows":
            result = subprocess.check_output(
                'wmic csproduct get UUID', 
                shell=True,
                stderr=subprocess.DEVNULL
            ).decode()
            uuid_line = result.strip().split('\n')[-1].strip()
            components['motherboard_uuid'] = uuid_line
        
        elif os_type == "Darwin":  # macOS
            result = subprocess.check_output(
                ['system_profiler', 'SPHardwareDataType'],
                stderr=subprocess.DEVNULL
            ).decode()
            
            # Hardware UUID
            for line in result.split('\n'):
                if 'Hardware UUID' in line:
                    hw_uuid = line.split(':')[1].strip()
                    components['hardware_uuid'] = hw_uuid
                    break
            
            # Serial Number
            for line in result.split('\n'):
                if 'Serial Number' in line:
                    serial = line.split(':')[1].strip()
                    components['serial_number'] = serial
                    break
        
        else:  # Linux
            try:
                with open('/etc/machine-id', 'r') as f:
                    components['machine_id'] = f.read().strip()
            except:
                components['machine_id'] = "Not available"
    
    except Exception as e:
        components['motherboard_uuid'] = f"Error: {e}"
    
    # ID процессора
    try:
        if os_type == "Windows":
            result = subprocess.check_output(
                'wmic cpu get ProcessorId', 
                shell=True,
                stderr=subprocess.DEVNULL
            ).decode()
            cpu_id = result.strip().split('\n')[-1].strip()
            components['cpu_id'] = cpu_id
        
        elif os_type == "Darwin":  # macOS
            result = subprocess.check_output(
                ['sysctl', '-n', 'machdep.cpu.brand_string'],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            components['cpu_brand'] = result
    
    except Exception as e:
        components['cpu_id'] = f"Error: {e}"
    
    # Имя компьютера
    components['hostname'] = platform.node()
    
    # MAC адрес
    components['mac_address'] = hex(uuid.getnode())
    
    # Финальный HWID
    components['hwid'] = get_hwid()
    
    return components


# =============================================================================
# ТЕСТИРОВАНИЕ
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🔐 ГЕНЕРАТОР HWID КОМПЬЮТЕРА")
    print("=" * 70)
    
    hwid = get_hwid()
    
    print(f"\n✅ HWID этого компьютера: {hwid}")
    print(f"\n📋 Компоненты:")
    
    components = get_hwid_components()
    for key, value in components.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 70)
    print("💡 ИНСТРУКЦИЯ:")
    print("=" * 70)
    print("1. Запусти программу на компьютере клиента")
    print("2. Клиент присылает тебе HWID")
    print("3. Ты генеришь license.key с этим HWID")
    print("4. Отправляешь клиенту файл")
    print("5. Клиент кладёт license.key рядом с программой")
    print("6. ✅ Готово!")
    print("=" * 70)