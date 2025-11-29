import os

import boto3

from boto3.resources.base import ServiceResource

from dotenv import load_dotenv
from infisical_sdk import InfisicalSDKClient

from telebot import TeleBot

load_dotenv()

# Инициализация клиента
client = InfisicalSDKClient(
    host=os.getenv('INFISICAL_HOST'),
    token=os.getenv('INFISICAL_TOKEN'),
    cache_ttl=300
)


def load_project_secrets(project_slug: str):
    resp = client.secrets.list_secrets(
        project_slug=project_slug,
        environment_slug=os.getenv('ENVIRONMENT_SLUG'),
        secret_path="/"
    )
    return {s['secretKey']: s['secretValue'] for s in resp.to_dict()['secrets']}

# Загружаем общие секреты
shared_secrets = load_project_secrets("shared-all")

# Загружаем проектные секреты
project_secrets = load_project_secrets("gpt_analiz")

# Объединяем: проектные перезаписывают общие при совпадении ключей
all_secrets = {**shared_secrets, **project_secrets}

# Добавляем в окружение
os.environ.update(all_secrets)

class Settings:

    ################################
    #/ Telegram
    ################################

    BOT_TOKEN: str = os.getenv('BOT_TOKEN')
    tg_client: TeleBot = TeleBot(
        token=BOT_TOKEN
    )

    ################################
    #/ APU URL
    ################################

    BASE_API_URL = os.getenv('BASE_API_URL')

    ################################
    #/ Биржевые
    ################################

    TEST_NET: bool = False
    PRINT_INFO: bool = True
    CATEGORY_KLINE: str = 'inverse'
    SYMBOL: str = 'BTCUSDT'

    ################################
    #/ S3 Client
    ################################

    AWS_ACCESS_KEY_ID: str = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY: str = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME: str = os.getenv('AWS_STORAGE_BUCKET_NAME')

    S3_URL: str = f'https://s3.twcstorage.ru/{AWS_STORAGE_BUCKET_NAME}/'
    s3_client: ServiceResource = boto3.resource(
        service_name='s3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        endpoint_url='https://s3.timeweb.com',
    )

    ################################
    # / API GPT
    ################################

    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    ################################
    # / RabbitMQ
    ################################

    RABBITMQ_HOST: str = os.getenv('RABBITMQ_HOST')
    RABBITMQ_PASSWORD: str = os.getenv('RABBITMQ_PASSWORD')
    RABBITMQ_PORT: str = os.getenv('RABBITMQ_PORT')
    RABBITMQ_USERNAME: str = os.getenv('RABBITMQ_USERNAME')
    RABBITMQ_VIRTUAL_HOST: str = os.getenv('RABBITMQ_VIRTUAL_HOST')

    RABBITMQ_URL: str = os.getenv('RABBITMQ_URL')

    ################################
    # / Redis
    ################################

    REDIS_HOST: str = os.getenv('REDIS_HOST')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT'))
    REDIS_PASSWORD: str = os.getenv('REDIS_PASSWORD')


settings = Settings()
