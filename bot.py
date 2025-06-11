from flask import Flask, request
from telegram import Update, LabeledPrice
from telegram.ext import Application, CommandHandler, ContextTypes
import os

TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER_TOKEN")

app = Flask(__name__)
bot_app = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Нажми /pay чтобы оплатить.")

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

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("pay", pay))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put_nowait(update)
    return "ok"

if __name__ == "__main__":
    bot_app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=f"https://your-render-url.onrender.com/{TOKEN}"
    )
