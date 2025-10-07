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

# Хранилище pg_payment_id по пользователю
user_payments = {}

# ------------------- ХЭНДЛЕРЫ -------------------
def start(update, context):
    update.message.reply_text("Привет! Введите /pay чтобы начать оплату.")


def pay(update, context):
    chat_id = update.message.chat_id
    title = "FreedomPay Тест"
    description = "Оплата товара"
    payload = f"order_{chat_id}"
    provider_token = "6450350554:LIVE:548841"
    currency = "KGS"
    price = 30

    prices = [LabeledPrice("Товар", price * 100)]

    try:
        bot.send_invoice(chat_id, title, description, payload, provider_token, currency, prices)
        logging.info(f"Создан инвойс для {chat_id} | order_id={payload}")
    except Exception as e:
        logging.error(f"Ошибка при отправке инвойса: {e}")
        update.message.reply_text(f"Ошибка при отправке инвойса: {e}")


def precheckout_callback(update, context):
    query = update.pre_checkout_query
    if not query.invoice_payload.startswith("order_"):
        query.answer(ok=False, error_message="Некорректный заказ")
    else:
        query.answer(ok=True)


def successful_payment_callback(update, context):
    """Срабатывает после успешной оплаты в Telegram"""
    payment = update.message.successful_payment
    update.message.reply_text("✅ Оплата прошла успешно!")
    payment_data = payment.to_dict()

    logging.info("=== УСПЕШНЫЙ ПЛАТЁЖ (TELEGRAM) ===")
    for key, value in payment_data.items():
        logging.info(f"{key}: {value}")

    chat_id = update.message.chat_id
    order_id = payment_data.get("invoice_payload")

    # Проверяем, есть ли pg_payment_id от FreedomPay
    pg_payment_id = user_payments.get(chat_id)
    if not pg_payment_id:
        logging.warning(f"Для пользователя {chat_id} нет pg_payment_id — ждем callback от FreedomPay.")
        return

    # --- Запрашиваем статус у FreedomPay ---
    try:
        params = {
            "pg_merchant_id": MERCHANT_ID,
            "pg_payment_id": pg_payment_id,
            "pg_salt": "check123",
        }

        # создаём подпись
        sorted_keys = sorted(params.keys())
        sig_parts = ["get_status3.php"] + [str(params[k] or "") for k in sorted_keys] + [FREEDOMPAY_SECRET]
        sig_string = ";".join(sig_parts)
        pg_sig = hashlib.md5(sig_string.encode("utf-8")).hexdigest()
        params["pg_sig"] = pg_sig

        resp = requests.post("https://api.freedompay.kg/get_status3.php", data=params, timeout=5)
        resp_text = resp.text
        logging.info("=== ОТВЕТ FREEDOMPAY ===")
        logging.info(resp_text)

        # парсим XML
        root = ET.fromstring(resp_text)
        pg_status = root.findtext("pg_status")
        pg_result = root.findtext("pg_result")
        pg_amount = root.findtext("pg_amount")

        logging.info(f"FreedomPay → status={pg_status}, result={pg_result}, amount={pg_amount}")

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

    pg_payment_id = data.get("pg_payment_id")
    pg_order_id = data.get("pg_order_id")

    if pg_payment_id and pg_order_id:
        try:
            chat_id = int(pg_order_id.replace("order_", ""))
            user_payments[chat_id] = pg_payment_id
            logging.info(f"Связка: chat_id={chat_id} → pg_payment_id={pg_payment_id}")
        except Exception:
            pass

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
