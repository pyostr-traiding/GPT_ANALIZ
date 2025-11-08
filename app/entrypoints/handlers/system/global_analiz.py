import os

from dotenv import load_dotenv

from pika.spec import Basic
from pika.adapters.blocking_connection import BlockingChannel

from app.core.mail import send_to_rabbitmq
from app.core.scripts.trend_analiz import trend_analiz
from app.entrypoints.decorators import action_handler
from app.entrypoints.handlers.actions.schemas.actions import ActionSchema


load_dotenv()

RABBITMQ_URL = os.getenv('URL_RABBITMQ')


@action_handler(['trend_analiz'])
def handle_trend_analiz(
        channel: BlockingChannel,
        method: Basic.Deliver,
        data: ActionSchema,
):
    """
    Системный анализ тренда

    Задача установка в базе данных значения текущего тренда
    """
    result = trend_analiz()

    channel.basic_ack(delivery_tag=method.delivery_tag)
    if isinstance(result, str):
        send_to_rabbitmq(
            {
                "is_test": True,
                "notification": False,
                "text": f"Ошибка обработки GPT: {result}",
            }
        )