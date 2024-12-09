import asyncio
from aiogram import Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from database import init_db, cleanup_rooms
from bot_instance import bot
from handlers import (
    start_command,
    create_room_callback,
    join_room_callback,
    process_room_code,
    throw_dice_callback,
    kick_player_callback,
    GameStates
)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

dp.register_message_handler(start_command, commands=['start'])
dp.register_callback_query_handler(create_room_callback, text='create_room')
dp.register_callback_query_handler(join_room_callback, text='join_room')
dp.register_message_handler(process_room_code, state=GameStates.waiting_for_room_code)
dp.register_callback_query_handler(throw_dice_callback, lambda c: c.data == 'throw_dice', state='*')
dp.register_callback_query_handler(kick_player_callback, text='kick_player', state=GameStates.in_game)

async def on_startup(dp):
    await init_db()
    asyncio.create_task(periodic_cleanup())

async def periodic_cleanup():
    while True:
        await cleanup_rooms()
        await asyncio.sleep(3600)

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)