import asyncio
import logging
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import requests
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo('Asia/Tashkent')
except Exception:
    TZ = None

import config
from database import db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Проверяем токен
print(f"Bot token: {config.Config.BOT_TOKEN[:10]}...")

try:
    bot = Bot(token=config.Config.BOT_TOKEN)
    dp = Dispatcher()
except Exception as e:
    print(f"Ошибка создания бота: {e}")
    exit(1)

def get_main_keyboard():
    """Основная клавиатура"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍️ Заказать товары")],
            [KeyboardButton(text="📞 Контакты"), KeyboardButton(text="ℹ️ О магазине")],
        ],
        resize_keyboard=True
    )

def get_products_keyboard():
    """Клавиатура с товарами - используем простые callback_data"""
    keyboard = []
    items = list(config.Products.ITEMS.items())
    
    for i in range(0, len(items), 2):
        row = []
        for j in range(2):
            if i + j < len(items):
                item_id, product = items[i + j]
                # Используем простой номер вместо item_1, item_2
                button = InlineKeyboardButton(
                    text=f"{product['name']} - {product['price']}₽",
                    callback_data=f"prod_{i+j+1}"
                )
                row.append(button)
        keyboard.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cart_keyboard():
    """Клавиатура корзины"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить товары", callback_data="add_more")],
        [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout")],
        [InlineKeyboardButton(text="🗑️ Очистить корзину", callback_data="clear_cart")]
    ])

# Хранилище корзин пользователей
user_carts = {}

# Сопоставление номеров с товарами
PRODUCT_MAPPING = {
    "1": "item_1",
    "2": "item_2", 
    "3": "item_3",
    "4": "item_4",
    "5": "item_5"
}

@dp.message(Command("start"))
async def start_command(message: types.Message):
    user = message.from_user
    welcome_text = f"""
👋 Добро пожаловать в {config.Config.SHOP_NAME}, {user.first_name}!

🎂 Мы предлагаем свежие кондитерские изделия собственного производства.

💡 <b>Доступные команды:</b>
• 🛍️ Заказать товары - выбрать товары из каталога
• 📞 Контакты - связаться с нами
• ℹ️ О магазине - информация о магазине

Выберите действие или используйте кнопки ниже:
    """
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode='HTML')

@dp.message(F.text == "🛍️ Заказать товары")
async def show_products(message: types.Message):
    products_text = "🎂 <b>Наши кондитерские изделия:</b>\n\n"
    
    for num, (item_id, product) in enumerate(config.Products.ITEMS.items(), 1):
        products_text += f"{num}. {product['name']} - {product['price']}₽\n"
    
    products_text += "\nВыберите товар для заказа:"
    
    await message.answer(products_text, reply_markup=get_products_keyboard(), parse_mode='HTML')

@dp.message(F.text == "📞 Контакты")
async def show_contacts(message: types.Message):
    contacts_text = f"""
📞 <b>Наши контакты:</b>

🏪 Магазин: <b>{config.Config.SHOP_NAME}</b>
📍 Адрес: {config.Config.SHOP_ADDRESS}
📱 Телефон: {config.Config.SHOP_PHONE}

⏰ <b>Время работы:</b>
Пн-Вс: 9:00 - 21:00

🚚 <b>Доставка:</b>
• Бесплатная доставка от 1000₽
• Время доставки: 60-90 минут
    """
    await message.answer(contacts_text, parse_mode='HTML')

@dp.message(F.text == "ℹ️ О магазине")
async def about_shop(message: types.Message):
    about_text = f"""
🏪 <b>{config.Config.SHOP_NAME}</b>

Мы специализируемся на свежих кондитерских изделиях собственного производства.

✨ <b>Наши преимущества:</b>
• ✅ Свежая выпечка ежедневно
• 🚚 Быстрая доставка
• 💰 Доступные цены
• 📞 Круглосуточная поддержка

📍 {config.Config.SHOP_ADDRESS}
📱 {config.Config.SHOP_PHONE}
    """
    await message.answer(about_text, parse_mode='HTML')

@dp.callback_query(F.data.startswith("prod_"))
async def add_to_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    product_num = callback.data.split("_")[1]  # Получаем "1", "2" и т.д.
    
    print(f"Adding product number: {product_num}")  # Для отладки
    
    if product_num not in PRODUCT_MAPPING:
        await callback.answer("❌ Товар не найден!")
        return
    
    product_key = PRODUCT_MAPPING[product_num]
    product = config.Products.ITEMS[product_key]
    
    if user_id not in user_carts:
        user_carts[user_id] = {}
    
    cart = user_carts[user_id]
    
    # Используем product_key для хранения в корзине
    if product_key in cart:
        cart[product_key] += 1
    else:
        cart[product_key] = 1
    
    # Показываем корзину после добавления товара
    cart_text = "🛒 <b>Товар добавлен в корзину!</b>\n\n"
    total = 0
    
    for cart_product_key, quantity in cart.items():
        if cart_product_key in config.Products.ITEMS:
            product_item = config.Products.ITEMS[cart_product_key]
            item_total = product_item['price'] * quantity
            total += item_total
            cart_text += f"• {product_item['name']} - {quantity}шт. × {product_item['price']}₽ = {item_total}₽\n"
    
    cart_text += f"\n<b>Итого: {total}₽</b>"
    
    await callback.message.edit_text(
        cart_text,
        reply_markup=get_cart_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer(f"✅ {product['name']} добавлен в корзину!")

@dp.callback_query(F.data == "add_more")
async def add_more_products(callback: types.CallbackQuery):
    products_text = "🎂 <b>Выберите товары:</b>\n\n"
    
    for num, (item_id, product) in enumerate(config.Products.ITEMS.items(), 1):
        products_text += f"{num}. {product['name']} - {product['price']}₽\n"
    
    products_text += "\nВыберите товар для добавления:"
    
    await callback.message.edit_text(
        products_text,
        reply_markup=get_products_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()

@dp.callback_query(F.data == "clear_cart")
async def clear_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in user_carts:
        user_carts[user_id] = {}
    
    products_text = "🗑️ <b>Корзина очищена!</b>\n\n🎂 <b>Наши кондитерские изделия:</b>\n\n"
    
    for num, (item_id, product) in enumerate(config.Products.ITEMS.items(), 1):
        products_text += f"{num}. {product['name']} - {product['price']}₽\n"
    
    products_text += "\nВыберите товары для нового заказа:"
    
    await callback.message.edit_text(
        products_text,
        reply_markup=get_products_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()

@dp.callback_query(F.data == "checkout")
async def process_checkout(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, {})
    
    if not cart:
        await callback.answer("🛒 Корзина пуста!")
        return
    
    # Рассчитываем итого
    total = 0
    items_list = []
    for product_key, quantity in cart.items():
        if product_key in config.Products.ITEMS:
            product = config.Products.ITEMS[product_key]
            item_total = product['price'] * quantity
            total += item_total
            items_list.append({
                'id': product_key,
                'name': product['name'],
                'price': product['price'],
                'quantity': quantity,
                'total': item_total
            })
    
    if not items_list:
        await callback.answer("❌ Ошибка: товары не найдены!")
        return
    
    # Создаем заказ в базе данных
    order_id = db.add_order(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        items=items_list,
        total_amount=total
    )
    
    # Определяем время оформления заказа в Ташкенте для отображения
    if TZ is not None:
        now_display = datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')
    else:
        now_display = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Формируем текст заказа для канала
    order_text = f"""
🛒 <b>НОВЫЙ ЗАКАЗ #{order_id}</b>

👤 <b>Клиент:</b> {callback.from_user.first_name} (@{callback.from_user.username})
📱 <b>ID:</b> {callback.from_user.id}

<b>Товары:</b>
"""
    for item in items_list:
        order_text += f"• {item['name']} - {item['quantity']}шт. × {item['price']}₽ = {item['total']}₽\n"
    
    order_text += f"""
<b>💰 Итого: {total}₽</b>
⏰ <b>Время:</b> {now_display}

💡 <i>Для связи с клиентом: @{callback.from_user.username}</i>
    """
    
    # Клавиатура для админов
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖨️ Распечатать чек", callback_data=f"print_{order_id}")],
        [InlineKeyboardButton(text="✅ Подтвержден", callback_data=f"confirm_{order_id}"),
         InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{order_id}")]
    ])
    
    try:
        # Отправляем заказ в канал
        await bot.send_message(
            chat_id=config.Config.CHANNEL_ID,
            text=order_text,
            reply_markup=admin_keyboard,
            parse_mode='HTML'
        )
        
        # Очищаем корзину пользователя
        if user_id in user_carts:
            del user_carts[user_id]
        
        # Сообщение пользователю
        await callback.message.edit_text(
            f"✅ <b>Ваш заказ #{order_id} принят!</b>\n\n"
            f"<b>Сумма:</b> {total}₽\n"
            f"<b>Статус:</b> Ожидает подтверждения\n\n"
            f"Мы свяжемся с вами в ближайшее время для уточнения деталей доставки.\n\n"
            f"📞 {config.Config.SHOP_PHONE}",
            parse_mode='HTML'
        )
        
        logger.info(f"New order #{order_id} from user {callback.from_user.id}")
        
    except Exception as e:
        await callback.message.edit_text(
            "❌ <b>Ошибка при оформлении заказа</b>\n\n"
            "Пожалуйста, попробуйте позже или свяжитесь с нами напрямую.",
            parse_mode='HTML'
        )
        logger.error(f"Order error: {e}")
    
    await callback.answer()

@dp.callback_query(F.data.startswith("print_"))
async def process_print_order(callback: types.CallbackQuery):
    """Обработка печати чека администратором"""
    if callback.from_user.id not in config.Config.ADMIN_IDS:
        await callback.answer("❌ У вас нет прав для этого действия!", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[1])
    order = db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден!", show_alert=True)
        return
    
    # Формируем данные для чека
    receipt_data = {
        "order_id": order.id,
        "customer_name": order.first_name,
        "customer_username": f"@{order.username}" if order.username else "Не указан",
        "phone": order.phone or "Не указан",
        "address": order.address or "Самовывоз",
        "items": eval(order.items) if order.items else [],
        "total_amount": order.total_amount,
        # Форматируем дату заказа в Ташкенте для чека
        "date": (order.created_at.replace(tzinfo=ZoneInfo('UTC')).astimezone(TZ).strftime('%Y-%m-%d %H:%M:%S') if (order.created_at and TZ is not None) else (order.created_at.strftime('%Y-%m-%d %H:%M:%S') if order.created_at else None)),
        "shop_name": config.Config.SHOP_NAME,
        "shop_address": config.Config.SHOP_ADDRESS,
        "shop_phone": config.Config.SHOP_PHONE
    }
    
    try:
        # Отправляем на печать
        headers = {"X-API-Key": config.Config.API_SECRET_KEY}
        response = requests.post(
            f"{config.Config.PRINTER_API_URL}/print",
            json=receipt_data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            # Обновляем статус заказа
            db.update_order_status(order_id, "printed", printed_by=callback.from_user.id)
            
            # Обновляем сообщение в канале
            edited_text = callback.message.text + f"\n\n✅ Чек распечатан администратором"
            await callback.message.edit_text(
                edited_text,
                reply_markup=None,
                parse_mode='HTML'
            )
            await callback.answer("✅ Чек отправлен на печать!")
            
            logger.info(f"Receipt printed for order #{order_id}")
        else:
            await callback.answer("❌ Ошибка печати чека!", show_alert=True)
            logger.error(f"Print error for order #{order_id}: {response.text}")
            
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        logger.error(f"Print exception for order #{order_id}: {str(e)}")

@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_order_admin(callback: types.CallbackQuery):
    """Подтверждение заказа администратором"""
    if callback.from_user.id not in config.Config.ADMIN_IDS:
        await callback.answer("❌ У вас нет прав!", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[1])
    db.update_order_status(order_id, "confirmed")
    
    edited_text = callback.message.text + f"\n\n✅ Подтвержден администратором"
    await callback.message.edit_text(edited_text, parse_mode='HTML')
    await callback.answer("Заказ подтвержден!")

@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_order_admin(callback: types.CallbackQuery):
    """Отмена заказа администратором"""
    if callback.from_user.id not in config.Config.ADMIN_IDS:
        await callback.answer("❌ У вас нет прав!", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[1])
    db.update_order_status(order_id, "cancelled")
    
    edited_text = callback.message.text + f"\n\n❌ Отменен администратором"
    await callback.message.edit_text(edited_text, parse_mode='HTML')
    await callback.answer("Заказ отменен!")

@dp.message(Command("admin"))
async def admin_command(message: types.Message):
    """Команда для админов для просмотра статистики"""
    if message.from_user.id not in config.Config.ADMIN_IDS:
        await message.answer("❌ У вас нет прав доступа!")
        return
    
    stats_text = "👑 <b>Панель администратора</b>\n\n"
    stats_text += "Используйте кнопки в канале заказов для управления.\n\n"
    stats_text += f"🆔 Ваш ID: {message.from_user.id}\n"
    stats_text += f"🏪 Магазин: {config.Config.SHOP_NAME}\n"
    stats_text += f"📊 Канал заказов: {config.Config.CHANNEL_ID}"
    
    await message.answer(stats_text, parse_mode='HTML')

@dp.message(Command("cart"))
async def show_cart_command(message: types.Message):
    """Команда для просмотра корзины"""
    user_id = message.from_user.id
    cart = user_carts.get(user_id, {})
    
    if not cart:
        await message.answer("🛒 Ваша корзина пуста! Используйте кнопку '🛍️ Заказать товары'")
        return
    
    cart_text = "🛒 <b>Ваша корзина:</b>\n\n"
    total = 0
    
    for product_key, quantity in cart.items():
        if product_key in config.Products.ITEMS:
            product = config.Products.ITEMS[product_key]
            item_total = product['price'] * quantity
            total += item_total
            cart_text += f"• {product['name']} - {quantity}шт. × {product['price']}₽ = {item_total}₽\n"
    
    cart_text += f"\n<b>Итого: {total}₽</b>"
    
    await message.answer(cart_text, reply_markup=get_cart_keyboard(), parse_mode='HTML')

@dp.message(Command("debug"))
async def debug_command(message: types.Message):
    """Команда для отладки"""
    user_id = message.from_user.id
    cart = user_carts.get(user_id, {})
    
    debug_text = f"""
🔧 <b>Отладочная информация</b>

🆔 Ваш ID: {user_id}
🛒 Товаров в корзине: {len(cart)}
📋 Содержимое корзины: {cart}

📊 Доступные товары:
"""
    for key, product in config.Products.ITEMS.items():
        debug_text += f"• {key}: {product['name']} - {product['price']}₽\n"
    
    await message.answer(debug_text, parse_mode='HTML')

async def main():
    logger.info("Бот запускается...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    asyncio.run(main())