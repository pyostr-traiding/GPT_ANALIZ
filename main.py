import os
import time
import pika
from dotenv import load_dotenv
from pika.exceptions import AMQPConnectionError, ChannelClosed, ConnectionClosed

from app.entrypoints.proccess_message import process_message
from conf.settings import settings

load_dotenv()

RABBITMQ_URL = settings.RABBITMQ_URL
RECONNECT_DELAY = 2  # секунд


def consume_rabbitmq():
    # while True:
        # try:
        #     print(" [*] Подключение к RabbitMQ...")
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    # QoS
    channel.basic_qos(prefetch_count=1)

    channel.queue_declare(queue="queue_gpt_analiz", durable=True)
    channel.queue_declare(queue="queue_gpt_message", durable=True)
    channel.queue_declare(
        queue="queue_gpt_analiz_trash",
        durable=True,
        arguments={
            "x-message-ttl": 500_000,  # 5 минут задержка
            "x-dead-letter-exchange": "",  # возврат в дефолтный exchange
        }
    )

    # Подписка на обработчики
    channel.basic_consume(queue='queue_gpt_analiz', on_message_callback=process_message)
    channel.basic_consume(queue='queue_gpt_analiz_trash', on_message_callback=process_message)
    channel.basic_consume(queue='queue_gpt_message', on_message_callback=process_message)

    print(" [*] Ожидание сообщений RabbitMQ...")
    channel.start_consuming()  # блокирующий вызов
        #
        # except (AMQPConnectionError, ChannelClosed, ConnectionClosed) as e:
        #     print(f" [!] Проблема с соединением RabbitMQ: {e}")
        # except Exception as e:
        #     print(f" [!] Общая ошибка RabbitMQ: {e}")
        # finally:
        #     print(f" [x] Попытка переподключения через {RECONNECT_DELAY} секунд...")
        #     time.sleep(RECONNECT_DELAY)

if __name__ == "__main__":
    try:
        consume_rabbitmq()
    except KeyboardInterrupt:
        print(" [x] Выход...")
