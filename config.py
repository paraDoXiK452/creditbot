"""
🎯 Конфигурация приложения Bot Control
Все константы, XPath'ы, настройки в одном месте
"""

# === ФАЙЛЫ И ПУТИ ===
CONFIG_FILE = "bot_config.json"
COOKIES_FILE = "cookies.json"

# === URL'Ы ===
LOGIN_URL_DEFAULT = "https://www.max.credit/manager/login"
RESTORE_URL = "https://www.max.credit/auth/restore"
MAIN_PAGE_PART_BOT = "collector-debt/work"

# === XPATH - ЛОГИН ===
XPATH_USERNAME_FIELD = "//*[@id='managerloginform-phone']"
XPATH_PASSWORD_FIELD = "//*[@id='managerloginform-password']"
XPATH_LOGIN_BUTTON = "//*[@id='w0']/div[3]/button"

# === XPATH - ОСНОВНАЯ ТАБЛИЦА ===
XPATH_ALL_ROWS_TABLE = "//*[@id='w2-container']/table/tbody/tr"
XPATH_LI_NEXT_PAGINATION = "//*[@id='w2']/ul/li[contains(@class,'next')]"

# === XPATH - КОММЕНТАРИИ ===
XPATH_COMMENT_FIELD = "//*[@id='collectorcommentform-message']"
XPATH_SUBMIT_BUTTON = "//*[@id='js-collector-comment-form-submit']"
XPATH_HISTORY_ALL_ROWS = "//div[@id='w1-container']//table/tbody/tr"
XPATH_HISTORY_COMMENT_TEXT = ".//td[2]"

# Фразы для игнорирования
JUNK_COMMENT_PHRASES = [
    "звонок: время:",
    "сообщение клиенту: ссылка для оплаты",
    "заявка назначена пользователю:",
    "просрочка:",
    "заявка перенесена в свободные"
]

# === XPATH - ЗВОНКИ ===
XPATH_DATE_UNTIL_INPUT = "//*[@id='collectordebtsearch-wcallatto']"
XPATH_FZ230_ELEMENT = "//*[@id='collectordebtsearch-fz230']"
XPATH_FILTER_SEARCH_BUTTON = "//*[@id='w1']/div[4]/div[1]/button[1]"
XPATH_CALL_LIST_BUTTON = "//*[@id='w1']/div[4]/div[2]/a"

# === XPATH - МОДАЛЬНЫЕ ОКНА ===
XPATH_MODAL_CONTENT = "//div[@class='modal-content']"
XPATH_MODAL_TAB_COMMENTS = "//div[contains(@class,'modal-body')]//ul[contains(@class,'nav-tabs')]//a[text()='Комментарии']"
XPATH_MODAL_COMMENT_FIELD = "//*[@id='collectorcommentform-message']"
XPATH_MODAL_SUBMIT_BUTTON = "//*[@id='js-collector-comment-form-submit']"
XPATH_MODAL_CONTINUE_BUTTON = "//a[contains(@class,'btn') and normalize-space(text())='Продолжить']"

# === XPATH - СПИСАНИЯ ===
XPATH_WRITEOFFS_TAB = "//a[contains(@href, '#writeoff-tab')]"
XPATH_NEW_WRITEOFF_BUTTON = "//a[contains(@class, 'btn') and contains(@href, 'writeoff/create')]"
XPATH_ADD_BUTTON = "//button[@type='submit' and contains(text(), 'Добавить')]"

# === XPATH - ССЫЛКИ НА ОПЛАТУ ===
XPATH_PAYMENT_LINK_BUTTON = "/html/body/div[1]/div/div[2]/div[3]/div[1]/div[2]/div/div/div[1]/form/button"
XPATH_PAYMENT_LINK_BUTTON_ALT1 = "//button[contains(text(), 'Отправить')]"
XPATH_PAYMENT_LINK_BUTTON_ALT2 = "//button[contains(@class, 'btn') and contains(text(), 'ссылк')]"
XPATH_PAYMENT_MODAL_DIALOG = "//div[contains(@class, 'modal-dialog')]"
XPATH_PAYMENT_OK_BUTTON = "/html/body/div[6]/div/div/div[3]/div/div/button[2]"
XPATH_PAYMENT_OK_BUTTON_ALT1 = "//button[contains(text(), 'Ok')]"
XPATH_PAYMENT_OK_BUTTON_ALT2 = "//button[@class='btn btn-warning' and text()='Ok']"
XPATH_PAYMENT_CANCEL_BUTTON = "//button[contains(text(), 'Отмена')]"

# === XPATH - ВОССТАНОВЛЕНИЕ ПАРОЛЯ ===
XPATH_PHONE_INPUT = "/html/body/div[2]/div/form/div[1]/input"
XPATH_CAPTCHA_IMAGE = "/html/body/div[2]/div/form/div[2]/img"
XPATH_CAPTCHA_INPUT = "/html/body/div[2]/div/form/div[2]/input"
XPATH_SUBMIT_WITH_CAPTCHA = "/html/body/div[2]/div/form/div[3]/button"
XPATH_SUBMIT_NO_CAPTCHA = "/html/body/div[2]/div/form/div[2]/button"

# === НАСТРОЙКИ БРАУЗЕРА ===
BROWSER_WINDOW_SIZE = "1920,1080"
BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# === TIMEOUTS ===
DEFAULT_TIMEOUT = 20
SHORT_TIMEOUT = 10
LONG_TIMEOUT = 30
DELAY_SHORT = 2
DELAY_MEDIUM = 3
DELAY_LONG = 5

# === РЕГИОЫ РФ (для парсинга адресов) ===
REGIONS = [
    "московск", "ленинградск", "свердловск", "новосибирск",
    "ростовск", "нижегородск", "самарск", "омск", "челябинск",
    "волгоградск", "воронежск", "саратовск", "краснодарск", "красноярск",
    "пермск", "тюменск", "иркутск", "томск", "кемеровск",
    "архангельск", "астраханск", "белгородск", "брянск",
    "владимирск", "вологодск", "ивановск",
    "калининградск", "калужск", "кировск", "костромск",
    "курганск", "курск", "липецк", "магаданск", "мурманск",
    "новгородск", "оренбургск", "орловск", "пензенск", "псковск",
    "рязанск", "смоленск", "тамбовск", "тверск", "тульск",
    "ульяновск", "ярославск", "амурск", "сахалинск",
    "татарстан", "башкортостан", "дагестан", "бурят", "якут",
    "чуваш", "мордов", "удмурт", "марий", "коми", "карел",
    "калмык", "тыва", "хакас", "алтай", "адыг", "кабардин",
    "карачаев", "осет", "ингуш", "чечен",
    "приморск", "забайкальск", "камчатск", "ставропольск", "хабаровск"
]

# === НАСТРОЙКИ РЕЖИМОВ ===
RESTART_INTERVAL_PASSWORD_RESET = 30  # Перезапуск браузера каждые N номеров

# === КОММЕНТАРИИ ПО УМОЛЧАНИЮ ===
DEFAULT_COMMENT = "мт но"

# === GUI НАСТРОЙКИ ===
WINDOW_TITLE = "🤖 Bot Control App v2.0"
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 800
SIDEBAR_WIDTH = 250

# === РЕЖИМЫ РАБОТЫ ===
MODE_CONFIG = {
    "account_settings": {
        "name": "Настройки аккаунта",
        "icon": "⚙️",
        "color": "primary"
    },
    "bankruptcy": {
        "name": "Проверка банкротства",
        "icon": "💼",
        "color": "primary"
    },
    "comments": {
        "name": "Комментарии",
        "icon": "💬",
        "color": "info"
    },
    "calls": {
        "name": "Обработка звонков", 
        "icon": "📞",
        "color": "success"
    },
    "writeoffs": {
        "name": "Списания",
        "icon": "📝",
        "color": "warning"
    },
    "payment_links": {
        "name": "Ссылки на оплату",
        "icon": "💳",
        "color": "info"
    },
    "password_reset": {
        "name": "Сброс паролей",
        "icon": "🔑",
        "color": "danger"
    },
    "email_ai": {
        "name": "Email AI Agent",
        "icon": "📧",
        "color": "info"
    },
    "online_stats": {
        "name": "Онлайн статистика",
        "icon": "📊",
        "color": "success"
    },
    "background_tasks": {
        "name": "Фоновые задачи",
        "icon": "⚙️",
        "color": "dark"
    }
}

# === ЦВЕТОВАЯ СХЕМА ===
COLORS = {
    "primary": "#0d6efd",
    "success": "#198754",
    "warning": "#ffc107",
    "danger": "#dc3545",
    "info": "#0dcaf0",
    "dark": "#212529",
    "light": "#f8f9fa",
    "sidebar_gradient_start": "#0057b8",
    "sidebar_gradient_end": "#00c6ff",
    "bg_main": "#ffffff",
    "bg_secondary": "#f8f9fa",
    "text_primary": "#212529",
    "text_secondary": "#6c757d"
}