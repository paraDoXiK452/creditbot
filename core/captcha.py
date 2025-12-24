"""
🔍 Модуль распознавания капчи
EasyOCR + PIL для обработки изображений
"""

import easyocr
import numpy as np
from io import BytesIO
from PIL import Image, ImageEnhance


class CaptchaSolver:
    """Распознаватель капчи Max.Credit"""
    
    def __init__(self):
        self.reader = None
    
    def _init_reader(self):
        """Ленивая инициализация EasyOCR"""
        if self.reader is None:
            print("📚 Инициализация EasyOCR...")
            self.reader = easyocr.Reader(['en'], gpu=False)
            print("✅ EasyOCR готов")
    
    def solve(self, captcha_element, logger_func=print):
        """
        Распознать капчу Max.Credit
        
        Args:
            captcha_element: Selenium WebElement с изображением капчи
            logger_func: Функция для логирования
            
        Returns:
            str or None: Распознанный текст капчи (6 цифр) или None
        """
        try:
            self._init_reader()
            
            # Скриншот капчи
            captcha_png = captcha_element.screenshot_as_png
            img = Image.open(BytesIO(captcha_png)).convert('RGB')
            
            # Увеличиваем в 3 раза для лучшего распознавания
            img = img.resize(
                (img.width * 3, img.height * 3), 
                Image.LANCZOS
            )
            
            # Улучшаем контраст и резкость
            img = ImageEnhance.Contrast(img).enhance(3.0)
            img = ImageEnhance.Sharpness(img).enhance(2.0)
            
            # Распознавание (только цифры)
            result = self.reader.readtext(
                np.array(img),
                allowlist='0123456789',
                detail=0,
                paragraph=False
            )
            
            if result:
                captcha_text = ''.join(result)
                # Фильтруем только цифры
                captcha_text = ''.join(filter(str.isdigit, captcha_text))
                
                if len(captcha_text) == 6:
                    logger_func(f"✅ Капча распознана: {captcha_text}")
                    return captcha_text
                else:
                    logger_func(
                        f"⚠️ Распознано {len(captcha_text)} цифр "
                        f"вместо 6: {captcha_text}"
                    )
                    return None
            else:
                logger_func("❌ Капча не распознана")
                return None
                
        except Exception as e:
            logger_func(f"❌ Ошибка распознавания капчи: {e}")
            return None
    
    def solve_with_retries(self, captcha_element, max_retries=3, logger_func=print):
        """
        Распознать капчу с повторными попытками
        
        Args:
            captcha_element: Selenium WebElement
            max_retries: Максимальное количество попыток
            logger_func: Функция логирования
            
        Returns:
            str or None: Распознанный текст или None
        """
        for attempt in range(1, max_retries + 1):
            logger_func(f"🔄 Попытка распознавания {attempt}/{max_retries}")
            result = self.solve(captcha_element, logger_func)
            
            if result:
                return result
            
            if attempt < max_retries:
                logger_func("⏳ Пауза перед следующей попыткой...")
                import time
                time.sleep(2)
        
        logger_func(f"❌ Не удалось распознать капчу за {max_retries} попыток")
        return None


# Глобальный экземпляр для переиспользования
_global_solver = None

def get_captcha_solver():
    """Получить глобальный экземпляр CaptchaSolver"""
    global _global_solver
    if _global_solver is None:
        _global_solver = CaptchaSolver()
    return _global_solver
