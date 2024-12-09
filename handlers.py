from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from database import async_session, Room
from keyboards import get_main_keyboard, get_host_keyboard, get_player_keyboard
from utils import generate_room_code, roll_dice
from sqlalchemy import select, or_
from bot_instance import bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class GameStates(StatesGroup):
    waiting_for_room_code = State()
    waiting_for_password = State()
    in_game = State()

def get_throw_dice_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎲 Бросить кости", callback_data="throw_dice"))
    return keyboard

async def start_command(message: types.Message):
    # Отправляем картинку
    await bot.send_photo(
        message.chat.id,
        'https://wallpaper-a-day.com/wp-content/uploads/2017/12/tumblr_p0eexyzxtl1u36eloo1_1280.jpg',
        caption=(
            "🎲 Добро пожаловать в игру в кости!\n\n"
            "👨‍💻 Создатель - КИАНА\n"
            "🌐 Форум - https://lolz.live/kqlol/\n"
        ),
        reply_markup=get_main_keyboard()
    )

async def create_room_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    room_code = generate_room_code()
    user = callback_query.from_user
    
    async with async_session() as session:
        new_room = Room(
            code=room_code,
            player1_id=user.id,
            player1_name=f"{user.first_name} {user.last_name if user.last_name else ''}",
        )
        session.add(new_room)
        await session.commit()
    
    await callback_query.message.answer(
        f"🎯 Комната создана!\nКод комнаты: {room_code}\n"
        f"Игрок 1: {new_room.player1_name} (ID: {new_room.player1_id})\n"
        "Ожидание второго игрока...",
        reply_markup=get_host_keyboard()
    )
    await callback_query.answer()

async def join_room_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await GameStates.waiting_for_room_code.set()
    await callback_query.message.answer("📝 Введите код комнаты:")
    await callback_query.answer()

async def process_room_code(message: types.Message, state: FSMContext):
    user = message.from_user
    room_code = message.text.upper()
    
    async with async_session() as session:
        query = select(Room).where(Room.code == room_code, Room.is_active == True)
        result = await session.execute(query)
        room = result.scalar_one_or_none()
        
        if not room:
            await state.finish()
            await message.answer(
                "❌ Комната не найдена!\nПопробуйте еще раз.", 
                reply_markup=get_main_keyboard()
            )
            return
            
        if room.player2_id:
            await state.finish()
            await message.answer(
                "❌ Комната уже заполнена!\nПопробуйте другую комнату.", 
                reply_markup=get_main_keyboard()
            )
            return
        
        room.player2_id = user.id
        room.player2_name = f"{user.first_name} {user.last_name if user.last_name else ''}"
        await session.commit()
        
        game_status = (
            f"🎮 Игра начинается!\n\n"
            f"Игрок 1: {room.player1_name}\n"
            f"Игрок 2: {room.player2_name}\n\n"
            f"У каждого игрока есть 3 попытки бросить кости. Удачи! 🎲"
        )
        
        for player_id in [room.player1_id, room.player2_id]:
            await bot.send_message(
                player_id,
                game_status,
                reply_markup=get_throw_dice_keyboard()
            )
            
    await GameStates.in_game.set()

async def throw_dice_callback(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    
    async with async_session() as session:
        query = select(Room).where(
            Room.is_active == True,
            or_(Room.player1_id == user_id, Room.player2_id == user_id)
        )
        result = await session.execute(query)
        room = result.scalar_one_or_none()
        
        if not room:
            await callback_query.answer("❌ Комната не найдена!", show_alert=True)
            return
        
        is_player1 = user_id == room.player1_id
        current_attempts = room.player1_attempts if is_player1 else room.player2_attempts
        
        if current_attempts >= 3:
            await callback_query.answer("❌ Вы уже использовали все попытки!", show_alert=True)
            return
        
        dice_value = roll_dice()
        if is_player1:
            room.player1_score += dice_value
            room.player1_attempts += 1
            player_name = room.player1_name
        else:
            room.player2_score += dice_value
            room.player2_attempts += 1
            player_name = room.player2_name
        
        await session.commit()
        
        game_status = (
            f"🎲 {player_name} выбросил: {dice_value}\n\n"
            f"Текущий счет:\n"
            f"{room.player1_name}: {room.player1_score} ({3 - room.player1_attempts} попыток осталось)\n"
            f"{room.player2_name}: {room.player2_score} ({3 - room.player2_attempts} попыток осталось)"
        )
        
        for player_id in [room.player1_id, room.player2_id]:
            await bot.send_message(
                player_id,
                game_status,
                reply_markup=get_throw_dice_keyboard()
            )
        
        if room.player1_attempts == 3 and room.player2_attempts == 3:
            if room.player1_score == room.player2_score:
                result_text = "🤝 Ничья!"
                final_message = (
                    f"🏆 Игра окончена!\n\n"
                    f"Финальный счет:\n"
                    f"{room.player1_name}: {room.player1_score}\n"
                    f"{room.player2_name}: {room.player2_score}\n\n"
                    f"{result_text}"
                )
                # Отправляем основное меню обоим игрокам
                for player_id in [room.player1_id, room.player2_id]:
                    await bot.send_message(player_id, final_message)
                    await bot.send_photo(
                        player_id,
                        'https://wallpaper-a-day.com/wp-content/uploads/2017/12/tumblr_p0eexyzxtl1u36eloo1_1280.jpg',
                        caption=(
                            "🎲 Добро пожаловать в игру в кости!\n\n"
                            "👨‍💻 Создатель - КИАНА\n"
                            "🌐 Форум - https://lolz.live/kqlol/\n"
                        ),
                        reply_markup=get_main_keyboard()
                    )
            else:
                winner_id = room.player1_id if room.player1_score > room.player2_score else room.player2_id
                loser_id = room.player2_id if room.player1_score > room.player2_score else room.player1_id
                winner_name = room.player1_name if room.player1_score > room.player2_score else room.player2_name
                
                final_message = (
                    f"🏆 Игра окончена!\n\n"
                    f"Финальный счет:\n"
                    f"{room.player1_name}: {room.player1_score}\n"
                    f"{room.player2_name}: {room.player2_score}\n\n"
                    f"{winner_name}, ты победил. Поздравляю с ней, удача с тобой!"
                )
                
                # Отправляем победителю гифку и меню
                await bot.send_message(winner_id, final_message)
                await bot.send_animation(winner_id, 'https://www.gifs.cc/congratulation/congrats-animation-smiley-2018.gif')
                await bot.send_photo(
                    winner_id,
                    'https://wallpaper-a-day.com/wp-content/uploads/2017/12/tumblr_p0eexyzxtl1u36eloo1_1280.jpg',
                    caption=(
                        "🎲 Добро пожаловать в игру в кости!\n\n"
                        "👨‍💻 Создатель - КИАНА\n"
                        "🌐 Форум - https://lolz.live/kqlol/\n"
                    ),
                    reply_markup=get_main_keyboard()
                )
                
                # Отправляем проигравшему сообщение и меню
                await bot.send_message(loser_id, final_message)
                await bot.send_photo(
                    loser_id,
                    'https://wallpaper-a-day.com/wp-content/uploads/2017/12/tumblr_p0eexyzxtl1u36eloo1_1280.jpg',
                    caption=(
                        "🎲 Добро пожаловать в игру в кости!\n\n"
                        "👨‍💻 Создатель - КИАНА\n"
                        "🌐 Форум - https://lolz.live/kqlol/\n"
                    ),
                    reply_markup=get_main_keyboard()
                )
            
            room.is_active = False
            await session.commit()
            await state.finish()



async def kick_player_callback(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    
    async with async_session() as session:
        query = select(Room).where(Room.player1_id == user_id, Room.is_active == True)
        result = await session.execute(query)
        room = result.scalar_one_or_none()
        
        if not room:
            await callback_query.answer("❌ Только создатель комнаты может выгонять игроков!", show_alert=True)
            return
        
        if room.player2_id:
            kicked_player_name = room.player2_name
            kicked_player_id = room.player2_id
            room.player2_id = None
            room.player2_name = None
            room.player2_score = 0
            room.player2_attempts = 0
            await session.commit()
            
            await callback_query.message.answer(f"👢 Игрок {kicked_player_name} был выгнан из комнаты!")
            await bot.send_message(kicked_player_id, "❌ Вы были выгнаны из комнаты!")
        else:
            await callback_query.answer("❌ В комнате нет второго игрока!", show_alert=True)
