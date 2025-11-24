import json
import requests
import tiktoken
import logging
from collections import deque
from typing import List, Dict, Tuple

from pika.spec import Basic
from pika.adapters.blocking_connection import BlockingChannel

from app.entrypoints.s_redis import get_chat, add_message
from app.entrypoints.schemas.actions import ActionSchema
from conf.settings import settings

HEADERS_API = {
    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
}
API_URL = 'https://openrouter.ai/api/v1/chat/completions'

enc = tiktoken.encoding_for_model("gpt-4o-mini")
logger = logging.getLogger(__name__)


def count_chat_tokens(messages: List[Dict[str, str]], encoding) -> int:
    """
    Точный подсчет токенов для ChatML формата (для gpt-4o / gpt-4o-mini).
    """
    if not messages:
        return 0

    chat_parts = []
    for msg in messages:
        chat_parts.extend([
            f"<|im_start|>{msg['role']}",
            f"<|im_end|>",
            msg['content'],
            "<|im_end|>"
        ])
    chat_text = "\n".join(chat_parts)
    return len(encoding.encode(chat_text)) + 3


def trim_chat_history(messages: List[Dict[str, str]], encoding, max_tokens: int) -> Tuple[List[Dict[str, str]], int]:
    """
    Обрезает историю сообщений с начала, чтобы уложиться в max_tokens.
    Гарантирует сохранение последнего сообщения.
    """
    if not messages:
        return [], 0

    total = count_chat_tokens(messages, encoding)
    if total <= max_tokens:
        return messages[:], total

    trimmed_deque = deque(messages)
    while trimmed_deque and count_chat_tokens(list(trimmed_deque), encoding) > max_tokens:
        if len(trimmed_deque) == 1:
            # оставляем последнее сообщение
            break
        trimmed_deque.popleft()

    trimmed = list(trimmed_deque)
    return trimmed, count_chat_tokens(trimmed, encoding)


def handle_new_message_in_chat(
        channel: BlockingChannel,
        method: Basic.Deliver,
        data: ActionSchema
):
    print(data)
    uuid_parts = data.extra.uuid.split(':')
    if len(uuid_parts) < 3:
        print(f"Invalid UUID format: {data.extra.uuid}")
        return

    chat_uuid = uuid_parts[1]
    action = uuid_parts[2]
    print(chat_uuid)

    # Добавляем сообщение пользователя
    add_message(
        chat_uuid=chat_uuid,
        action=action,
        message_type='text',
        message=data.extra.text,
        role='user',
        code=data.extra.code,
        context=data.extra.context,
    )

    # Получаем историю
    chat_history_redis = get_chat(data.extra.uuid) or []
    print('chat_history_redis: ', chat_history_redis)
    chat_history = [
        {"role": msg["role"], "content": msg["message"]}
        for msg in chat_history_redis
        if msg.get('message_type') == 'text'
    ]

    max_context_tokens = int(data.extra.context or 128000)

    print(f"Before trimming: {len(chat_history)} messages, "
                 f"{count_chat_tokens(chat_history, enc)} tokens")

    chat_history_trimmed, total_tokens = trim_chat_history(chat_history, enc, max_context_tokens)

    print(
        f"Chat {chat_uuid}: {total_tokens}/{max_context_tokens} tokens. "
        f"Messages: {len(chat_history)} -> {len(chat_history_trimmed)}"
    )

    if not chat_history_trimmed:
        chat_history_trimmed = [{"role": "user", "content": data.extra.text}]
        total_tokens = count_chat_tokens(chat_history_trimmed, enc)

    payload = {
        "model": data.extra.code,
        "messages": chat_history_trimmed,
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    try:
        response = requests.post(
            url=API_URL,
            headers=HEADERS_API,
            json=payload,
            timeout=60,
        )

        response.raise_for_status()

        resp_model = response.json()
        resp_text = resp_model['choices'][0]['message']['content']

        add_message(
            chat_uuid=chat_uuid, action=action, message_type='text',
            message=resp_text, role='assistant', code=data.extra.code, context=data.extra.context
        )

        print(f"Chat {chat_uuid}: Response generated successfully ({len(resp_text)} chars)")

    except requests.exceptions.RequestException as e:
        error_msg = f"API request failed: {str(e)}"
        print(error_msg)
        add_message(
            chat_uuid=chat_uuid, action=action, message_type='text',
            message=error_msg, role='assistant', code=data.extra.code, context=data.extra.context
        )
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        error_msg = f"API response parse error: {str(e)}"
        print(error_msg)
        add_message(
            chat_uuid=chat_uuid, action=action, message_type='text',
            message=error_msg, role='assistant', code=data.extra.code, context=data.extra.context
        )
    except Exception as e:
        print(f"Unexpected error in chat {chat_uuid}")
        add_message(
            chat_uuid=chat_uuid, action=action, message_type='text',
            message=f"Internal error: {str(e)}", role='assistant',
            code=data.extra.code, context=data.extra.context
        )

