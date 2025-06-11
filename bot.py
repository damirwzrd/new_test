from flask import Flask, request
from telegram import Update, LabeledPrice
from telegram.ext import Application, CommandHandler, ContextTypes
import os

# Загружаем переменные окружения
TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_URL", "https://new-test-axkz.onrender.com")  # Добавлено

# Инициализация Flask и Telegram Application
app = Flask(__name__)
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

# Webhook-обработчик для Telegram
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put_nowait(update)
    return "ok"

# Запуск вебхука
if __name__ == "__main__":
    bot_app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=f"{WEBHOOK_HOST}/{TOKEN}"  # Используем переменную или дефолтный URL
    )
