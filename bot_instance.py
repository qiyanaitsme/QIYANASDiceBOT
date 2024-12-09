import json
from aiogram import Bot

with open('config.json') as f:
    config = json.load(f)

bot = Bot(token=config['bot_token'])
