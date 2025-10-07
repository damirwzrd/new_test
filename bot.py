import logging
import os
import threading
from flask import Flask, request
from telegram import Bot, Update, LabeledPrice
from telegram.ext import (
    Dispatcher, CommandHandler, MessageHandler, Filters,
    PreCheckoutQueryHandler, ConversationHandler
)
import requests

# Логирование
logging.basicConfig(level=logging.INFO)

# Получаем токен из окружения
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не задан в окружении!")

# Инициализация бота и Flask
bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=1, use_context=True)

# Состояния диалога
ENTER_AMOUNT = 1

# ---------- Хэндлеры Telegram ----------

def start(update, context):
    update.message.reply_text("Привет! Отправь /pay чтобы оплатить произвольную сумму.")

def pay(update, context):
    update.message.reply_text("💰 Введите сумму оплаты (не меньше 10 сом):")
    return ENTER_AMOUNT

def handle_amount(update, context):
    try:
        amount = int(update.message.text)
        if amount < 10:
            update.message.reply_text("❗ Минимальная сумма — 10 сом. Попробуйте снова.")
            return ENTER_AMOUNT

        chat_id = update.message.chat_id
        title = "FreedomPay Тест"
        description = f"Оплата {amount} сом"
        payload = f"order_{chat_id}"
        provider_token = "6450350554:LIVE:548841"
        currency = "KGS"

        prices = [LabeledPrice("Оплата через Telegram", amount * 100)]

        bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token=provider_token,
            currency=currency,
            prices=prices
        )

        return ConversationHandler.END

    except ValueError:
        update.message.reply_text("Введите сумму числом, например: 100")
        return ENTER_AMOUNT
    except Exception as e:
        logging.error(f"Ошибка при создании инвойса: {e}")
        update.message.reply_text(f"Ошибка при создании инвойса: {e}")
        return ConversationHandler.END


def precheckout_callback(update, context):
    query = update.pre_checkout_query
    if not query.invoice_payload.startswith("order_"):
        query.answer(ok=False, error_message="Ошибка проверки платежа.")
    else:
        query.answer(ok=True)

def successful_payment_callback(update, context):
    payment = update.message.successful_payment
    update.message.reply_text("✅ Оплата прошла успешно! Спасибо 🙌")

    payment_data = payment.to_dict()
    logging.info("=== УСПЕШНЫЙ ПЛАТЁЖ (TELEGRAM) ===")
    for key, value in payment_data.items():
        logging.info(f"{key}: {value}")

    try:
        response = requests.post(
            "https://webhook.site/0460c9db-b629-49f3-90eb-e9ed90b73be8",
            json={
                "chat_id": update.message.chat_id,
                "username": update.message.chat.username,
                "payment": payment_data
            },
            timeout=5
        )
        logging.info(f"Webhook отправлен: {response.status_code}")
    except Exception as e:
        logging.error(f"Ошибка при отправке webhook: {e}")

# ---------- Новый маршрут: FreedomPay pg_result_url ----------

@app.route('/freedompay/result', methods=['POST'])
def freedompay_result():
    """
    Этот endpoint вызывается FreedomPay после оплаты.
    Он должен возвращать HTTP 200, иначе FreedomPay будет пытаться повторно.
    """
    data = request.form.to_dict()
    logging.info("=== CALLBACK от FreedomPay (pg_result_url) ===")
    for key, value in data.items():
        logging.info(f"{key}: {value}")

    # Проверим статус
    if data.get('pg_result') == '1':
        logging.info(f"✅ Платёж успешен! ORDER_ID: {data.get('pg_order_id')} | PAYMENT_ID: {data.get('pg_payment_id')}")
    else:
        logging.warning(f"❌ Ошибка платежа! ORDER_ID: {data.get('pg_order_id')} | Статус: {data.get('pg_result')}")

    # Всегда отвечаем 200 OK
    return "OK", 200


# ---------- Регистрируем хэндлеры Telegram ----------

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('pay', pay)],
    states={ENTER_AMOUNT: [MessageHandler(Filters.text & ~Filters.command, handle_amount)]},
    fallbacks=[CommandHandler('pay', pay)]
)

dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(conv_handler)
dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))

# ---------- Flask webhook для Telegram ----------

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

def run_bot():
    PORT = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=PORT)

if __name__ == "__main__":
    set_webhook()
    thread = threading.Thread(target=run_bot)
    thread.start()
