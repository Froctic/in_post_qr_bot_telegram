from flask import Flask, request
import qrcode
from io import BytesIO
import requests
import os

TOKEN = os.environ.get('7611903971:AAGJ9MWOcx7YLcMT3tP8IlauvBp0qrIcw7U')  # В Render лучше хранить токен в переменной окружения
API_URL = f'https://api.telegram.org/bot7611903971:AAGJ9MWOcx7YLcMT3tP8IlauvBp0qrIcw7U/'

app = Flask(__name__)
user_data = {}  # user_id: {'phone': '...', 'step': 'wait_code'}

def send_message(chat_id, text):
    requests.post(API_URL + 'sendMessage', data={
        'chat_id': chat_id,
        'text': text
    })

def send_photo(chat_id, image_bytes, caption=''):
    files = {'photo': ('qr.png', image_bytes)}
    data = {'chat_id': chat_id, 'caption': caption}
    requests.post(API_URL + 'sendPhoto', files=files, data=data)

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if 'message' not in update:
        return 'ok'

    message = update['message']
    user_id = message['from']['id']

    if 'contact' in message:
        phone = message['contact']['phone_number']
        user_data[user_id] = {'phone': phone, 'step': 'wait_code'}
        send_message(user_id, f"📲 Телефон сохранён: {phone}\nТеперь отправь 6-значный код.")
    elif 'text' in message:
        text = message['text']
        if user_id not in user_data:
            if text.startswith('+') and len(text) > 10:
                user_data[user_id] = {'phone': text, 'step': 'wait_code'}
                send_message(user_id, "✅ Номер сохранён. Теперь пришли 6-значный код.")
            else:
                send_message(user_id, "Сначала отправь свой номер телефона или контакт.")
        else:
            if user_data[user_id]['step'] == 'wait_code':
                if text.isdigit() and len(text) == 6:
                    phone = user_data[user_id]['phone']
                    qr_text = f"P|{phone}|{text}"

                    qr = qrcode.make(qr_text)
                    bio = BytesIO()
                    qr.save(bio, 'PNG')
                    bio.seek(0)

                    send_photo(user_id, bio, caption=f"Вот твой QR Код")
                    del user_data[user_id]
                else:
                    send_message(user_id, "⚠️ Нужно отправить ровно 6 цифр.")

    return 'ok'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
