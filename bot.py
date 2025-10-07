import logging
import os
import threading
from flask import Flask, request, jsonify
from telegram import Bot, Update, LabeledPrice
from telegram.ext import Dispatcher, CommandHandler, PreCheckoutQueryHandler, MessageHandler, Filters

# ------------------- ЛОГИРОВАНИЕ -------------------
logging.basicConfig(level=logging.INFO)

# ------------------- НАСТРОЙКИ -------------------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения!")

bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=1, use_context=True)

# ------------------- КОМАНДЫ -------------------
def start(update, context):
    update.message.reply_text("Привет! Введите /pay чтобы начать оплату.")


def pay(update, context):
    """Создание инвойса Telegram"""
    chat_id = update.message.chat_id
    title = "FreedomPay Тест"
    description = "Оплата товара"
    payload = f"order_{chat_id}"
    provider_token = "6450350554:LIVE:548841"  # твой рабочий токен
    currency = "KGS"
    price = 30

    prices = [LabeledPrice("Товар", price * 100)]

    try:
        bot.send_invoice(chat_id, title, description, payload, provider_token, currency, prices)
        logging.info(f"Создан инвойс для {chat_id} | order_id={payload}")
    except Exception as e:
        logging.error(f"Ошибка при отправке инвойса: {e}")
        update.message.reply_text(f"Произошла ошибка при отправке инвойса: {e}")


def precheckout_callback(update, context):
    """Проверка перед оплатой"""
    query = update.pre_checkout_query
    if not query.invoice_payload.startswith("order_"):
        query.answer(ok=False, error_message="Некорректный заказ.")
    else:
        query.answer(ok=True)


def successful_payment_callback(update, context):
    """После успешной оплаты Telegram"""
    payment = update.message.successful_payment
    update.message.reply_text("✅ Оплата прошла успешно!")
    payment_data = payment.to_dict()

    logging.info("=== УСПЕШНЫЙ ПЛАТЁЖ (TELEGRAM) ===")
    for key, value in payment_data.items():
        logging.info(f"{key}: {value}")


# ------------------- ОБРАБОТКА CALLBACK FREEDOMPAY -------------------
@app.route("/freedompay/result", methods=["POST"])
def freedompay_result():
    """Коллбэк от FreedomPay (pg_result_url)"""
    data = request.form.to_dict() or request.get_json(force=True, silent=True) or {}
    logging.info("=== CALLBACK ОТ FREEDOMPAY ===")

    # Логируем все параметры
    for k, v in data.items():
        logging.info(f"{k}: {v}")

    # Извлекаем ключевые данные
    pg_payment_id = data.get("pg_payment_id")
    pg_order_id = data.get("pg_order_id")
    pg_result = data.get("pg_result")

    # Логируем основное
    logging.info(f"FreedomPay callback → payment_id={pg_payment_id}, order_id={pg_order_id}, result={pg_result}")

    # Можно также опционально уведомить пользователя
    try:
        if pg_result == "1" and pg_order_id and pg_order_id.startswith("order_"):
            chat_id = int(pg_order_id.replace("order_", ""))
            bot.send_message(chat_id, "✅ FreedomPay подтвердил оплату!")
    except Exception as e:
        logging.warning(f"Ошибка при уведомлении пользователя: {e}")

    # Возвращаем OK (обязательно!)
    return jsonify({"status": "ok"}), 200


# ------------------- TELEGRAM ВЕБХУК -------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"


@app.route("/")
def index():
    return "Бот работает!"


def set_webhook():
    render_url = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    if not render_url:
        logging.warning("RENDER_EXTERNAL_HOSTNAME не задан, вебхук не будет установлен.")
        return
    webhook_url = f"https://{render_url}/webhook"
    success = bot.set_webhook(webhook_url)
    logging.info(f"Вебхук установлен: {webhook_url} — {success}")


# ------------------- РЕГИСТРАЦИЯ -------------------
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("pay", pay))
dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))

# ------------------- ЗАПУСК -------------------
def run_bot():
    PORT = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    set_webhook()
    thread = threading.Thread(target=run_bot)
    thread.start()
