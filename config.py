import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel_id")
    ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "123456789").split(',')] if os.getenv("ADMIN_IDS") else [123456789]
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///orders.db")
    
    # Printer
    PRINTER_API_URL = os.getenv("PRINTER_API_URL", "http://localhost:5000")
    PRINTER_HOST = os.getenv("PRINTER_HOST", "localhost")
    PRINTER_PORT = int(os.getenv("PRINTER_PORT", "9100"))
    
    # Security
    API_SECRET_KEY = os.getenv("API_SECRET_KEY", "your-secret-key-change-this-in-production")
    
    # Shop
    SHOP_NAME = os.getenv("SHOP_NAME", "Кондитерская Сладости")
    SHOP_ADDRESS = os.getenv("SHOP_ADDRESS", "ул. Кондитерская, 15")
    SHOP_PHONE = os.getenv("SHOP_PHONE", "+7 (999) 123-45-67")


class Products:
    """Каталог товаров кондитерской"""
    ITEMS = {
        'item_1': {
            'name': 'Торт "Наполеон"',
            'price': 350
        },
        'item_2': {
            'name': 'Эклер шоколадный',
            'price': 120
        },
        'item_3': {
            'name': 'Пирожное "Картошка"',
            'price': 80
        },
        'item_4': {
            'name': 'Чизкейк классический',
            'price': 280
        },
        'item_5': {
            'name': 'Макарон ассорти (5 шт)',
            'price': 450
        }
    }