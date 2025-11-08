import json

from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties

from app.entrypoints.decorators import ACTION_HANDLERS
from app.entrypoints.handlers.actions.schemas.actions import ActionSchema


def process_message(
        ch: BlockingChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes,

):
    # if body is bytes:
    decode_message = body.decode('utf-8')
    json_message = json.loads(decode_message)
    schema_message = ActionSchema.model_validate_json(json_message)
    if schema_message.action in ACTION_HANDLERS:
        for func in ACTION_HANDLERS[schema_message.action]:
            func(
                channel=ch,
                data=schema_message,
                method=method
            )