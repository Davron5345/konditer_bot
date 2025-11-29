from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import config

Base = declarative_base()

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    phone = Column(String(20))
    address = Column(Text)
    items = Column(Text, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String(20), default='new')
    created_at = Column(DateTime, default=datetime.utcnow)
    printed_at = Column(DateTime)
    printed_by = Column(Integer)

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    price = Column(Float, nullable=False)
    photo_url = Column(String(500))
    category = Column(String(100))
    description = Column(Text)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Database:
    def __init__(self, db_url=None):
        self.engine = create_engine(db_url or config.Config.DATABASE_URL)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        # Экспортируем модели как атрибуты для удобства вызова в других местах
        self.Order = Order
        self.Product = Product
    
    # Методы для заказов
    def add_order(self, user_id, username, first_name, items, total_amount, phone=None, address=None):
        order = Order(
            user_id=user_id,
            username=username,
            first_name=first_name,
            phone=phone,
            address=address,
            items=str(items),
            total_amount=total_amount
        )
        self.session.add(order)
        self.session.commit()
        return order.id
    
    def get_order(self, order_id):
        return self.session.query(Order).filter(Order.id == order_id).first()
    
    def update_order_status(self, order_id, status, printed_by=None):
        order = self.get_order(order_id)
        if order:
            order.status = status
            if status == 'printed':
                order.printed_at = datetime.utcnow()
                order.printed_by = printed_by
            self.session.commit()
            return True
        return False
    
    def get_orders(self, status=None, limit=100):
        query = self.session.query(Order).order_by(Order.created_at.desc())
        if status:
            query = query.filter(Order.status == status)
        return query.limit(limit).all()

    def get_today_stats(self):
        """Возвращает простую статистику по заказам за текущие сутки (UTC):
        {'orders': int, 'revenue': float, 'by_status': {status: count}}
        """
        from datetime import datetime, timedelta, timezone
        try:
            # Используем стандартную зону Asia/Tashkent
            from zoneinfo import ZoneInfo
            tz = ZoneInfo('Asia/Tashkent')
        except Exception:
            # Фоллбек: если zoneinfo недоступен, используем смещение +5
            tz = None

        if tz is not None:
            # Определяем начало текущих суток в Ташкенте, затем переводим в UTC
            now_tz = datetime.now(tz)
            start_of_day_tz = now_tz.replace(hour=0, minute=0, second=0, microsecond=0)
            start_of_day_utc = start_of_day_tz.astimezone(timezone.utc).replace(tzinfo=None)
            orders = self.session.query(Order).filter(Order.created_at >= start_of_day_utc).all()
        else:
            # Если zoneinfo недоступен, считаем по UTC, но с поправкой +5 часов
            # Начало дня в Ташкенте соответствует UTC-5 часов назад
            now_utc = datetime.utcnow()
            # Считаем начало дня Ташкента в UTC
            start_of_day = (now_utc + timedelta(hours=5)).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=5)
            orders = self.session.query(Order).filter(Order.created_at >= start_of_day).all()

        total_orders = len(orders)
        total_revenue = sum((o.total_amount or 0) for o in orders)

        status_counts = {}
        for o in orders:
            status_counts[o.status] = status_counts.get(o.status, 0) + 1

        return {
            'orders': total_orders,
            'revenue': total_revenue,
            'by_status': status_counts
        }
    
    # Методы для товаров
    def add_product(self, name, price, photo_url=None, category=None, description=None):
        product = Product(
            name=name,
            price=price,
            photo_url=photo_url,
            category=category,
            description=description
        )
        self.session.add(product)
        self.session.commit()
        return product.id
    
    def get_product(self, product_id):
        return self.session.query(Product).filter(Product.id == product_id).first()
    
    def get_all_products(self, available_only=True):
        query = self.session.query(Product).order_by(Product.created_at.desc())
        if available_only:
            query = query.filter(Product.is_available == True)
        return query.all()
    
    def update_product(self, product_id, **kwargs):
        product = self.get_product(product_id)
        if product:
            for key, value in kwargs.items():
                if hasattr(product, key):
                    setattr(product, key, value)
            product.updated_at = datetime.utcnow()
            self.session.commit()
            return True
        return False
    
    def delete_product(self, product_id):
        product = self.get_product(product_id)
        if product:
            self.session.delete(product)
            self.session.commit()
            return True
        return False
    
    def toggle_product_availability(self, product_id):
        product = self.get_product(product_id)
        if product:
            product.is_available = not product.is_available
            product.updated_at = datetime.utcnow()
            self.session.commit()
            return True
        return False

# Инициализация базы данных
db = Database()