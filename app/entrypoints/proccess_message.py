import json

from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties

from app.entrypoints.general import handle_general_script
from app.entrypoints.new_message import handle_new_message_in_chat
from app.entrypoints.schemas.actions import ActionSchema
from app.entrypoints.trend_analiz import handle_trend_analiz


def process_message(
        ch: BlockingChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes,

):
    # if body is bytes:
    decode_message = body.decode('utf-8')
    json_message = json.loads(decode_message)

    if isinstance(json_message, str):
        schema_message = ActionSchema.model_validate_json(json_message)
    else:
        schema_message = ActionSchema(**json_message)

    if schema_message.action == 'new_message_in_chat':
        handle_new_message_in_chat(
            data=schema_message,
            channel=ch,
            method=method,
        )
    elif schema_message.action == 'general_analiz':
        handle_general_script(
            data=schema_message,
        )

    elif schema_message.action == 'trend_analiz':
        handle_trend_analiz(
            data=schema_message,
        )

    ch.basic_ack(delivery_tag=method.delivery_tag)
