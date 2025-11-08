import time

import google

from API.panel.gpt import get_prompt

def safe_send_message(chat, text, retries=4, delay=5):
    """
    Отправка сообщения с повторными попытками в случае ошибки.
    retries: максимальное число попыток
    delay: задержка между попытками в секундах
    """
    attempt = 0
    while attempt < retries:
        try:
            print(f'[GPT отправка]: {text}')
            response = chat.send_message(text)
            return response.text
        except Exception as e:
            print(f'[GPT]: {e}')
            attempt += 1
            if attempt >= retries:
                return None
            time.sleep(delay)

def send_gpt_data(chat, prompt: str, data=None) -> str:
    """
    Универсальная функция для отправки данных в GPT по заданному prompt_name
    data: дополнительные данные, которые нужно добавить к prompt
    """
    text = prompt
    if data is not None:
        text += str(data)
    return safe_send_message(chat, text)
