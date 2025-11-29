import os
import asyncio
from threading import Thread

# Import the Flask admin app and the bot module
from admin_panel import app as admin_app
import bot


def run_flask():
    port = int(os.getenv('PORT', '8080'))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    # When running inside a thread, disable reloader
    admin_app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)


if __name__ == '__main__':
    # Запускаем админ-панель в отдельном потоке
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Запускаем aiogram polling в основном потоке (event loop)
    try:
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        pass
