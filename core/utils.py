"""
🛠️ Вспомогательные функции
Парсинг, валидация, утилиты
"""

import re
from config import REGIONS


def extract_region_from_address(address):
    """
    Извлекает регион из полного адреса или названия суда
    
    Примеры:
        "302000 Орловская Область Орёл..." -> "Орловская"
        "АС Орловской области" -> "Орловская"
    
    Args:
        address: Полный адрес или название
        
    Returns:
        str: Название региона или пустая строка
    """
    if not address:
        return ""
    
    address_lower = address.lower().strip()
    
    # Убираем префиксы
    address_lower = address_lower.replace("ас ", "")
    address_lower = address_lower.replace("арбитражный суд ", "")
    
    # Ищем совпадение по КОРНЮ
    for region in REGIONS:
        if region in address_lower:
            # Возвращаем с правильным окончанием
            if region == "орловск":
                return "Орловская"
            elif region == "московск":
                return "Московская"
            elif region.endswith("ск"):
                return region.capitalize() + "ая"
            else:
                return region.capitalize()
    
    return ""


def normalize_phone(phone):
    """
    Нормализует номер телефона
    
    Args:
        phone: Номер в любом формате
        
    Returns:
        str: 10 цифр без кода страны (или пустая строка)
    """
    if not phone:
        return ""
    
    # Оставляем только цифры
    phone_clean = ''.join(filter(str.isdigit, str(phone)))
    
    # Убираем код страны если есть
    if phone_clean.startswith('7') and len(phone_clean) == 11:
        phone_clean = phone_clean[1:]
    elif phone_clean.startswith('8') and len(phone_clean) == 11:
        phone_clean = phone_clean[1:]
    
    # Проверяем длину
    if len(phone_clean) == 10:
        return phone_clean
    
    return ""


def is_detailed_info(text):
    """
    Проверяет, содержит ли комментарий детальную информацию
    
    Args:
        text: Текст комментария
        
    Returns:
        bool: True если найдено минимум 4 ключевых поля
    """
    keywords = [
        "фамилия:", "имя:", "отчество:", "дата рождения:",
        "телефон:", "паспорт рф:", "место_работы:",
        "должность:", "сумма_дохода:"
    ]
    
    text_lower = text.lower()
    found_count = sum(1 for kw in keywords if kw in text_lower)
    
    return found_count >= 4


def is_fio_and_dob(text):
    """
    Проверяет наличие ФИО + даты рождения
    
    Args:
        text: Текст комментария
        
    Returns:
        bool: True если найдено ФИО и дата рождения
    """
    # Паттерн: ФИО (2-3 слова кириллицей) + дата в формате ДД.ММ.ГГГГ
    pattern = r"([А-ЯЁа-яё]{2,}\s+[А-ЯЁа-яё]{2,}(\s+[А-ЯЁа-яё]{2,})?)\s+(\d{2}\.\d{2}\.\d{4})"
    match = re.search(pattern, text, re.IGNORECASE)
    return bool(match)


def is_junk_comment(text, junk_phrases):
    """
    Проверяет, является ли комментарий "мусорным"
    
    Args:
        text: Текст комментария
        junk_phrases: Список фраз для игнорирования
        
    Returns:
        bool: True если комментарий мусорный
    """
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in junk_phrases)


def format_duration(seconds):
    """
    Форматирует длительность в человекочитаемый вид
    
    Args:
        seconds: Количество секунд
        
    Returns:
        str: Форматированная строка (например "2ч 15м 30с")
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}ч")
    if minutes > 0:
        parts.append(f"{minutes}м")
    if secs > 0 or not parts:
        parts.append(f"{secs}с")
    
    return " ".join(parts)


def truncate_text(text, max_length=100, suffix="..."):
    """
    Обрезает текст до указанной длины
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
        suffix: Суффикс для обрезанного текста
        
    Returns:
        str: Обрезанный текст
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def validate_excel_phone_column(sheet, required_keywords=None):
    """
    Находит столбец с телефонами в Excel
    
    Args:
        sheet: Активный лист openpyxl
        required_keywords: Список ключевых слов для поиска
        
    Returns:
        int or None: Индекс столбца (1-indexed) или None
    """
    if required_keywords is None:
        required_keywords = ["телефон", "phone", "номер"]
    
    for col_idx, cell in enumerate(sheet[1], start=1):
        if cell.value:
            cell_lower = str(cell.value).lower()
            if any(kw in cell_lower for kw in required_keywords):
                return col_idx
    
    return None


def generate_random_delay(min_delay, max_delay):
    """
    Генерирует случайную задержку
    
    Args:
        min_delay: Минимальная задержка в секундах
        max_delay: Максимальная задержка в секундах
        
    Returns:
        float: Случайная задержка
    """
    import random
    return random.uniform(min_delay, max_delay)
