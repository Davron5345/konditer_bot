from flask import Flask, request, jsonify
from flask_httpauth import HTTPTokenAuth
from flask_cors import CORS
import socket
import json
import logging
from datetime import datetime
import config
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo('Asia/Tashkent')
except Exception:
    TZ = None

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('printer_server.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
auth = HTTPTokenAuth(scheme='Bearer')

@auth.verify_token
def verify_token(token):
    return token == config.Config.API_SECRET_KEY

class ReceiptPrinter:
    def __init__(self, host=None, port=None):
        self.host = host or config.Config.PRINTER_HOST
        self.port = port or config.Config.PRINTER_PORT
        self.encoding = 'cp866'  # Кодировка для русских символов
    
    def print_receipt(self, order_data):
        """Формирует и отправляет чек на принтер"""
        try:
            # Формируем текст чека
            receipt_bytes = self._format_receipt_bytes(order_data)
            
            # Подключаемся к принтеру
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10)
                sock.connect((self.host, self.port))
                sock.sendall(receipt_bytes)
                
            logger.info(f"Receipt printed successfully for order #{order_data['order_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Print error for order #{order_data.get('order_id', 'unknown')}: {str(e)}")
            return False
    
    def _format_receipt_bytes(self, order_data):
        """Форматирует чек в байты для ESC/POS принтера"""
        commands = []
        
        # Инициализация принтера
        commands.append(b'\x1B\x40')  # Initialize
        
        # Заголовок
        commands.append(b'\x1B\x21\x08')  # Bold ON
        commands.append(self._encode_text(f"{order_data['shop_name']}\n"))
        commands.append(b'\x1B\x21\x00')  # Bold OFF
        
        commands.append(self._encode_text(f"{order_data['shop_address']}\n"))
        commands.append(self._encode_text(f"Тел: {order_data['shop_phone']}\n"))
        commands.append(b'\x1D\x21\x00')  # Normal text
        
        # Разделитель
        commands.append(self._encode_text("=" * 32 + "\n"))
        
        # Информация о заказе
        commands.append(b'\x1B\x21\x08')  # Bold ON
        commands.append(self._encode_text(f"ЗАКАЗ #{order_data['order_id']}\n"))
        commands.append(b'\x1B\x21\x00')  # Bold OFF
        
        commands.append(self._encode_text(f"Дата: {order_data['date']}\n"))
        commands.append(self._encode_text(f"Кассир: Администратор\n"))
        commands.append(self._encode_text("=" * 32 + "\n"))
        
        # Клиент
        commands.append(b'\x1B\x21\x08')  # Bold ON
        commands.append(self._encode_text("КЛИЕНТ:\n"))
        commands.append(b'\x1B\x21\x00')  # Bold OFF
        commands.append(self._encode_text(f"Имя: {order_data['customer_name']}\n"))
        if order_data['customer_username'] != "Не указан":
            commands.append(self._encode_text(f"Telegram: {order_data['customer_username']}\n"))
        commands.append(self._encode_text(f"Телефон: {order_data['phone']}\n"))
        commands.append(self._encode_text(f"Адрес: {order_data['address']}\n"))
        commands.append(self._encode_text("=" * 32 + "\n"))
        
        # Товары
        commands.append(b'\x1B\x21\x08')  # Bold ON
        commands.append(self._encode_text("ТОВАРЫ:\n"))
        commands.append(b'\x1B\x21\x00')  # Bold OFF
        
        for item in order_data['items']:
            # Название товара
            name = item['name']
            if len(name) > 20:
                name = name[:17] + "..."
            commands.append(self._encode_text(f"{name}\n"))
            
            # Количество и цена
            line = f"{item['quantity']} x {item['price']:.2f} = {item['total']:.2f}\n"
            commands.append(self._encode_text(line))
            
            commands.append(self._encode_text("-" * 20 + "\n"))
        
        # Итого
        commands.append(b'\x1B\x21\x08')  # Bold ON
        commands.append(self._encode_text(f"ИТОГО: {order_data['total_amount']:.2f}₽\n"))
        commands.append(b'\x1B\x21\x00')  # Bold OFF
        
        commands.append(self._encode_text("=" * 32 + "\n"))
        
        # Подвал
        commands.append(self._encode_text("Спасибо за покупку!\n"))
        commands.append(self._encode_text("Ждем вас снова!\n"))
        
        # Разрыв бумаги
        commands.append(b'\n\n\n\n\x1D\x56\x00')  # Partial cut
        
        return b''.join(commands)
    
    def _encode_text(self, text):
        """Кодирует текст в нужную кодировку"""
        return text.encode(self.encoding, errors='replace')

printer = ReceiptPrinter()

@app.route('/print', methods=['POST'])
@auth.login_required
def print_receipt():
    try:
        if not request.json:
            return jsonify({"status": "error", "message": "No JSON data provided"}), 400
        
        order_data = request.json
        
        # Валидация обязательных полей
        required_fields = ['order_id', 'customer_name', 'items', 'total_amount']
        for field in required_fields:
            if field not in order_data:
                return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400
        
        if printer.print_receipt(order_data):
            logger.info(f"Successfully printed receipt for order #{order_data['order_id']}")
            return jsonify({
                "status": "success", 
                "message": "Чек отправлен на печать",
                "order_id": order_data['order_id']
            })
        else:
            logger.error(f"Failed to print receipt for order #{order_data['order_id']}")
            return jsonify({"status": "error", "message": "Ошибка печати"}), 500
            
    except Exception as e:
        logger.error(f"Print route error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка статуса принтера"""
    try:
        # Пытаемся подключиться к принтеру
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.connect((config.Config.PRINTER_HOST, config.Config.PRINTER_PORT))
        
        return jsonify({
            "status": "ok", 
            "printer": "connected",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "printer": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 503

@app.route('/test-print', methods=['POST'])
@auth.login_required
def test_print():
    """Тестовая печать"""
    try:
        test_data = {
            "order_id": 999,
            "customer_name": "Тестовый Клиент",
            "customer_username": "@testuser",
            "phone": "+7 (999) 123-45-67",
            "address": "Тестовый адрес",
            "items": [
                {"name": "Тестовый товар 1", "price": 1000, "quantity": 2, "total": 2000},
                {"name": "Тестовый товар 2", "price": 500, "quantity": 1, "total": 500}
            ],
            "total_amount": 2500,
            "date": (datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S') if TZ is not None else datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            "shop_name": config.Config.SHOP_NAME,
            "shop_address": config.Config.SHOP_ADDRESS,
            "shop_phone": config.Config.SHOP_PHONE
        }
        
        if printer.print_receipt(test_data):
            return jsonify({"status": "success", "message": "Тестовый чек распечатан"})
        else:
            return jsonify({"status": "error", "message": "Ошибка тестовой печати"}), 500
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting Printer Server...")
    app.run(host='0.0.0.0', port=5000, debug=False)