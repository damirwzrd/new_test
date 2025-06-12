import os
import json
from flask import Flask, request
import requests

# === Конфигурация ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN")

WEBHOOK_PATH = f"/{BOT_TOKEN}"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    data = request.get_json()

    # Сообщение от пользователя
    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]

        # Уведомление о платеже
        if "successful_payment" in message:
            send_message(chat_id, "✅ Платёж прошёл успешно!")
        else:
            send_message(chat_id, "Привет! Нажми кнопку для оплаты:", [
                [{"text": "Оплатить 💳", "callback_data": "pay"}]
            ])

    # Нажатие на inline-кнопку
    elif "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        callback_id = callback["id"]
        callback_data = callback["data"]

        send_callback_answer(callback_id, "Обрабатываю...")

        if callback_data == "pay":
            send_invoice(chat_id)

    # Чекаут перед оплатой
    elif "pre_checkout_query" in data:
        approve_checkout(data["pre_checkout_query"]["id"])

    return "ok", 200

# === Оплата ===
def send_invoice(chat_id):
    payload = {
        "chat_id": chat_id,
        "title": "Оплата подписки",
        "description": "1 месяц доступа",
        "payload": "sub_monthly_001",
        "provider_token": PROVIDER_TOKEN,
        "currency": "KZT",
        "prices": [{"label": "Подписка", "amount": 10000}],  # 100 тенге
        "start_parameter": "pay-subscription",
    }
    r = requests.post(f"{TELEGRAM_API_URL}/sendInvoice", json=payload)
    print("sendInvoice:", r.status_code, r.text)

def approve_checkout(query_id):
    payload = {
        "pre_checkout_query_id": query_id,
        "ok": True
    }
    requests.post(f"{TELEGRAM_API_URL}/answerPreCheckoutQuery", json=payload)

# === Утилиты ===
def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps({"inline_keyboard": reply_markup})
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

def send_callback_answer(callback_query_id, text):
    payload = {
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": False
    }
    requests.post(f"{TELEGRAM_API_URL}/answerCallbackQuery", json=payload)

# === Запуск ===
if __name__ == "__main__":
    print("Запуск Flask-сервера...")
    app.run(host="0.0.0.0", port=5000)
