import requests
import time
import qrcode
from io import BytesIO

TOKEN = 'ТВОЙ_ТОКЕН_БОТА'
API_URL = f'https://api.telegram.org/bot7611903971:AAGJ9MWOcx7YLcMT3tP8IlauvBp0qrIcw7U/'

user_data = {}  # user_id: {'phone': '...', 'step': 'wait_code'}

def get_updates(offset=None):
    params = {'timeout': 30, 'offset': offset}
    res = requests.get(API_URL + 'getUpdates', params=params)
    return res.json()

def send_message(chat_id, text):
    requests.post(API_URL + 'sendMessage', data={
        'chat_id': chat_id,
        'text': text
    })

def send_photo(chat_id, image_bytes, caption=''):
    files = {'photo': ('qr.png', image_bytes)}
    data = {'chat_id': chat_id, 'caption': caption}
    requests.post(API_URL + 'sendPhoto', files=files, data=data)

def handle_contact(message):
    user_id = message['from']['id']
    phone = message['contact']['phone_number']
    user_data[user_id] = {'phone': phone, 'step': 'wait_code'}
    send_message(user_id, f"📲 Телефон сохранён: {phone}\nТеперь отправь 6-значный код.")

def handle_text(message):
    user_id = message['from']['id']
    text = message['text']

    if user_id not in user_data:
        if text.startswith('+') and len(text) > 10:
            user_data[user_id] = {'phone': text, 'step': 'wait_code'}
            send_message(user_id, "✅ Номер сохранён. Теперь пришли 6-значный код.")
        else:
            send_message(user_id, "Сначала отправь свой номер телефона или контакт.")
        return

    if user_data[user_id]['step'] == 'wait_code':
        if text.isdigit() and len(text) == 6:
            phone = user_data[user_id]['phone']
            qr_text = f"P|{phone}|{text}"

            # Создание QR-кода
            qr = qrcode.make(qr_text)
            bio = BytesIO()
            qr.save(bio, 'PNG')
            bio.seek(0)

            send_photo(user_id, bio, caption=f"Вот твой QR Код")
            del user_data[user_id]
        else:
            send_message(user_id, "⚠️ Нужно отправить ровно 6 цифр.")

def main():
    last_update_id = None
    print("Бот запущен...")

    while True:
        updates = get_updates(last_update_id)
        for update in updates.get('result', []):
            last_update_id = update['update_id'] + 1

            msg = update.get('message')
            if not msg:
                continue

            if 'contact' in msg:
                handle_contact(msg)
            elif 'text' in msg:
                handle_text(msg)

        time.sleep(1)

if __name__ == '__main__':
    main()
