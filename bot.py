from flask import Flask, request
from telegram import Update, LabeledPrice
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
import os

TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_URL", "https://new-test-axkz.onrender.com")  # your Render URL

app = Flask(__name__)

# Создаем Telegram Application (без запуска сервера)
bot_app = Application.builder().token(TOKEN).build()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Нажми /pay чтобы оплатить.")

# Команда /pay
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_invoice(
        title="Покупка",
        description="Тестовая покупка через FreedomPay",
        payload="test_payload",
        provider_token=PAYMENT_PROVIDER,
        currency="KGS",
        prices=[LabeledPrice("Товар", 10000)],  # 100.00 сом
        start_parameter="test-payment",
    )

# Регистрируем команды
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("pay", pay))

# Webhook endpoint для Telegram
@app.route(f"/{TOKEN}", methods=["POST"])
async def telegram_webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return "ok"

# Render требует app.run() — без run_webhook!
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot_app.initialize())

    # Установим webhook (можно один раз)
    import requests
    webhook_url = f"{WEBHOOK_HOST}/{TOKEN}"
    requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}")

    app.run(host="0.0.0.0", port=10000)
