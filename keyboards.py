from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🎲 Создать комнату", callback_data="create_room"),
        InlineKeyboardButton("🎯 Войти в комнату", callback_data="join_room")
    )
    return keyboard

def get_host_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🎲 Бросить кости", callback_data="throw_dice"),
        InlineKeyboardButton("❌ Выгнать игрока", callback_data="kick_player")
    )
    return keyboard

def get_player_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎲 Бросить кости", callback_data="throw_dice"))
    return keyboard
