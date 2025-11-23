import requests
import tiktoken
import logging

from pika.spec import Basic
from collections import deque
from typing import List, Dict, Tuple

from pika.adapters.blocking_connection import BlockingChannel

from app.core.scripts.ulils.s_redis import get_chat, add_message
from app.entrypoints.decorators import action_handler
from app.entrypoints.handlers.actions.schemas.actions import ActionSchema

HEADERS_API = {
    "Authorization": "Bearer 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",
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
    # +3 для BOS/EOS и возможных служебных
    return len(encoding.encode(chat_text)) + 3


def trim_chat_history(messages: List[Dict[str, str]], encoding, max_tokens: int) -> Tuple[List[Dict[str, str]], int]:
    """
    Обрезает историю сообщений с начала, чтобы уложиться в max_tokens.
    Использует deque для O(1) popleft.
    """

    def _count(msgs: List[Dict[str, str]]) -> int:
        return count_chat_tokens(msgs, encoding)

    total = _count(messages)
    if total <= max_tokens:
        return messages[:], total  # copy to avoid mutation

    # Используем deque для эффективного удаления с начала
    trimmed_deque = deque(messages)
    while trimmed_deque and _count(list(trimmed_deque)) > max_tokens:
        trimmed_deque.popleft()

    trimmed = list(trimmed_deque)
    return trimmed, _count(trimmed)


@action_handler(['new_message_in_chat'])
def handle_new_message_in_chat(
        channel: BlockingChannel,
        method: Basic.Deliver,
        data: ActionSchema
):
    """
    Обработчик новых сообщений в чате.
    Добавляет сообщение пользователя, обрезает историю по токенам,
    отправляет в API и сохраняет ответ.
    """
    # Парсинг UUID (лучше использовать namedtuple или dataclass в будущем)
    uuid_parts = data.extra.uuid.split(':')
    chat_uuid = uuid_parts[1]
    action = uuid_parts[2]

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

    # Получаем историю чата (исправлено: по chat_uuid, а не полному UUID)
    chat_history_redis = get_chat(chat_uuid) or []

    # Строим chat_history только из текстовых сообщений
    chat_history = [
        {
            "role": msg["role"],
            "content": msg["message"],
        }
        for msg in chat_history_redis
        if msg['message_type'] == 'text'
    ]

    max_context_tokens = int(data.extra.context)  # Явное приведение к int

    # Обрезаем историю
    chat_history_trimmed, total_tokens = trim_chat_history(
        chat_history, enc, max_context_tokens
    )

    logger.info(
        f"Chat {chat_uuid}: Tokens {total_tokens}/{max_context_tokens}. "
        f"Messages: {len(chat_history)} -> {len(chat_history_trimmed)}"
    )

    # Отправляем запрос в API
    try:
        response = requests.post(
            url=API_URL,
            headers=HEADERS_API,
            json={  # Лучше json= вместо data=json.dumps()
                "model": data.extra.code,  # e.g. "gpt-4o-mini"
                "messages": chat_history_trimmed,  # ИСПРАВЛЕНО: используем trimmed!
            },
            timeout=30,  # Добавлен timeout
        )

        response.raise_for_status()  # Поднимает HTTP ошибки

        resp_model = response.json()
        if 'choices' not in resp_model or not resp_model['choices']:
            raise ValueError("No choices in API response")

        resp_text = resp_model['choices'][0]['message']['content']

        # Добавляем ответ ассистента
        add_message(
            chat_uuid=chat_uuid,
            action=action,
            message_type='text',
            message=resp_text,
            role='assistant',
            code=data.extra.code,
            context=data.extra.context,
        )

    except requests.exceptions.RequestException as e:
        error_msg = f"API request failed: {str(e)}"
        logger.error(error_msg)
        add_message(
            chat_uuid=chat_uuid,
            action=action,
            message_type='text',
            message=error_msg,
            role='assistant',
            code=data.extra.code,
            context=data.extra.context,
        )
    except (KeyError, ValueError, Exception) as e:
        error_msg = f"API response error: {str(e)}"
        logger.error(error_msg)
        add_message(
            chat_uuid=chat_uuid,
            action=action,
            message_type='text',
            message=error_msg,
            role='assistant',
            code=data.extra.code,
            context=data.extra.context,
        )

    # Ack в любом случае
    channel.basic_ack(delivery_tag=method.delivery_tag)
    # except Exception as e:
    #     print(e)
    #     add_message(
    #         chat_uuid=chat_uuid,
    #         action=action,
    #         message_type='text',
    #         message=str(e),
    #         role='assistant'
    #     )
