from pprint import pprint

from google import genai
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic

from API.gemini.api import send_gpt_data
from app.core.scripts.ulils.s_redis import get_chat, add_message
from app.entrypoints.decorators import action_handler
from app.entrypoints.handlers.actions.schemas.actions import ActionSchema
from conf.settings import settings


@action_handler(['new_message_in_chat'])
def handle_new_message_in_chat(
        channel: BlockingChannel,
        method: Basic.Deliver,

        data: ActionSchema
):
    chat_uuid = data.extra.uuid.split(':')[1]
    action = data.extra.uuid.split(':')[2]

    # try:
    chat_history_redis = get_chat(data.extra.uuid)
    if not chat_history_redis:
        chat_history_redis = []
    chat_history = []
    for message in chat_history_redis:
        if message['message_type'] == 'text':
            role = 'user' if message["role"] == 'user' else 'model'
            chat_history.append({
                "role": role,
                "parts": [{"text": message["message"]}],
            })
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    chat = client.chats.create(model="gemini-2.5-flash", history=chat_history)
    add_message(
        chat_uuid=chat_uuid,
        action=action,
        message_type='text',
        message=data.extra.text,
        role='user'
    )
    result = send_gpt_data(chat=chat, prompt=data.extra.text)
    add_message(
        chat_uuid=chat_uuid,
        action=action,
        message_type='text',
        message=result,
        role='assistant'
    )
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
