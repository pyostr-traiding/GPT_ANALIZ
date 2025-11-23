from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic

from app.core.scripts.general import general_script
from app.entrypoints.decorators import action_handler
from app.entrypoints.handlers.actions.schemas.actions import ActionSchema
from conf.settings import settings


@action_handler(['general_analiz'])
def handle_general_analiz(
        channel: BlockingChannel,
        method: Basic.Deliver,

        data: ActionSchema
):
    message = settings.tg_client.send_message(
        chat_id=data.tg_id,
        text='🟢 Запрос общей сводки принят в работу'
    )

    result = general_script(
        message=message,
        data=data,
    )
    channel.basic_ack(delivery_tag=method.delivery_tag)

