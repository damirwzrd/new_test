import logging
import os
import threading
import hashlib
import requests
import xml.etree.ElementTree as ET
from flask import Flask, request, jsonify
from telegram import Bot, Update, LabeledPrice
from telegram.ext import Dispatcher, CommandHandler, PreCheckoutQueryHandler, MessageHandler, Filters

# ------------------- НАСТРОЙКА -------------------
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения!")

FREEDOMPAY_SECRET = os.getenv("FREEDOMPAY_SECRET")
MERCHANT_ID = os.getenv("FREEDOMPAY_MERCHANT_ID", "548841")

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

    try:
        bot.send_invoice(
            chat_id, title, description, payload,
            provider_token, currency, prices
        )
        logging.info(f"Создан инвойс для {chat_id}")
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
    """После успешной оплаты в Telegram"""
    payment = update.message.successful_payment
    update.message.reply_text("✅ Оплата прошла успешно!")
    payment_data = payment.to_dict()

    logging.info("=== УСПЕШНЫЙ ПЛАТЁЖ (TELEGRAM) ===")
    for key, value in payment_data.items():
        logging.info(f"{key}: {value}")

    provider_payment_id = payment_data.get("provider_payment_charge_id")
    if not provider_payment_id:
        logging.warning("provider_payment_charge_id не найден!")
        return

    # --- Запрашиваем статус у FreedomPay ---
    try:
        params = {
            "pg_merchant_id": MERCHANT_ID,
            "pg_payment_id": provider_payment_id,
            "pg_salt": "check123",
        }

        # создаём подпись
        sorted_keys = sorted(params.keys())
        sig_parts = ["get_status3.php"] + [str(params[k]) for k in sorted_keys] + [FREEDOMPAY_SECRET]
        sig_string = ";".join(sig_parts)
        pg_sig = hashlib.md5(sig_string.encode("utf-8")).hexdigest()
        params["pg_sig"] = pg_sig


        # отправляем запрос
        resp = requests.post("https://api.freedompay.kg/get_status3.php", data=params, timeout=5)
        resp_text = resp.text
        logging.info("=== ОТВЕТ FREEDOMPAY ===")
        logging.info(resp_text)

        # парсим XML
        try:
            root = ET.fromstring(resp_text)
            pg_status = root.findtext("pg_status")
            pg_payment_id = root.findtext("pg_payment_id")
            pg_order_id = root.findtext("pg_order_id")
            pg_amount = root.findtext("pg_amount")
            pg_result = root.findtext("pg_result")

            logging.info(f"FreedomPay → status={pg_status}, payment_id={pg_payment_id}, order_id={pg_order_id}, amount={pg_amount}, result={pg_result}")

            # отправим эти данные на webhook.site
            requests.post("https://webhook.site/0460c9db-b629-49f3-90eb-e9ed90b73be8", json={
                "chat_id": update.message.chat_id,
                "username": update.message.chat.username,
                "pg_payment_id": pg_payment_id,
                "pg_order_id": pg_order_id,
                "pg_amount": pg_amount,
                "pg_result": pg_result,
                "pg_status": pg_status
            }, timeout=5)

        except Exception as e:
            logging.error(f"Ошибка при парсинге XML: {e}")

    except Exception as e:
        logging.error(f"Ошибка при запросе get_status3.php: {e}")


# ------------------- ОБРАБОТКА FREEDOMPAY CALLBACK -------------------
@app.route("/freedompay/result", methods=["POST"])
def freedompay_result():
    """Коллбэк от FreedomPay (pg_result_url)"""
    data = request.form.to_dict() or request.get_json(force=True, silent=True) or {}
    logging.info("=== CALLBACK ОТ FREEDOMPAY ===")
    for k, v in data.items():
        logging.info(f"{k}: {v}")
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
