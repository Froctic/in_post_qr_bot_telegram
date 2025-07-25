from flask import Flask, request
import qrcode
from io import BytesIO
import requests
import os

TOKEN = os.environ.get('7611903971:AAGJ9MWOcx7YLcMT3tP8IlauvBp0qrIcw7U')  # В Render лучше хранить токен в переменной окружения
API_URL = f'https://api.telegram.org/bot7611903971:AAGJ9MWOcx7YLcMT3tP8IlauvBp0qrIcw7U/'

user_data = {}  # user_id: {'step': 'waiting_phone'/'waiting_code', 'phones': [], 'codes': []}

def get_updates(offset=None):
    params = {'timeout': 30, 'offset': offset}
    res = requests.get(API_URL + 'getUpdates', params=params)
    return res.json()

def send_message(chat_id, text, reply_markup=None):
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        data['reply_markup'] = reply_markup
    requests.post(API_URL + 'sendMessage', data=data)

def send_photo(chat_id, image_bytes, caption=''):
    files = {'photo': ('qr.png', image_bytes)}
    data = {'chat_id': chat_id, 'caption': caption}
    requests.post(API_URL + 'sendPhoto', files=files, data=data)

def send_main_menu(chat_id):
    keyboard = {
        'inline_keyboard': [
            [{'text': 'Сгенерировать код для пачки', 'callback_data': 'batch_qr'}]
        ]
    }
    send_message(chat_id, "Выбери действие:", reply_markup=json.dumps(keyboard))

def handle_contact(message):
    user_id = message['from']['id']
    phone = message['contact']['phone_number']
    # для упрощения здесь не используем batch, только одиночный вариант
    user_data[user_id] = {'step': 'wait_code', 'phones': [phone], 'codes': []}
    send_message(user_id, f"📲 Телефон сохранён: {phone}\nТеперь отправь 6-значный код.")

def handle_text(message):
    user_id = message['from']['id']
    text = message['text']

    if user_id not in user_data:
        send_main_menu(user_id)
        return

    step = user_data[user_id].get('step')

    if step == 'waiting_phone':
        # ожидаем номер телефона для пачки
        if text.startswith('+') and len(text) > 10:
            user_data[user_id]['phones'] = [text]
            user_data[user_id]['step'] = 'waiting_code'
            send_message(user_id, "✅ Номер телефона получен. Теперь пришли 6-значный код для пачки (через запятую, например: 123456,654321)")
        else:
            send_message(user_id, "❗ Введите номер телефона в формате +7xxxxxxxxxx")
        return

    if step == 'waiting_code':
        # получили код(ы)
        codes = [c.strip() for c in text.split(',') if c.strip().isdigit() and len(c.strip()) == 6]
        if not codes:
            send_message(user_id, "⚠️ Нужно отправить один или несколько 6-значных кодов через запятую.")
            return
        user_data[user_id]['codes'] = codes

        # Генерируем QR для каждого (пример с одним для простоты, можно сделать несколько файлов или один с объединением)
        for code in codes:
            phone = user_data[user_id]['phones'][0]
            qr_text = f"P|{phone}|{code}"
            qr = qrcode.make(qr_text)
            bio = BytesIO()
            qr.save(bio, 'PNG')
            bio.seek(0)
            send_photo(user_id, bio, caption=f"QR Код для: {phone} | Код: {code}")

        user_data.pop(user_id)
        send_main_menu(user_id)
        return

    if step == 'wait_code':
        # одиночный режим, как раньше
        if text.isdigit() and len(text) == 6:
            phone = user_data[user_id]['phones'][0]
            qr_text = f"P|{phone}|{text}"

            qr = qrcode.make(qr_text)
            bio = BytesIO()
            qr.save(bio, 'PNG')
            bio.seek(0)

            send_photo(user_id, bio, caption="Вот твой QR Код")
            user_data.pop(user_id)
            send_main_menu(user_id)
        else:
            send_message(user_id, "⚠️ Нужно отправить ровно 6 цифр.")
        return

def handle_callback_query(callback):
    user_id = callback['from']['id']
    data = callback['data']

    if data == 'batch_qr':
        user_data[user_id] = {'step': 'waiting_phone', 'phones': [], 'codes': []}
        send_message(user_id, "✉️ Пришли номер телефона для пачки (например +79991234567)")

import json

def main():
    last_update_id = None
    print("Бот запущен...")

    while True:
        updates = get_updates(last_update_id)
        for update in updates.get('result', []):
            last_update_id = update['update_id'] + 1

            if 'callback_query' in update:
                handle_callback_query(update['callback_query'])
                continue

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
