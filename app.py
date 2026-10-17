import os
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder=None)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/order")
def order():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    if not name or not phone:
        return jsonify(error="Укажите имя и телефон для связи."), 400

    token = os.environ.get("BOT_TOKEN", "").strip()
    chat_id = os.environ.get("ADMIN_CHAT_ID", "").strip()
    if not token or not chat_id:
        app.logger.error("BOT_TOKEN or ADMIN_CHAT_ID is not configured")
        return jsonify(error="Сервис временно не настроен."), 503

    fields = [
        ("Имя", name),
        ("Телефон для связи", phone),
        ("Дата мероприятия", data.get("date") or "не указана"),
        ("Количество гостей", data.get("guests") or "не указано"),
        ("Заказ", data.get("product") or "не указано"),
        ("Адрес доставки в Симферополе", data.get("address") or "не указан"),
        ("Комментарий", data.get("comment") or "нет"),
    ]
    message = "🎉 Новая заявка — Sofia Sweet Moments\n\n" + "\n".join(
        f"{label}: {str(value)[:1500]}" for label, value in fields
    )
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=12,
        )
        result = resp.json()
        if not resp.ok or not result.get("ok"):
            app.logger.error("Telegram sendMessage failed: HTTP %s", resp.status_code)
            return jsonify(error="Не удалось передать заявку в Telegram."), 502
    except requests.RequestException:
        app.logger.exception("Telegram request failed")
        return jsonify(error="Временно не удалось связаться с Telegram."), 502

    return jsonify(ok=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
