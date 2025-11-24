import json
import os
from datetime import datetime

import pika
from dotenv import load_dotenv

load_dotenv()

credentials = pika.PlainCredentials(
    username=os.getenv('RABBITMQ_USERNAME'),
    password=os.getenv('RABBITMQ_PASSWORD')
)

connection_params = pika.ConnectionParameters(
    host=os.getenv('RABBITMQ_HOST'),
    port=os.getenv('RABBITMQ_PORT'),
    virtual_host=os.getenv('RABBITMQ_VIRTUAL_HOST'),
    credentials=credentials
)


def json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def send_to_rabbitmq(
        message: dict,
) -> bool:
    """
    Отправить сообщение в RabbitMQ.
    Возвращает True при успехе, иначе False.
    """
    try:
        connection = pika.BlockingConnection(connection_params)
        channel = connection.channel()

        channel.queue_declare(queue='mailing', durable=True)

        body = json.dumps(message, default=json_serializer, ensure_ascii=False)

        channel.basic_publish(
            exchange='',
            routing_key='mailing',
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2  # сообщение сохраняется при сбоях
            )
        )

        print(f"[x] Отправлено сообщение в очередь 'mailing': {message}")
        connection.close()
        return True

    except Exception as e:
        print(f"[!] Ошибка отправки в RabbitMQ: {e}")
        return False
