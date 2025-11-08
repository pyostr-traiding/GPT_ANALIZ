# import io
# import os
#
# from dotenv import load_dotenv
#
# from conf.settings import settings
#
# load_dotenv()
#
# # путь к файлу
# filename = "img.jpg"
#
# # открываем и читаем в память
# with open(filename, "rb") as f:
#     buf = io.BytesIO(f.read())
#
# buf.seek(0)
#
# print(buf)
#
# res = settings.s3_client.Bucket(os.getenv('AWS_STORAGE_BUCKET_NAME')).put_object(
#     Key='media/img.jpg',
#     Body=buf,
#     ContentType='image/jpeg'
# )
# print(res)
import json
from pprint import pprint

x = {"action": "general_analiz","tg_id": "572982939","created_on": "123"}
