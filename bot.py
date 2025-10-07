import logging
import os
import threading
from flask import Flask, request
from telegram import Bot, Update, LabeledPrice
from telegram.ext import Dispatcher, CommandHandler, PreCheckoutQueryHandler, MessageHandler, Filters

# Логирование
logging.basicConfig(level=logging.INFO)

# Получаем токен из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения!")

# Инициализация бота
bot = Bot(token=TOKEN)

# Flask-приложение
app = Flask(__name__)

# Диспетчер для обработки апдейтов
dispatcher = Dispatcher(bot, None, workers=1, use_context=True)

# ---------- Хэндлеры команд ----------
def start(update, context):
    update.message.reply_text("Привет! Введите /pay чтобы начать оплату.")

def pay(update, context):
    chat_id = update.message.chat_id
    title = "FreedomPay Тест"
    description = "Оплата товара"
    payload = "custom_payload"
    provider_token = "6450350554:LIVE:548841"
    currency = "KGS"
    price = 30

    prices = [LabeledPrice("Товар", price * 100)]

    try:
        bot.send_invoice(
            chat_id, title, description, payload,
            provider_token, currency, prices
        )
    except Exception as e:
        logging.error(f"Ошибка при отправке инвойса: {e}")
        update.message.reply_text(f"Произошла ошибка при отправке инвойса: {e}")

def precheckout_callback(update, context):
    query = update.pre_checkout_query
    if query.invoice_payload != "custom_payload":
        query.answer(ok=False, error_message="Что-то пошло не так...")
    else:
        query.answer(ok=True)

def successful_payment_callback(update, context):
    payment = update.message.successful_payment

    # Ответ пользователю
    update.message.reply_text("✅ Оплата прошла успешно! Спасибо 🙌")

    # Преобразуем данные в словарь
    payment_data = payment.to_dict()

    # Логируем все данные платежа в Render Logs
    logging.info("=== УСПЕШНЫЙ ПЛАТЁЖ ===")
    for key, value in payment_data.items():
        logging.info(f"{key}: {value}")

    # Логируем пользователя
    logging.info(f"Пользователь: {update.message.chat.username} (ID: {update.message.chat_id})")

    # Отправляем данные о платеже на webhook.site
    try:
        import requests
        response = requests.post(
            "https://webhook.site/3293b58b-a35a-4645-a175-2f5561ae0994",
            json={
                "chat_id": update.message.chat_id,
                "username": update.message.chat.username,
                "payment": payment_data
            },
            timeout=5
        )
        logging.info(f"Коллбэк отправлен: {response.status_code}")
    except Exception as e:
        logging.error(f"Ошибка при отправке данных коллбэка: {e}")

# Регистрируем хэндлеры
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('pay', pay))
dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))

# ---------- Вебхук ----------
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok'

@app.route('/')
def index():
    return 'Бот работает!'

def set_webhook():
    render_url = os.getenv('RENDER_EXTERNAL_HOSTNAME')
    if not render_url:
        logging.warning("RENDER_EXTERNAL_HOSTNAME не задан, вебхук не будет установлен.")
        return
    webhook_url = f"https://{render_url}/webhook"
    success = bot.set_webhook(webhook_url)
    logging.info(f"Вебхук установлен: {webhook_url} — {success}")

# ---------- Запуск ----------
def run_bot():
    PORT = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=PORT)

if __name__ == "__main__":
    set_webhook()  # Устанавливаем вебхук один раз при старте
    thread = threading.Thread(target=run_bot)
    thread.start()
