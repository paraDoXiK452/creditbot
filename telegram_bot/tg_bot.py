#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 Telegram Bot для управления MaxCreditBot
Команды управления + уведомления
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Добавляем путь к settings_manager
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from settings_manager import get_settings_manager

# Импортируем TelegramManager из корневой папки
try:
    from telegram_manager import set_telegram_bot
    TELEGRAM_MANAGER_AVAILABLE = True
    print("✅ telegram_manager импортирован")
except ImportError:
    print("⚠️ Модуль telegram_manager не найден")
    TELEGRAM_MANAGER_AVAILABLE = False
    def set_telegram_bot(bot):
        pass

# Пути к файлам состояния (работает в PyInstaller)
if getattr(sys, 'frozen', False):
    # Если запущено из .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Если запущено из Python
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SHARED_DIR = os.path.join(BASE_DIR, "shared")
STATUS_FILE = os.path.join(SHARED_DIR, "bot_status.json")
COMMANDS_FILE = os.path.join(SHARED_DIR, "bot_commands.json")

# Файлы для режимов с загрузкой
BANKRUPTCY_FILE = os.path.join(SHARED_DIR, "bankruptcy_file.xlsx")
PASSWORD_RESET_FILE = os.path.join(SHARED_DIR, "password_reset_file.xlsx")

# Создаём папку shared если её нет
os.makedirs(SHARED_DIR, exist_ok=True)


class TelegramBot:
    """Telegram бот для управления"""
    
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.app = None
        self.settings = get_settings_manager()
        self.waiting_for_file = None  # "bankruptcy" или "password_reset"
        self.waiting_state_file = os.path.join(SHARED_DIR, "bot_waiting_state.json")
        
    def get_main_keyboard(self):
        """Создаёт главное меню с кнопками"""
        keyboard = [
            [
                InlineKeyboardButton("📊 Статус", callback_data="status")
            ],
            [
                InlineKeyboardButton("📈 Онлайн-статистика", callback_data="menu_online_stats")
            ],
            [
                InlineKeyboardButton("💬 Комментарии", callback_data="menu_comments")
            ],
            [
                InlineKeyboardButton("📞 Звонки", callback_data="menu_calls")
            ],
            [
                InlineKeyboardButton("💸 Списания", callback_data="menu_writeoffs")
            ],
            [
                InlineKeyboardButton("💳 Ссылки оплаты", callback_data="menu_payment_links")
            ],
            [
                InlineKeyboardButton("💼 Банкротство", callback_data="menu_bankruptcy")
            ],
            [
                InlineKeyboardButton("🔑 Сброс паролей", callback_data="menu_password_reset")
            ],
            [
                InlineKeyboardButton("🛑 Остановить всё", callback_data="stop_all")
            ],
            [
                InlineKeyboardButton("📋 Логи", callback_data="logs")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start - приветствие с кнопками"""
        welcome_msg = """
🤖 <b>MaxCredit Control Bot</b>

Управление ботом через кнопки!

📊 Нажми кнопку для действия:
        """
        await update.message.reply_text(
            welcome_msg, 
            parse_mode='HTML',
            reply_markup=self.get_main_keyboard()
        )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        action = query.data
        
        # ============= ГЛАВНОЕ МЕНЮ =============
        if action == "status":
            await self.show_status(query)
        elif action == "stop_all":
            self.write_command("stop_all")
            await query.edit_message_text(
                "🛑 Команда отправлена: Остановка всех режимов",
                reply_markup=self.get_main_keyboard()
            )
        elif action == "logs":
            await self.show_logs(query)
        elif action == "back_to_main":
            await query.edit_message_text(
                "🤖 <b>MaxCredit Control Bot</b>\n\n"
                "Выберите действие:",
                parse_mode='HTML',
                reply_markup=self.get_main_keyboard()
            )
        
        # ============= ПОДМЕНЮ РЕЖИМОВ =============
        elif action == "menu_online_stats":
            await self.show_menu_online_stats(query)
        elif action == "menu_comments":
            await self.show_menu_comments(query)
        elif action == "menu_calls":
            await self.show_menu_calls(query)
        elif action == "menu_writeoffs":
            await self.show_menu_writeoffs(query)
        elif action == "menu_payment_links":
            await self.show_menu_payment_links(query)
        elif action == "menu_bankruptcy":
            await self.show_menu_bankruptcy(query)
        elif action == "menu_password_reset":
            await self.show_menu_password_reset(query)
        
        # ============= КОМАНДЫ ЗАПУСКА/ОСТАНОВКИ =============
        elif action == "online_stats_refresh":
            # Обновляем меню с актуальными данными
            await self.show_menu_online_stats(query)
        elif action == "online_stats_start":
            self.write_command("start_online_stats")
            await query.edit_message_text(
                "✅ Команда отправлена: Запуск онлайн-статистики",
                reply_markup=self.get_main_keyboard()
            )
        elif action == "online_stats_stop":
            self.write_command("stop_online_stats")
            await query.edit_message_text(
                "🛑 Команда отправлена: Остановка онлайн-статистики",
                reply_markup=self.get_main_keyboard()
            )
        elif action == "comments_start":
            self.write_command("start_comments")
            await query.edit_message_text(
                "✅ Команда отправлена: Запуск комментариев",
                reply_markup=self.get_main_keyboard()
            )
        elif action == "comments_stop":
            self.write_command("stop_comments")
            await query.edit_message_text(
                "🛑 Команда отправлена: Остановка комментариев",
                reply_markup=self.get_main_keyboard()
            )
        elif action == "calls_start":
            self.write_command("start_calls")
            await query.edit_message_text(
                "✅ Команда отправлена: Запуск звонков",
                reply_markup=self.get_main_keyboard()
            )
        elif action == "calls_stop":
            self.write_command("stop_calls")
            await query.edit_message_text(
                "🛑 Команда отправлена: Остановка звонков",
                reply_markup=self.get_main_keyboard()
            )
        elif action == "writeoffs_start":
            self.write_command("start_writeoffs")
            await query.edit_message_text(
                "✅ Команда отправлена: Запуск списаний",
                reply_markup=self.get_main_keyboard()
            )
        elif action == "writeoffs_stop":
            self.write_command("stop_writeoffs")
            await query.edit_message_text(
                "🛑 Команда отправлена: Остановка списаний",
                reply_markup=self.get_main_keyboard()
            )
        elif action == "payment_links_start":
            self.write_command("start_payment_links")
            await query.edit_message_text(
                "✅ Команда отправлена: Запуск отправки ссылок на оплату",
                reply_markup=self.get_main_keyboard()
            )
        elif action == "payment_links_stop":
            self.write_command("stop_payment_links")
            await query.edit_message_text(
                "🛑 Команда отправлена: Остановка отправки ссылок",
                reply_markup=self.get_main_keyboard()
            )
        elif action == "bankruptcy_upload":
            self.waiting_for_file = "bankruptcy"
            self.save_waiting_state("bankruptcy", query.from_user.id)
            await query.edit_message_text(
                "💼 <b>Банкротство - Загрузка файла</b>\n\n"
                "📎 Отправьте Excel файл (.xlsx) с данными для проверки банкротства.\n\n"
                "Файл должен содержать ФИО клиентов.",
                parse_mode='HTML'
            )
        elif action == "bankruptcy_stop":
            self.write_command("stop_bankruptcy")
            await query.edit_message_text(
                "🛑 Команда отправлена: Остановка банкротства",
                reply_markup=self.get_main_keyboard()
            )
        elif action == "password_reset_upload":
            self.waiting_for_file = "password_reset"
            self.save_waiting_state("password_reset", query.from_user.id)
            await query.edit_message_text(
                "🔑 <b>Сброс паролей - Загрузка файла</b>\n\n"
                "📎 Отправьте Excel файл (.xlsx) с телефонами.\n\n"
                "Файл должен содержать список номеров.",
                parse_mode='HTML'
            )
        elif action == "password_reset_stop":
            self.write_command("stop_password_reset")
            await query.edit_message_text(
                "🛑 Команда отправлена: Остановка сброса паролей",
                reply_markup=self.get_main_keyboard()
            )
        
        # ============= НАСТРОЙКИ =============
        elif action == "settings_comments":
            await self.show_settings_comments(query)
        elif action == "settings_calls":
            await self.show_settings_calls(query)
        elif action == "settings_writeoffs":
            await self.show_settings_writeoffs(query)
        elif action == "settings_payment_links":
            await self.show_settings_payment_links(query)
        
        # Обработчики настроек
        elif action.startswith("calls_"):
            await self.handle_calls_settings(query, action)
        elif action.startswith("pl_"):
            await self.handle_payment_links_settings(query, action)
    
    async def show_status(self, query):
        """Показать статус через кнопку"""
        status = self.read_status()
        
        if not status:
            await query.edit_message_text(
                "⚠️ Статус недоступен (бот не запущен)",
                reply_markup=self.get_main_keyboard()
            )
            return
        
        # Формируем сообщение
        msg = "📊 <b>Статус бота</b>\n\n"
        
        # Комментарии
        comments = status.get("comments", {})
        if comments.get("running"):
            msg += f"📝 Комментарии: <b>✅ Работают</b>\n"
            msg += f"   Обработано: {comments.get('processed', 0)}\n"
        else:
            msg += "📝 Комментарии: ⏸ Остановлены\n"
        
        if comments.get("last_error"):
            msg += f"   ⚠️ Ошибка: {comments['last_error']}\n"
        
        msg += "\n"
        
        # Звонки
        calls = status.get("calls", {})
        if calls.get("running"):
            msg += f"📞 Звонки: <b>✅ Работают</b>\n"
            msg += f"   Обработано: {calls.get('processed', 0)}\n"
        else:
            msg += "📞 Звонки: ⏸ Остановлены\n"
        
        if calls.get("last_error"):
            msg += f"   ⚠️ Ошибка: {calls['last_error']}\n"
        
        msg += "\n"
        
        # Списания
        writeoffs = status.get("writeoffs", {})
        if writeoffs.get("running"):
            msg += f"💸 Списания: <b>✅ Работают</b>\n"
            msg += f"   Обработано: {writeoffs.get('processed', 0)}\n"
        else:
            msg += "💸 Списания: ⏸ Остановлены\n"
        
        if writeoffs.get("last_error"):
            msg += f"   ⚠️ Ошибка: {writeoffs['last_error']}\n"
        
        msg += "\n"
        
        # Ссылки на оплату
        payment_links = status.get("payment_links", {})
        if payment_links.get("running"):
            msg += f"💳 Ссылки оплаты: <b>✅ Работают</b>\n"
            msg += f"   Обработано: {payment_links.get('processed', 0)}\n"
        else:
            msg += "💳 Ссылки оплаты: ⏸ Остановлены\n"
        
        if payment_links.get("last_error"):
            msg += f"   ⚠️ Ошибка: {payment_links['last_error']}\n"
        
        msg += "\n"
        
        # Банкротство
        bankruptcy = status.get("bankruptcy", {})
        if bankruptcy.get("running"):
            msg += f"💼 Банкротство: <b>✅ Работает</b>\n"
            msg += f"   Обработано: {bankruptcy.get('processed', 0)}\n"
        else:
            msg += "💼 Банкротство: ⏸ Остановлено\n"
        
        if bankruptcy.get("last_error"):
            msg += f"   ⚠️ Ошибка: {bankruptcy['last_error']}\n"
        
        msg += "\n"
        
        # Сброс паролей
        password_reset = status.get("password_reset", {})
        if password_reset.get("running"):
            msg += f"🔑 Сброс паролей: <b>✅ Работает</b>\n"
            msg += f"   Обработано: {password_reset.get('processed', 0)}\n"
        else:
            msg += "🔑 Сброс паролей: ⏸ Остановлен\n"
        
        if password_reset.get("last_error"):
            msg += f"   ⚠️ Ошибка: {password_reset['last_error']}\n"
        
        msg += "\n"
        
        # Онлайн-статистика
        online_stats = status.get("online_stats", {})
        if online_stats.get("running"):
            msg += f"📈 Онлайн-статистика: <b>✅ Работает</b>\n"
            clients_count = online_stats.get('clients_count', 0)
            sbor = online_stats.get('sbor', 0.0)
            premium = online_stats.get('premium', {})
            if isinstance(premium, dict):
                premium_total = premium.get('total_premium', 0.0)
            else:
                # Совместимость со старым форматом
                premium_total = premium
            msg += f"   Клиентов: {clients_count}\n"
            msg += f"   Сбор: {sbor:,.2f} руб\n"
            msg += f"   Премия: {premium_total:,.2f} руб\n"
        else:
            msg += "📈 Онлайн-статистика: ⏸ Остановлена\n"
        
        if online_stats.get("last_error"):
            msg += f"   ⚠️ Ошибка: {online_stats['last_error']}\n"
        
        # Время обновления
        timestamp = status.get("timestamp", "Неизвестно")
        msg += f"\n🕐 Обновлено: {timestamp}"
        
        await query.edit_message_text(
            msg, 
            parse_mode='HTML',
            reply_markup=self.get_main_keyboard()
        )
    
    async def show_logs(self, query):
        """Показать логи через кнопку"""
        logs_file = os.path.join(SHARED_DIR, "bot_logs.txt")
        
        if not os.path.exists(logs_file):
            await query.edit_message_text(
                "📋 Логи пока пусты",
                reply_markup=self.get_main_keyboard()
            )
            return
        
        try:
            with open(logs_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Берём последние 20 строк
            last_lines = lines[-20:] if len(lines) > 20 else lines
            logs_text = ''.join(last_lines)
            
            # Обрезаем если слишком длинное
            if len(logs_text) > 3500:
                logs_text = logs_text[-3500:]
            
            await query.edit_message_text(
                f"📋 <b>Последние логи:</b>\n\n<pre>{logs_text}</pre>",
                parse_mode='HTML',
                reply_markup=self.get_main_keyboard()
            )
        except Exception as e:
            await query.edit_message_text(
                f"⚠️ Ошибка чтения логов: {e}",
                reply_markup=self.get_main_keyboard()
            )
        
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /status - показать статус"""
        status = self.read_status()
        
        if not status:
            await update.message.reply_text("⚠️ Статус недоступен (бот не запущен)")
            return
        
        # Формируем красивое сообщение
        msg = "📊 <b>Статус бота</b>\n\n"
        
        # Комментарии
        comments = status.get("comments", {})
        if comments.get("running"):
            msg += f"📝 Комментарии: <b>✅ Работают</b>\n"
            msg += f"   Обработано: {comments.get('processed', 0)}\n"
        else:
            msg += "📝 Комментарии: ⏸ Остановлены\n"
        
        if comments.get("last_error"):
            msg += f"   ⚠️ Ошибка: {comments['last_error']}\n"
        
        msg += "\n"
        
        # Звонки
        calls = status.get("calls", {})
        if calls.get("running"):
            msg += f"📞 Звонки: <b>✅ Работают</b>\n"
            msg += f"   Обработано: {calls.get('processed', 0)}\n"
        else:
            msg += "📞 Звонки: ⏸ Остановлены\n"
        
        if calls.get("last_error"):
            msg += f"   ⚠️ Ошибка: {calls['last_error']}\n"
        
        msg += "\n"
        
        # Списания
        writeoffs = status.get("writeoffs", {})
        if writeoffs.get("running"):
            msg += f"💸 Списания: <b>✅ Работают</b>\n"
            msg += f"   Обработано: {writeoffs.get('processed', 0)}\n"
        else:
            msg += "💸 Списания: ⏸ Остановлены\n"
        
        if writeoffs.get("last_error"):
            msg += f"   ⚠️ Ошибка: {writeoffs['last_error']}\n"
        
        # Время обновления
        timestamp = status.get("timestamp", "Неизвестно")
        msg += f"\n🕐 Обновлено: {timestamp}"
        
        await update.message.reply_text(msg, parse_mode='HTML')
    
    async def comments_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запустить комментарии"""
        self.write_command("start_comments")
        await update.message.reply_text("✅ Команда отправлена: Запуск комментариев")
    
    async def comments_stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Остановить комментарии"""
        self.write_command("stop_comments")
        await update.message.reply_text("🛑 Команда отправлена: Остановка комментариев")
    
    async def calls_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запустить звонки"""
        self.write_command("start_calls")
        await update.message.reply_text("✅ Команда отправлена: Запуск звонков")
    
    async def calls_stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Остановить звонки"""
        self.write_command("stop_calls")
        await update.message.reply_text("🛑 Команда отправлена: Остановка звонков")
    
    async def writeoffs_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запустить списания"""
        self.write_command("start_writeoffs")
        await update.message.reply_text("✅ Команда отправлена: Запуск списаний")
    
    async def writeoffs_stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Остановить списания"""
        self.write_command("stop_writeoffs")
        await update.message.reply_text("🛑 Команда отправлена: Остановка списаний")
    
    async def stop_all_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Остановить всё"""
        self.write_command("stop_all")
        await update.message.reply_text("🛑 Команда отправлена: Остановка всех режимов")
    
    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать последние логи"""
        logs_file = os.path.join(SHARED_DIR, "bot_logs.txt")
        
        if not os.path.exists(logs_file):
            await update.message.reply_text("📋 Логи пока пусты")
            return
        
        try:
            with open(logs_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Берём последние 20 строк
            last_lines = lines[-20:] if len(lines) > 20 else lines
            logs_text = ''.join(last_lines)
            
            # Обрезаем если слишком длинное
            if len(logs_text) > 4000:
                logs_text = logs_text[-4000:]
            
            await update.message.reply_text(f"📋 <b>Последние логи:</b>\n\n<pre>{logs_text}</pre>", parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка чтения логов: {e}")
    
    async def payment_links_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запуск режима ссылок на оплату"""
        self.write_command("start_payment_links")
        await update.message.reply_text(
            "✅ Команда отправлена: Запуск ссылок на оплату\n"
            "Статус можно проверить через /status",
            reply_markup=self.get_main_keyboard()
        )
    
    async def payment_links_stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Остановка режима ссылок на оплату"""
        self.write_command("stop_payment_links")
        await update.message.reply_text(
            "🛑 Команда отправлена: Остановка ссылок на оплату",
            reply_markup=self.get_main_keyboard()
        )
    
    async def online_stats_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запуск онлайн-статистики"""
        self.write_command("start_online_stats")
        await update.message.reply_text(
            "✅ Команда отправлена: Запуск онлайн-статистики\n"
            "Мониторинг начнётся в фоновом режиме",
            reply_markup=self.get_main_keyboard()
        )
    
    async def online_stats_stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Остановка онлайн-статистики"""
        self.write_command("stop_online_stats")
        await update.message.reply_text(
            "🛑 Команда отправлена: Остановка онлайн-статистики",
            reply_markup=self.get_main_keyboard()
        )
    
    async def online_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать текущую онлайн-статистику"""
        status = self.read_status()
        
        if not status:
            await update.message.reply_text(
                "⚠️ Статус недоступен (бот не запущен)",
                reply_markup=self.get_main_keyboard()
            )
            return
        
        online_stats = status.get("online_stats", {})
        
        if not online_stats.get("running"):
            await update.message.reply_text(
                "📈 <b>Онлайн-статистика</b>\n\n"
                "🔴 Мониторинг не запущен\n\n"
                "Запустите через /online_stats_start",
                parse_mode='HTML',
                reply_markup=self.get_main_keyboard()
            )
            return
        
        clients_count = online_stats.get('clients_count', 0)
        sbor = online_stats.get('sbor', 0.0)
        premium = online_stats.get('premium', {})
        if isinstance(premium, dict):
            premium_total = premium.get('total_premium', 0.0)
            premium_sbor = premium.get('sbor_premium', 0.0)
            premium_ext = premium.get('extensions_premium', 0.0)
            ext_count = premium.get('extensions_count', 0)
        else:
            # Совместимость со старым форматом
            premium_total = premium
            premium_sbor = premium
            premium_ext = 0.0
            ext_count = 0
        timestamp = status.get("timestamp", "Неизвестно")
        
        msg = (
            f"📈 <b>Онлайн-статистика</b>\n\n"
            f"🟢 <b>Статус: Работает</b>\n\n"
            f"👥 Клиентов: <b>{clients_count}</b>\n"
            f"💰 Сбор: <b>{sbor:,.2f} руб</b>\n\n"
            f"💵 <b>Премия за месяц: {premium_total:,.2f} руб</b>\n"
            f"   • По сбору: <b>{premium_sbor:,.2f} руб</b>\n"
            f"   • По продлениям: <b>{premium_ext:,.2f} руб</b> ({ext_count} шт)\n\n"
            f"🕐 Обновлено: {timestamp}"
        )
        
        await update.message.reply_text(
            msg,
            parse_mode='HTML',
            reply_markup=self.get_main_keyboard()
        )
    
    # ============================================================================
    # ПОДМЕНЮ РЕЖИМОВ
    # ============================================================================
    
    async def show_menu_comments(self, query):
        """Показать меню режима комментариев"""
        keyboard = [
            [InlineKeyboardButton("▶ Запустить", callback_data="comments_start")],
            [InlineKeyboardButton("⏸ Остановить", callback_data="comments_stop")],
            [InlineKeyboardButton("◀ Назад в главное меню", callback_data="back_to_main")]
        ]
        
        await query.edit_message_text(
            "💬 <b>Комментарии</b>\n\n"
            "Автоматическая отправка комментариев клиентам.\n\n"
            "Выберите действие:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_menu_calls(self, query):
        """Показать меню режима звонков"""
        keyboard = [
            [InlineKeyboardButton("▶ Запустить", callback_data="calls_start")],
            [InlineKeyboardButton("⏸ Остановить", callback_data="calls_stop")],
            [InlineKeyboardButton("⚙️ Настройки", callback_data="settings_calls")],
            [InlineKeyboardButton("◀ Назад в главное меню", callback_data="back_to_main")]
        ]
        
        await query.edit_message_text(
            "📞 <b>Звонки</b>\n\n"
            "Автоматический обзвон клиентов через Zoiper.\n\n"
            "Выберите действие:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_menu_writeoffs(self, query):
        """Показать меню режима списаний"""
        keyboard = [
            [InlineKeyboardButton("▶ Запустить", callback_data="writeoffs_start")],
            [InlineKeyboardButton("⏸ Остановить", callback_data="writeoffs_stop")],
            [InlineKeyboardButton("◀ Назад в главное меню", callback_data="back_to_main")]
        ]
        
        await query.edit_message_text(
            "💸 <b>Списания</b>\n\n"
            "Автоматическое списание долгов клиентов.\n\n"
            "Выберите действие:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_menu_payment_links(self, query):
        """Показать меню режима ссылок на оплату"""
        keyboard = [
            [InlineKeyboardButton("▶ Запустить", callback_data="payment_links_start")],
            [InlineKeyboardButton("⏸ Остановить", callback_data="payment_links_stop")],
            [InlineKeyboardButton("⚙️ Настройки", callback_data="settings_payment_links")],
            [InlineKeyboardButton("◀ Назад в главное меню", callback_data="back_to_main")]
        ]
        
        await query.edit_message_text(
            "💳 <b>Ссылки на оплату</b>\n\n"
            "Автоматическая отправка платёжных ссылок клиентам.\n\n"
            "Выберите действие:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_menu_bankruptcy(self, query):
        """Показать меню режима банкротства"""
        keyboard = [
            [InlineKeyboardButton("📤 Загрузить файл и запустить", callback_data="bankruptcy_upload")],
            [InlineKeyboardButton("⏸ Остановить", callback_data="bankruptcy_stop")],
            [InlineKeyboardButton("◀ Назад в главное меню", callback_data="back_to_main")]
        ]
        
        await query.edit_message_text(
            "💼 <b>Банкротство</b>\n\n"
            "Проверка клиентов на банкротство.\n\n"
            "📎 Загрузите Excel файл с ФИО клиентов для проверки.\n\n"
            "Выберите действие:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_menu_password_reset(self, query):
        """Показать меню режима сброса паролей"""
        keyboard = [
            [InlineKeyboardButton("📤 Загрузить файл и запустить", callback_data="password_reset_upload")],
            [InlineKeyboardButton("⏸ Остановить", callback_data="password_reset_stop")],
            [InlineKeyboardButton("◀ Назад в главное меню", callback_data="back_to_main")]
        ]
        
        await query.edit_message_text(
            "🔑 <b>Сброс паролей</b>\n\n"
            "Автоматический сброс паролей клиентов.\n\n"
            "📎 Загрузите Excel файл с телефонами клиентов.\n\n"
            "Выберите действие:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_menu_online_stats(self, query):
        """Показать меню онлайн-статистики с текущими данными"""
        # Читаем текущий статус
        status = self.read_status()
        
        # Формируем сообщение с текущими данными
        msg = "📈 <b>Онлайн-статистика</b>\n\n"
        
        if status:
            online_stats = status.get("online_stats", {})
            if online_stats.get("running"):
                clients_count = online_stats.get('clients_count', 0)
                sbor = online_stats.get('sbor', 0.0)
                premium = online_stats.get('premium', {})
                if isinstance(premium, dict):
                    premium_total = premium.get('total_premium', 0.0)
                    premium_sbor = premium.get('sbor_premium', 0.0)
                    premium_ext = premium.get('extensions_premium', 0.0)
                    ext_count = premium.get('extensions_count', 0)
                else:
                    # Совместимость со старым форматом
                    premium_total = premium
                    premium_sbor = premium
                    premium_ext = 0.0
                    ext_count = 0
                
                msg += "🟢 <b>Статус: Работает</b>\n\n"
                msg += f"👥 Клиентов: <b>{clients_count}</b>\n"
                msg += f"💰 Сбор: <b>{sbor:,.2f} руб</b>\n\n"
                msg += f"💵 <b>Премия: {premium_total:,.2f} руб</b>\n"
                msg += f"   • Сбор: <b>{premium_sbor:,.2f} руб</b>\n"
                msg += f"   • Продления: <b>{premium_ext:,.2f} руб</b> ({ext_count} шт)\n\n"
                
                timestamp = status.get("timestamp", "")
                if timestamp:
                    msg += f"🕐 Обновлено: {timestamp}\n\n"
            else:
                msg += "🔴 <b>Статус: Остановлен</b>\n\n"
        else:
            msg += "⚪ <b>Статус: Не запущен</b>\n\n"
        
        msg += "🔔 Бот будет уведомлять вас о:\n"
        msg += "• Новых оплатах\n"
        msg += "• Добавлении/удалении клиентов\n"
        msg += "• Изменении общего сбора\n\n"
        msg += "Обновление каждую минуту.\n\n"
        msg += "Выберите действие:"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить данные", callback_data="online_stats_refresh")],
            [InlineKeyboardButton("▶ Включить мониторинг", callback_data="online_stats_start")],
            [InlineKeyboardButton("⏸ Выключить мониторинг", callback_data="online_stats_stop")],
            [InlineKeyboardButton("◀ Назад в главное меню", callback_data="back_to_main")]
        ]
        
        await query.edit_message_text(
            msg,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ============================================================================
    # НАСТРОЙКИ РЕЖИМОВ
    # ============================================================================
    
    async def show_settings_calls(self, query):
        """Показать настройки звонков"""
        settings = self.load_settings("calls")
        
        use_timezones = settings.get("use_timezones", False)
        use_duration = settings.get("use_call_duration", False)
        duration_min = settings.get("duration_min", 30)
        duration_max = settings.get("duration_max", 60)
        
        tz_status = "✅ Вкл" if use_timezones else "❌ Выкл"
        dur_status = "✅ Вкл" if use_duration else "❌ Выкл"
        dur_text = f"{duration_min}-{duration_max} сек"
        
        keyboard = [
            [InlineKeyboardButton(
                f"🌍 Часовые пояса: {tz_status}",
                callback_data="calls_toggle_tz"
            )],
            [InlineKeyboardButton(
                f"⏱ Длительность звонка: {dur_status}",
                callback_data="calls_toggle_duration"
            )],
            [InlineKeyboardButton(
                f"📊 Время звонка: {dur_text}",
                callback_data="calls_set_duration"
            )],
            [InlineKeyboardButton("◀ Назад", callback_data="menu_calls")]
        ]
        
        await query.edit_message_text(
            "⚙️ <b>Настройки звонков</b>\n\n"
            f"🌍 Фильтр по часовым поясам: {tz_status}\n"
            f"⏱ Длительность звонка: {dur_status}\n"
            f"📊 Время звонка: {dur_text}\n\n"
            "Выберите параметр:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_settings_payment_links(self, query):
        """Показать настройки ссылок на оплату"""
        settings = self.load_settings("payment_links")
        
        use_delay = settings.get("use_delay_filter", False)
        delay_from = settings.get("delay_from", "")
        delay_to = settings.get("delay_to", "")
        max_links = settings.get("max_links")
        
        delay_status = "✅ Вкл" if use_delay else "❌ Выкл"
        delay_text = f"{delay_from}-{delay_to} дней" if delay_from and delay_to else "не указано"
        max_links_text = str(max_links) if max_links else "все"
        
        keyboard = [
            [InlineKeyboardButton(
                f"📅 Фильтр по дням: {delay_status}",
                callback_data="pl_toggle_delay"
            )],
            [InlineKeyboardButton(
                f"📊 Дни просрочки: {delay_text}",
                callback_data="pl_set_delay_days"
            )],
            [InlineKeyboardButton(
                f"🎯 Количество: {max_links_text}",
                callback_data="pl_set_max_links"
            )],
            [InlineKeyboardButton("◀ Назад", callback_data="menu_payment_links")]
        ]
        
        await query.edit_message_text(
            "⚙️ <b>Настройки ссылок на оплату</b>\n\n"
            f"📅 Фильтр по дням просрочки: {delay_status}\n"
            f"📊 Дни просрочки: {delay_text}\n"
            f"🎯 Количество ссылок: {max_links_text}\n\n"
            "Выберите параметр:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_settings_comments(self, query):
        """Показать настройки комментариев (если будут)"""
        keyboard = [
            [InlineKeyboardButton("◀ Назад", callback_data="menu_comments")]
        ]
        
        await query.edit_message_text(
            "⚙️ <b>Настройки комментариев</b>\n\n"
            "Настройки пока не добавлены.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_settings_writeoffs(self, query):
        """Показать настройки списаний (если будут)"""
        keyboard = [
            [InlineKeyboardButton("◀ Назад", callback_data="menu_writeoffs")]
        ]
        
        await query.edit_message_text(
            "⚙️ <b>Настройки списаний</b>\n\n"
            "Настройки пока не добавлены.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ============================================================================
    # ОБРАБОТЧИКИ НАСТРОЕК
    # ============================================================================
    
    async def handle_calls_settings(self, query, action):
        """Обработка настроек звонков"""
        settings = self.load_settings("calls")
        
        if action == "calls_toggle_tz":
            settings["use_timezones"] = not settings.get("use_timezones", False)
            self.save_settings("calls", settings)
            await self.show_settings_calls(query)
            
        elif action == "calls_toggle_duration":
            settings["use_call_duration"] = not settings.get("use_call_duration", False)
            self.save_settings("calls", settings)
            await self.show_settings_calls(query)
            
        elif action == "calls_set_duration":
            self.waiting_for_file = "calls_duration"
            self.save_waiting_state("calls_duration", query.from_user.id)
            await query.edit_message_text(
                "⏱ <b>Установка длительности звонка</b>\n\n"
                "Отправьте время в секундах в формате:\n"
                "<code>мин макс</code>\n\n"
                "Например: <code>30 60</code> (от 30 до 60 секунд)",
                parse_mode='HTML'
            )
    
    def load_settings(self, mode: str):
        """
        Загрузка настроек режима из файла
        
        Args:
            mode: "calls", "payment_links", "comments", "writeoffs"
        """
        settings_file = os.path.join(SHARED_DIR, "bot_settings.json")
        
        # Настройки по умолчанию
        default_settings = {
            "calls": {
                "use_timezones": False,
                "use_call_duration": False,
                "duration_min": 30,
                "duration_max": 60
            },
            "payment_links": {
                "use_delay_filter": False,
                "delay_from": "",
                "delay_to": "",
                "max_links": None
            },
            "comments": {},
            "writeoffs": {}
        }
        
        if not os.path.exists(settings_file):
            return default_settings.get(mode, {})
        
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                return settings.get(mode, default_settings.get(mode, {}))
        except:
            return default_settings.get(mode, {})
    
    def save_settings(self, mode: str, mode_settings: dict):
        """
        Сохранение настроек режима в файл
        
        Args:
            mode: "calls", "payment_links", "comments", "writeoffs"
            mode_settings: словарь с настройками режима
        """
        settings_file = os.path.join(SHARED_DIR, "bot_settings.json")
        
        # Загружаем существующие настройки
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            except:
                settings = {}
        else:
            settings = {}
        
        # Обновляем настройки режима
        settings[mode] = mode_settings
        
        # Сохраняем
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
            return False
    
    def save_waiting_state(self, state, user_id):
        """Сохранить состояние ожидания в файл"""
        try:
            with open(self.waiting_state_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "waiting_for": state, 
                    "user_id": user_id,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }, f, ensure_ascii=False, indent=2)
            print(f"DEBUG: Сохранено состояние ожидания: {state} для user {user_id}")
        except Exception as e:
            print(f"Ошибка сохранения waiting_state: {e}")

    def load_waiting_state(self, user_id):
        """Загрузить состояние ожидания из файла"""
        try:
            if os.path.exists(self.waiting_state_file):
                with open(self.waiting_state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get("user_id") == user_id:
                        state = data.get("waiting_for")
                        print(f"DEBUG: Загружено состояние: {state} для user {user_id}")
                        return state
        except Exception as e:
            print(f"Ошибка загрузки waiting_state: {e}")
        return None

    def clear_waiting_state(self):
        """Очистить состояние ожидания"""
        try:
            if os.path.exists(self.waiting_state_file):
                os.remove(self.waiting_state_file)
                print("DEBUG: Состояние ожидания очищено")
        except Exception as e:
            print(f"Ошибка очистки waiting_state: {e}")
    
    async def handle_payment_links_settings(self, query, action):
        """Обработка настроек payment_links"""
        settings = self.load_settings("payment_links")
        
        if action == "pl_toggle_delay":
            # Переключить фильтр по дням
            settings["use_delay_filter"] = not settings.get("use_delay_filter", False)
            self.save_settings("payment_links", settings)
            await self.show_settings_payment_links(query)
            
        elif action == "pl_set_delay_days":
            # Запросить дни просрочки
            self.waiting_for_file = "pl_delay_days"
            self.save_waiting_state("pl_delay_days", query.from_user.id)
            await query.edit_message_text(
                "📊 <b>Установка дней просрочки</b>\n\n"
                "Отправьте дни просрочки в формате:\n"
                "<code>от до</code>\n\n"
                "Например: <code>1 30</code> (от 1 до 30 дней)\n"
                "Или: <code>0 0</code> чтобы сбросить",
                parse_mode='HTML'
            )
            
        elif action == "pl_set_max_links":
            # Запросить количество ссылок
            self.waiting_for_file = "pl_max_links"
            self.save_waiting_state("pl_max_links", query.from_user.id)
            await query.edit_message_text(
                "🎯 <b>Установка количества ссылок</b>\n\n"
                "Отправьте число - сколько ссылок отправить:\n\n"
                "Например: <code>50</code>\n"
                "Или: <code>0</code> чтобы отправлять все ссылки",
                parse_mode='HTML'
            )
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка загруженного файла"""
        user_id = update.effective_user.id
        
        # Загружаем состояние из файла если не установлено
        if not self.waiting_for_file:
            self.waiting_for_file = self.load_waiting_state(user_id)
        
        if not self.waiting_for_file:
            await update.message.reply_text(
                "⚠️ Я не жду файл. Используйте кнопки:\n"
                "💼 Банкротство 📎\n"
                "🔑 Сброс паролей 📎"
            )
            return
        
        # Если ожидаем настройки - это не файл
        if self.waiting_for_file in ["pl_delay_days", "pl_max_links", "calls_duration"]:
            await update.message.reply_text(
                "⚠️ Отправьте текстовое сообщение, а не файл!"
            )
            return
        
        document = update.message.document
        
        # Проверяем расширение файла
        if not document.file_name.endswith('.xlsx'):
            await update.message.reply_text(
                "⚠️ Неверный формат файла!\n"
                "Отправьте файл с расширением .xlsx"
            )
            return
        
        try:
            # Скачиваем файл
            await update.message.reply_text("⏳ Загружаю файл...")
            
            file = await context.bot.get_file(document.file_id)
            
            # Определяем куда сохранять
            if self.waiting_for_file == "bankruptcy":
                file_path = BANKRUPTCY_FILE
                command = "start_bankruptcy"
                mode_name = "Банкротство"
            else:  # password_reset
                file_path = PASSWORD_RESET_FILE
                command = "start_password_reset"
                mode_name = "Сброс паролей"
            
            # Сохраняем файл
            await file.download_to_drive(file_path)
            
            await update.message.reply_text(
                f"✅ Файл загружен: {document.file_name}\n"
                f"📊 Размер: {document.file_size / 1024:.1f} KB\n\n"
                f"🚀 Запускаю {mode_name}..."
            )
            
            # Отправляем команду на запуск
            self.write_command(command)
            
            # Сбрасываем ожидание
            self.waiting_for_file = None
            self.clear_waiting_state()
            
            await update.message.reply_text(
                f"✅ Команда отправлена: Запуск {mode_name}\n\n"
                f"Следите за статусом через кнопку 📊 Статус",
                reply_markup=self.get_main_keyboard()
            )
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка загрузки файла: {e}\n\n"
                f"Попробуйте снова."
            )
            self.waiting_for_file = None
            self.clear_waiting_state()
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений (для настроек)"""
        user_id = update.effective_user.id
        
        # Загружаем состояние из файла если не установлено
        if not self.waiting_for_file:
            self.waiting_for_file = self.load_waiting_state(user_id)
        
        if not self.waiting_for_file:
            print(f"DEBUG: Текст '{update.message.text}' получен от user {user_id}, но waiting_for_file пусто")
            return
        
        print(f"DEBUG: Обрабатываем текст '{update.message.text}' для режима {self.waiting_for_file} от user {user_id}")
        
        text = update.message.text.strip()
        
        # ============= НАСТРОЙКИ ЗВОНКОВ =============
        if self.waiting_for_file == "calls_duration":
            try:
                parts = text.split()
                if len(parts) != 2:
                    await update.message.reply_text(
                        "⚠️ Неверный формат!\n"
                        "Отправьте два числа через пробел: <code>мин макс</code>\n"
                        "Например: <code>30 60</code>",
                        parse_mode='HTML'
                    )
                    return
                
                duration_min = int(parts[0])
                duration_max = int(parts[1])
                
                if duration_min < 1 or duration_max < duration_min:
                    await update.message.reply_text(
                        "⚠️ Некорректные значения!\n"
                        "Минимум должен быть >= 1, максимум >= минимума",
                        parse_mode='HTML'
                    )
                    return
                
                # Сохраняем
                settings = self.load_settings("calls")
                settings["duration_min"] = duration_min
                settings["duration_max"] = duration_max
                self.save_settings("calls", settings)
                
                self.waiting_for_file = None
                self.clear_waiting_state()
                
                await update.message.reply_text(
                    f"✅ Длительность звонка установлена: {duration_min}-{duration_max} секунд",
                    reply_markup=self.get_main_keyboard()
                )
                
            except ValueError:
                await update.message.reply_text(
                    "⚠️ Ошибка! Отправьте два числа.\n"
                    "Например: <code>30 60</code>",
                    parse_mode='HTML'
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка: {e}")
                self.waiting_for_file = None
                self.clear_waiting_state()
        
        # ============= НАСТРОЙКИ PAYMENT_LINKS =============
        elif self.waiting_for_file == "pl_delay_days":
            try:
                parts = text.split()
                if len(parts) != 2:
                    await update.message.reply_text(
                        "⚠️ Неверный формат!\n"
                        "Отправьте два числа через пробел: <code>от до</code>\n"
                        "Например: <code>1 30</code>",
                        parse_mode='HTML'
                    )
                    return
                
                delay_from = parts[0]
                delay_to = parts[1]
                
                # Проверка что это числа
                int(delay_from)
                int(delay_to)
                
                # Сохраняем
                settings = self.load_settings("payment_links")
                settings["delay_from"] = delay_from
                settings["delay_to"] = delay_to
                self.save_settings("payment_links", settings)
                
                self.waiting_for_file = None
                self.clear_waiting_state()
                
                await update.message.reply_text(
                    f"✅ Дни просрочки установлены: {delay_from} - {delay_to} дней",
                    reply_markup=self.get_main_keyboard()
                )
                
            except ValueError:
                await update.message.reply_text(
                    "⚠️ Ошибка! Отправьте два числа.\n"
                    "Например: <code>1 30</code>",
                    parse_mode='HTML'
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка: {e}")
                self.waiting_for_file = None
                self.clear_waiting_state()
                
        elif self.waiting_for_file == "pl_max_links":
            try:
                max_links = int(text)
                
                if max_links < 0:
                    await update.message.reply_text("⚠️ Число должно быть положительным!")
                    return
                
                # Сохраняем
                settings = self.load_settings("payment_links")
                settings["max_links"] = max_links if max_links > 0 else None
                self.save_settings("payment_links", settings)
                
                self.waiting_for_file = None
                self.clear_waiting_state()
                
                links_text = str(max_links) if max_links > 0 else "все"
                await update.message.reply_text(
                    f"✅ Количество ссылок установлено: {links_text}",
                    reply_markup=self.get_main_keyboard()
                )
                
            except ValueError:
                await update.message.reply_text(
                    "⚠️ Ошибка! Отправьте число.\n"
                    "Например: <code>50</code> или <code>0</code> для всех",
                    parse_mode='HTML'
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка: {e}")
                self.waiting_for_file = None
                self.clear_waiting_state()
    
    def read_status(self):
        """Читает текущий статус бота"""
        if not os.path.exists(STATUS_FILE):
            return None
        
        try:
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    
    def write_command(self, command: str):
        """Записывает команду для основного бота"""
        command_data = {
            "command": command,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "executed": False
        }
        
        try:
            with open(COMMANDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(command_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка записи команды: {e}")
    
    async def send_notification(self, message: str):
        """Отправка уведомления в Telegram"""
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"Ошибка отправки уведомления: {e}")
    
    async def send_file(self, file_path: str, caption: str = None):
        """Отправка файла в Telegram"""
        try:
            if not os.path.exists(file_path):
                print(f"⚠️ Файл не найден: {file_path}")
                return False
            
            with open(file_path, 'rb') as f:
                await self.app.bot.send_document(
                    chat_id=self.chat_id,
                    document=f,
                    caption=caption,
                    parse_mode='HTML' if caption else None
                )
            
            print(f"✅ Файл отправлен: {file_path}")
            return True
        except Exception as e:
            print(f"❌ Ошибка отправки файла: {e}")
            return False
    
    async def start_bot(self):
        """Запуск бота"""
        print("=" * 60)
        print("🤖 Telegram Bot для MaxCreditBot")
        print("=" * 60)
        print(f"Token: {self.token[:20]}...")
        print(f"Chat ID: {self.chat_id}")
        print("Запуск...")
        
        # Создаём приложение
        self.app = Application.builder().token(self.token).build()
        
        # ОТЛАДКА
        print(f"🔍 DEBUG: TELEGRAM_MANAGER_AVAILABLE = {TELEGRAM_MANAGER_AVAILABLE}")
        print(f"🔍 DEBUG: set_telegram_bot function = {set_telegram_bot}")
        
        # РЕГИСТРИРУЕМ БОТА В TELEGRAM MANAGER
        if TELEGRAM_MANAGER_AVAILABLE:
            set_telegram_bot(self)
            print("✅ Бот зарегистрирован в TelegramManager")
        else:
            print("❌ DEBUG: TELEGRAM_MANAGER_AVAILABLE is False!")
        
        # Регистрируем команды
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(CommandHandler("comments_start", self.comments_start_command))
        self.app.add_handler(CommandHandler("comments_stop", self.comments_stop_command))
        self.app.add_handler(CommandHandler("calls_start", self.calls_start_command))
        self.app.add_handler(CommandHandler("calls_stop", self.calls_stop_command))
        self.app.add_handler(CommandHandler("writeoffs_start", self.writeoffs_start_command))
        self.app.add_handler(CommandHandler("writeoffs_stop", self.writeoffs_stop_command))
        self.app.add_handler(CommandHandler("payment_links_start", self.payment_links_start_command))
        self.app.add_handler(CommandHandler("payment_links_stop", self.payment_links_stop_command))
        self.app.add_handler(CommandHandler("online_stats_start", self.online_stats_start_command))
        self.app.add_handler(CommandHandler("online_stats_stop", self.online_stats_stop_command))
        self.app.add_handler(CommandHandler("online_stats", self.online_stats_command))
        self.app.add_handler(CommandHandler("stop_all", self.stop_all_command))
        self.app.add_handler(CommandHandler("logs", self.logs_command))
        
        # Обработчик кнопок
        self.app.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Обработчик документов (файлов)
        self.app.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        
        # Обработчик текстовых сообщений (для настроек)
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        
        print("✅ Бот запущен!")
        print("Отправь /start своему боту в Telegram")
        print("-" * 60)
        
        # Запускаем бота вручную (без app.run_polling чтобы избежать конфликта event loop)
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        
        # Держим бота активным бесконечно
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass
        finally:
            # Корректное завершение
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()


def start_telegram_bot():
    """Функция для запуска из основного приложения"""
    global _telegram_bot_instance
    
    settings = get_settings_manager()
    token = settings.get_telegram_token()
    chat_id = settings.get_telegram_chat_id()
    
    if not token or not chat_id:
        print("⚠️ Telegram настройки не заполнены. Бот не запущен.")
        return
    
    bot = TelegramBot(token, chat_id)
    _telegram_bot_instance = bot  # Сохраняем глобально
    
    # Используем существующий event loop или создаём новый
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Если loop уже запущен - используем create_task
            asyncio.create_task(bot.start_bot())
        else:
            # Если не запущен - запускаем
            loop.run_until_complete(bot.start_bot())
    except RuntimeError:
        # Нет event loop - создаём новый
        asyncio.run(bot.start_bot())


# Глобальный экземпляр бота
_telegram_bot_instance = None


if __name__ == "__main__":
    # Для тестирования - запуск напрямую
    start_telegram_bot()