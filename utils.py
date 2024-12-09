import random
import string

def generate_room_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def roll_dice():
    return random.randint(1, 6)