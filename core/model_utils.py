import random
import string

def generate_random_key():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(10))
