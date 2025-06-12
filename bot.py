import os
import json
from flask import Flask, request
import requests

# === Конфигурация ===
BOT_TOKEN = "8057853656:AAEbcvA5wrfm980x3G1Ldn419MiAsoBQewQ"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

# === Обработка вебхука ===
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        send_message(chat_id, "Привет! Нажми кнопку ниже:", [
            [{"text": "Нажми меня", "callback_data": "pressed"}]
        ])
    elif "callback_query" in data:
        chat_id = data["callback_query"]["message"]["chat"]["id"]
        callback_id = data["callback_query"]["id"]
        send_callback_answer(callback_id, "Кнопка нажата!")
        send_message(chat_id, "Ты нажал на кнопку ✅")

    return "ok", 200

# === Утилиты ===
def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
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

# === Точка входа ===
if __name__ == "__main__":
    print("Запуск Flask-сервера...")
    app.run(host="0.0.0.0", port=5000)
