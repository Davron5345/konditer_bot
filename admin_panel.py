import os
from flask import Flask, render_template, jsonify, request
import json
from datetime import datetime, timedelta
from database import db
import config
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo('Asia/Tashkent')
except Exception:
    TZ = None

app = Flask(__name__)

@app.route('/admin')
def admin_dashboard():
    return render_template('admin.html')

@app.route('/api/orders')
def get_orders():
    status = request.args.get('status')
    limit = int(request.args.get('limit', 50))
    
    orders = db.get_orders(status=status, limit=limit)
    
    orders_data = []
    for order in orders:
        # Приводим время к часовому поясу Ташкента для отображения
        created_at_display = None
        printed_at_display = None
        if order.created_at:
            if TZ is not None:
                # order.created_at хранится в UTC (naive) — делаем aware UTC, затем конвертируем
                created_utc = order.created_at.replace(tzinfo=ZoneInfo('UTC'))
                created_at_display = created_utc.astimezone(TZ).strftime('%Y-%m-%d %H:%M:%S')
            else:
                created_at_display = order.created_at.strftime('%Y-%m-%d %H:%M:%S')

        if order.printed_at:
            if TZ is not None:
                printed_utc = order.printed_at.replace(tzinfo=ZoneInfo('UTC'))
                printed_at_display = printed_utc.astimezone(TZ).strftime('%Y-%m-%d %H:%M:%S')
            else:
                printed_at_display = order.printed_at.strftime('%Y-%m-%d %H:%M:%S')

        orders_data.append({
            'id': order.id,
            'customer': f"{order.first_name} (@{order.username})" if order.username else order.first_name,
            'phone': order.phone,
            'address': order.address,
            'items': eval(order.items) if order.items else [],
            'total_amount': order.total_amount,
            'status': order.status,
            'created_at': created_at_display,
            'printed_at': printed_at_display
        })
    
    return jsonify(orders_data)

@app.route('/api/stats')
def get_stats():
    # Статистика за сегодня
    today_stats = db.get_today_stats()
    
    # Статистика за неделю
    week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_orders = db.session.query(db.Order).filter(
        db.Order.created_at >= week_ago
    ).all()
    
    weekly_revenue = sum(order.total_amount for order in weekly_orders)
    
    # Статистика по статусам
    status_stats = {}
    all_orders = db.get_orders(limit=1000)
    for order in all_orders:
        status_stats[order.status] = status_stats.get(order.status, 0) + 1
    
    return jsonify({
        'today': today_stats,
        'weekly': {
            'orders': len(weekly_orders),
            'revenue': weekly_revenue
        },
        'statuses': status_stats
    })

@app.route('/api/order/<int:order_id>/status', methods=['POST'])
def update_order_status(order_id):
    data = request.json
    new_status = data.get('status')
    
    if new_status in ['new', 'confirmed', 'printed', 'cancelled']:
        success = db.update_order_status(order_id, new_status)
        if success:
            return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error'}), 400

if __name__ == '__main__':
    port = int(os.getenv('PORT', '8080'))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    # use_reloader=False because we run Flask inside a thread when using start.py
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)