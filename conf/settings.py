import os

import boto3

from boto3.resources.base import ServiceResource

from dotenv import load_dotenv

from telebot import TeleBot

load_dotenv()


class Settings:
    BOT_TOKEN: str = os.getenv('BOT_TOKEN')
    tg_client: TeleBot = TeleBot(
        token=BOT_TOKEN
    )
    BASE_API_URL = os.getenv('BASE_API_URL')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    TEST_NET: bool = False
    PRINT_INFO: bool = True

    CATEGORY_KLINE: str = 'inverse'

    SYMBOL: str = 'BTCUSDT'
    s3_client: ServiceResource = boto3.resource(
        service_name='s3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        endpoint_url='https://s3.timeweb.com',
    )
    OPENAI_API_KEY = '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'

settings = Settings()
