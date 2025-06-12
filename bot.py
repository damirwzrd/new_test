import os
import asyncio
import requests
from flask import Flask, request

from telegram import Update, LabeledPrice
from telegram.ext import Application, CommandHandler, ContextTypes

# Переменные окружения
TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_URL", "https://your-render-url.onrender.com")  # Заменить на свой URL
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Flask-приложение
app = Flask(__name__)

# Telegram Application
bot_app = Application.builder().token(TOKEN).build()

# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Нажми /pay чтобы оплатить.")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_invoice(
        title="Покупка",
        description="Тестовая покупка через FreedomPay",
        payload="test_payload",
        provider_token=PAYMENT_PROVIDER,
        currency="KGS",
        prices=[LabeledPrice("Товар", 10000)],
        start_parameter="test-payment",
    )

# Регистрируем команды
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("pay", pay))

# Webhook обработка
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot_app.bot)
        asyncio.run(bot_app.process_update(update))
    except RuntimeError as e:
        # asyncio.run нельзя вызывать если уже есть активный event loop (например, в Render)
        print("Ошибка asyncio.run:", e)
        asyncio.create_task(bot_app.process_update(update))
    except Exception as e:
        print("Ошибка при обработке вебхука:", e)
    return "ok"

# Установка webhook и запуск
async def run():
    response = requests.get(
        f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
    )
    print("Webhook setup response:", response.text)
    await bot_app.initialize()
    print("Bot initialized.")

# Flask run
if __name__ == "__main__":
    asyncio.run(run())
    app.run(host="0.0.0.0", port=10000)
