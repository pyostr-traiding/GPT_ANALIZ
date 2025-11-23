import datetime
import json
import os
from typing import Literal

import redis
from dotenv import load_dotenv

load_dotenv()

redis_server = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    password=os.getenv('REDIS_PASSWORD'),
    port=int(os.getenv('REDIS_PORT')),
    db=5,
    decode_responses=True
)

def add_message(
        chat_uuid: str,
        action: str,
        message_type: str,
        message: str,
        code: str,
        context: int,
        role: Literal['assistant', 'user'],
):
    """

    """

    payload = {
        'uuid': chat_uuid,
        'action': action,
        'message_type': message_type,
        'message': message,
        'role': role,
        'code': code,
        'context': context,
        'dt': str(datetime.datetime.now(datetime.UTC)),
    }
    key = f'chat:{chat_uuid}:{action}'

    chat = redis_server.get(key)
    if chat is None:
        chat = []
    else:
        chat = json.loads(chat)

    chat.append(payload)

    redis_server.set(key, json.dumps(chat))
    redis_server.publish(channel='GPT_ANALIZ', message=json.dumps(payload))

def get_chat(
        key: str,
):
    result = redis_server.get(key)
    if result is None:
        return False
    return json.loads(result)
