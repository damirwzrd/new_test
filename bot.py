import logging
import os
import threading
import hashlib
import requests
from flask import Flask, request, jsonify
from telegram import Bot, Update, LabeledPrice
from telegram.ext import Dispatcher, CommandHandler, PreCheckoutQueryHandler, MessageHandler, Filters

# ------------------- НАСТРОЙКА -------------------
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения!")

FREEDOMPAY_SECRET = os.getenv("FREEDOMPAY_SECRET")  # Добавь в Render → Environment
MERCHANT_ID = "548841"  # Твой ID мерчанта

bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=1, use_context=True)

# ------------------- ХЭНДЛЕРЫ -------------------
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

    result_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/freedompay/result"

    try:
        bot.send_invoice(
            chat_id, title, description, payload,
            provider_token, currency, prices
        )
        logging.info(f"Создан инвойс для {chat_id} | result_url={result_url}")
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
    """После успешной оплаты Telegram"""
    payment = update.message.successful_payment
    update.message.reply_text("✅ Оплата прошла успешно!")
    payment_data = payment.to_dict()

    logging.info("=== УСПЕШНЫЙ ПЛАТЁЖ (TELEGRAM) ===")
    for key, value in payment_data.items():
        logging.info(f"{key}: {value}")

    provider_payment_id = payment_data.get("provider_payment_charge_id")
    logging.info(f"FreedomPay pg_payment_id (из Telegram): {provider_payment_id}")

    # --- Запрос деталей платежа к FreedomPay ---
    try:
        params = {
            "pg_merchant_id": MERCHANT_ID,
            "pg_payment_id": provider_payment_id,
            "pg_salt": "check123"
        }

        sorted_params = sorted(params.items())
        sig_string = ";".join(str(v) for k, v in sorted_params)
        sig_string = f"get_payment;{sig_string};{FREEDOMPAY_SECRET}"
        pg_sig = hashlib.md5(sig_string.encode("utf-8")).hexdigest()
        params["pg_sig"] = pg_sig

        resp = requests.post("https://pay.freedompay.io/api/get_payment", data=params, timeout=5)
        resp_text = resp.text

        logging.info("=== ОТВЕТ FREEDOMPAY ===")
        logging.info(resp_text)

        # Отправим данные на webhook.site для наглядности
        try:
            requests.post(
                "https://webhook.site/3293b58b-a35a-4645-a175-2f5561ae0994",
                json={
                    "chat_id": update.message.chat_id,
                    "username": update.message.chat.username,
                    "payment_id": provider_payment_id,
                    "freedompay_response": resp_text
                },
                timeout=5
            )
        except Exception as e:
            logging.warning(f"Не удалось отправить лог на webhook.site: {e}")

    except Exception as e:
        logging.error(f"Ошибка при запросе get_payment: {e}")

# ------------------- CALLBACK FREEDOMPAY -------------------
@app.route("/freedompay/result", methods=["POST"])
def freedompay_result():
    """Коллбэк от FreedomPay"""
    data = request.form.to_dict() or request.get_json(force=True, silent=True) or {}
    logging.info("=== CALLBACK ОТ FREEDOMPAY ===")
    for k, v in data.items():
        logging.info(f"{k}: {v}")

    payment_id = data.get("pg_payment_id")
    order_id = data.get("pg_order_id")
    status = data.get("pg_result")

    logging.info(f"FreedomPay result: payment_id={payment_id}, order_id={order_id}, status={status}")

    return jsonify({"status": "ok"}), 200

# ------------------- ВЕБХУК TELEGRAM -------------------
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
